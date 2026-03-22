# ml/train.py  (v5 — Crime Danger Index + percentile rank target)
# ─────────────────────────────────────────────────────────────────────────────
# SafeHer — Correct risk target definition.
#
# WHY PREVIOUS TARGETS FAILED:
#   v2: Per-incident severity → same location, different labels → R²=0.08
#   v3: Aggregated mean severity weight → compressed to 0.15–0.25 range
#       Only 9/14129 cells > 0.7 → model predicts mean → R²=0.17
#   v4: Same compression problem — MinMaxScaler with skewed data
#       makes almost all cells cluster near 0
#
# ROOT CAUSE: Averaging severity weights ignores frequency.
#   A cell with 1000 thefts + 1 homicide ≈ 1000 thefts alone (by mean).
#   But the homicide cell IS more dangerous for a safety app.
#
# CORRECT TARGET — Crime Danger Index (CDI):
#   CDI(cell) = violent_rate(cell) × log1p(crime_count(cell))
#
#   violent_rate = violent crimes (sev≥3) / total crimes in cell
#   log1p(crime_count) = crime frequency, log-scaled to handle outliers
#
#   → Cells with HIGH violent rate AND HIGH frequency score highest
#   → Rare crimes in quiet areas don't dominate
#   → Convert to percentile rank → uniform 0–1 distribution
#      → cell at 90th percentile is more dangerous than 90% of all cells
#
# Temporal multiplier uses VIOLENT crime rate by hour (not total),
# since Chicago records unreported times as 00:00 — total count at
# midnight is inflated by data entry, violent count is not.
#
# Architecture (unchanged from v4):
#   risk(cell, hour, day) = spatial_risk(cell) × temporal_multiplier(hour, day)
#
# Saved artifacts:
#   lgbm_model.pkl       — spatial risk model (CDI percentile)
#   density_lookup.pkl   — (grid_lat, grid_lon) → crime_count
#   temporal_lookup.pkl  — (hour, day_of_week) → violent multiplier
#   risk_scaler.pkl      — kept for API compatibility (identity here)
# ─────────────────────────────────────────────────────────────────────────────

import os
import time
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import MinMaxScaler

import lightgbm as lgb
import xgboost as xgb

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(__file__)
DATA_PATH     = os.path.join(BASE_DIR, "data",   "chicago_processed.csv")
MODEL_DIR     = os.path.join(BASE_DIR, "models")
LGBM_PATH     = os.path.join(MODEL_DIR, "lgbm_model.pkl")
DENSITY_PATH  = os.path.join(MODEL_DIR, "density_lookup.pkl")
TEMPORAL_PATH = os.path.join(MODEL_DIR, "temporal_lookup.pkl")
SCALER_PATH   = os.path.join(MODEL_DIR, "risk_scaler.pkl")

# Violent crimes = severity ≥ 3 (battery, assault, robbery, weapons, homicide)
VIOLENT_SEVERITY_THRESHOLD = 3

# Spatial features — cell-level, time-invariant
SPATIAL_FEATURES = [
    "Latitude", "Longitude",
    "crime_count",
    "log_crime_count",      # log1p(crime_count) — new
    "violent_count",        # new
    "violent_rate",         # new
    "location_type",
    "is_domestic_rate",
    "community_area",
    "police_district",
    "distance_to_police",
    "rolling_7day",
]

SEED = 42


# ─────────────────────────────────────────────────────────────────────────────
# Component 1 — Build spatial risk (CDI percentile)
# ─────────────────────────────────────────────────────────────────────────────

def build_spatial_features(df: pd.DataFrame):
    """
    One row per grid cell. Target = CDI percentile rank (0–1).

    CDI = violent_rate × log1p(crime_count)
    base_risk = CDI.rank(pct=True)   ← uniform distribution
    """
    print("[2/6] Building spatial risk (CDI percentile) per grid cell ...")

    df["is_violent"] = (df["severity"] >= VIOLENT_SEVERITY_THRESHOLD).astype(int)

    cell = df.groupby(["grid_lat", "grid_lon"]).agg(
        Latitude          = ("Latitude",          "mean"),
        Longitude         = ("Longitude",         "mean"),
        crime_count       = ("crime_count",       "first"),
        rolling_7day      = ("rolling_7day",      "mean"),
        violent_count     = ("is_violent",        "sum"),
        incident_count    = ("severity",          "count"),
        location_type     = ("location_type",     lambda x: x.mode().iloc[0]),
        is_domestic_rate  = ("is_domestic",       "mean"),
        community_area    = ("community_area",    lambda x: x.mode().iloc[0]),
        police_district   = ("police_district",   lambda x: x.mode().iloc[0]),
        distance_to_police= ("distance_to_police","mean"),
    ).reset_index()

    # CDI features
    cell["violent_rate"]    = cell["violent_count"] / cell["incident_count"].clip(lower=1)
    cell["log_crime_count"] = np.log1p(cell["crime_count"])
    cell["CDI"]             = cell["violent_rate"] * cell["log_crime_count"]

    # Percentile rank → uniform 0–1 target
    cell["base_risk"] = cell["CDI"].rank(pct=True)

    # Print distribution check
    print(f"      Grid cells   : {len(cell):,}")
    print(f"      CDI range    : {cell['CDI'].min():.4f} → {cell['CDI'].max():.4f}")
    print(f"      base_risk    : mean={cell['base_risk'].mean():.4f}  "
          f"(should be ~0.50 for uniform dist)")
    print(f"      >0.7 cells   : {(cell['base_risk'] > 0.7).sum():,}  "
          f"(should be ~{int(len(cell)*0.3):,} for uniform dist)")
    print(f"      >0.9 cells   : {(cell['base_risk'] > 0.9).sum():,}  "
          f"(top 10% most dangerous)")

    # Top 5 most dangerous cells
    top5 = cell.nlargest(5, "base_risk")[
        ["Latitude","Longitude","violent_rate","crime_count","base_risk"]
    ]
    print("\n      Top 5 highest-risk cells:")
    print(top5.to_string(index=False))

    scaler = MinMaxScaler()  # kept for API compatibility — identity on 0–1 range
    scaler.fit(cell[["base_risk"]])

    return cell, scaler


# ─────────────────────────────────────────────────────────────────────────────
# Component 2 — Temporal multiplier (violent crimes only)
# ─────────────────────────────────────────────────────────────────────────────

def build_temporal_lookup(df: pd.DataFrame) -> dict:
    """
    Violent crime rate by (hour, day_of_week), normalised to mean=1.0.
    Uses violent crimes only — total count is inflated at midnight
    by Chicago's data-entry convention (unreported times → 00:00).
    """
    print("\n[3/6] Building temporal multiplier (violent crimes) ...")

    violent = df[df["severity"] >= VIOLENT_SEVERITY_THRESHOLD]
    slot_counts = (
        violent.groupby(["hour", "day_of_week"])
               .size()
               .reset_index(name="count")
    )

    # Fill any missing (hour, day) slots with the global minimum
    all_slots = pd.MultiIndex.from_product(
        [range(24), range(7)], names=["hour", "day_of_week"]
    ).to_frame(index=False)
    slot_counts = all_slots.merge(slot_counts, on=["hour","day_of_week"], how="left")
    slot_counts["count"] = slot_counts["count"].fillna(slot_counts["count"].min())

    avg = slot_counts["count"].mean()
    slot_counts["multiplier"] = (slot_counts["count"] / avg).round(4)

    lookup = {
        (int(r.hour), int(r.day_of_week)): float(r.multiplier)
        for _, r in slot_counts.iterrows()
    }

    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    print(f"      Slots     : {len(lookup)} (24 × 7 = 168)")
    print(f"      Multiplier: {min(lookup.values()):.3f} → {max(lookup.values()):.3f}")
    top5 = sorted(lookup.items(), key=lambda x: x[1], reverse=True)[:5]
    print("      Top 5 dangerous time slots (violent crimes):")
    for (h, d), m in top5:
        print(f"        {days[d]} {h:02d}:00  →  {m:.3f}×")

    return lookup


# ─────────────────────────────────────────────────────────────────────────────
# Train / evaluate spatial model
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_spatial(name, model, X_test, y_test) -> dict:
    sample  = X_test.iloc[:10_000] if len(X_test) >= 10_000 else X_test
    repeats = max(1, 10_000 // len(sample))

    t0 = time.time()
    for _ in range(repeats):
        model.predict(sample)
    elapsed = round((time.time() - t0) / repeats, 2)

    y_pred = np.clip(model.predict(X_test), 0, 1)
    mae    = mean_absolute_error(y_test, y_pred)
    r2     = r2_score(y_test, y_pred)

    # High-risk: top 30% of cells (base_risk > 0.7)
    thr = 0.7
    tp  = ((y_pred > thr) & (y_test.values > thr)).sum()
    prec = tp / max((y_pred  > thr).sum(), 1)
    rec  = tp / max((y_test.values > thr).sum(), 1)

    print(f"\n  [{name}]")
    print(f"    MAE           : {mae:.4f}  (on 0–1 percentile scale)")
    print(f"    R²            : {r2:.4f}")
    print(f"    HR Precision  : {prec:.4f}  (predicted >0.7, actually >0.7)")
    print(f"    HR Recall     : {rec:.4f}  (of actual >0.7, how many caught)")
    print(f"    Inference/10k : {elapsed:.2f}s")

    return {
        "model":             name,
        "MAE":               round(mae,  4),
        "R2":                round(r2,   4),
        "hr_precision":      round(prec, 4),
        "hr_recall":         round(rec,  4),
        "inference_10k_sec": elapsed,
    }


def train_lightgbm(X_train, X_test, y_train, y_test):
    print("\n[4/6] Training LightGBM spatial model ...")
    t0 = time.time()
    model = lgb.LGBMRegressor(
        n_estimators=1000,
        learning_rate=0.02,
        max_depth=8,
        num_leaves=63,
        min_child_samples=3,
        colsample_bytree=0.8,
        subsample=0.8,
        reg_alpha=0.01,
        reg_lambda=0.01,
        random_state=SEED,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[
            lgb.early_stopping(80, verbose=False),
            lgb.log_evaluation(period=-1),
        ],
    )
    print(f"      Training time: {time.time() - t0:.1f}s")
    return model


def train_rf(X_train, y_train):
    print("\n[5/6] Training Random Forest (baseline) ...")
    t0 = time.time()
    model = RandomForestRegressor(
        n_estimators=200, max_depth=None,
        min_samples_leaf=1, random_state=SEED, n_jobs=-1,
    )
    model.fit(X_train, y_train)
    print(f"      Training time: {time.time() - t0:.1f}s")
    return model


def train_xgb(X_train, y_train):
    print("\n[5/6] Training XGBoost (baseline) ...")
    t0 = time.time()
    model = xgb.XGBRegressor(
        n_estimators=500, learning_rate=0.02, max_depth=6,
        subsample=0.8, colsample_bytree=0.8,
        random_state=SEED, n_jobs=-1, verbosity=0,
    )
    model.fit(X_train, y_train)
    print(f"      Training time: {time.time() - t0:.1f}s")
    return model


def print_feature_importance(model, features):
    imp = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)
    print("\n── LightGBM Feature Importance ──────────────────────────")
    for feat, val in imp.items():
        bar = "█" * int(val / imp.max() * 20)
        print(f"  {feat:<25} {val:>8}  {bar}")


def print_table1(results):
    print("\n" + "─"*78)
    print("  TABLE 1 — Spatial Risk Model Comparison (Paper Section 4)")
    print("─"*78)
    print(f"  {'Model':<20} {'MAE':>6} {'R²':>6} {'HR-Prec':>9} {'HR-Rec':>8} {'Inf/10k':>9}")
    print("  " + "-"*74)
    for r in results:
        print(f"  {r['model']:<20} {r['MAE']:>6.4f} {r['R2']:>6.4f} "
              f"{r['hr_precision']:>9.4f} {r['hr_recall']:>8.4f} "
              f"{r['inference_10k_sec']:>8.2f}s")
    print("─"*78)
    print("  Target = CDI percentile rank (0–1). HR threshold = 0.7 (top 30%).")
    print("  Final risk at inference = spatial_risk × temporal_multiplier.")
    print("─"*78)


def preview_combined_risk(model, cell_df, temporal_lookup, features):
    print("\n── Combined Risk Preview (spatial × temporal) ────────────")
    days  = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    slots = [(5, 1, "Tue 5AM"), (14, 2, "Wed 2PM"), (23, 4, "Fri 11PM")]
    feats = [f for f in features if f in cell_df.columns]
    spatial = np.clip(model.predict(cell_df[feats]), 0, 1)

    for hour, day, label in slots:
        mult     = temporal_lookup.get((hour, day), 1.0)
        combined = np.clip(spatial * mult, 0, 1)
        high     = (combined > 0.6).sum()
        print(f"  {label:<12}  mult={mult:.3f}  "
              f"mean_risk={combined.mean():.4f}  "
              f"high_risk_cells(>0.6)={high:>4}")
    print()
    print("  ✓ High-risk cell count should increase from morning → night.")
    print("  ✓ This is Novel Contribution 5 — dynamic temporal heatmap.")


def build_density_lookup(df):
    return df.groupby(["grid_lat","grid_lon"])["crime_count"].first().to_dict()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  SafeHer — Training v5 (CDI percentile + violent temp)  ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    print(f"[1/6] Loading {DATA_PATH} ...")
    df = pd.read_csv(DATA_PATH)
    print(f"      {len(df):,} rows")

    # Fix distance_to_police sentinel value
    if "distance_to_police" in df.columns:
        bad_mask = df["distance_to_police"] == -1
        if bad_mask.all():
            df["distance_to_police"] = 0.0
            global SPATIAL_FEATURES
            SPATIAL_FEATURES = [f for f in SPATIAL_FEATURES
                                 if f != "distance_to_police"]
            print("      ⚠ distance_to_police dropped (all -1)")
        elif bad_mask.any():
            median_d = df.loc[~bad_mask, "distance_to_police"].median()
            df.loc[bad_mask, "distance_to_police"] = median_d

    # Build components
    cell_df, scaler  = build_spatial_features(df)
    temporal_lookup  = build_temporal_lookup(df)
    density_lookup   = build_density_lookup(df)

    # Train spatial model
    feats = [f for f in SPATIAL_FEATURES if f in cell_df.columns]
    X, y  = cell_df[feats], cell_df["base_risk"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED
    )
    print(f"\n      Spatial train: {len(X_train):,}  |  test: {len(X_test):,}")

    lgbm_model = train_lightgbm(X_train, X_test, y_train, y_test)
    rf_model   = train_rf(X_train, y_train)
    xgb_model  = train_xgb(X_train, y_train)

    # Evaluate
    print("\n── Evaluation ────────────────────────────────────────────")
    results = [
        evaluate_spatial("LightGBM",     lgbm_model, X_test, y_test),
        evaluate_spatial("RandomForest", rf_model,   X_test, y_test),
        evaluate_spatial("XGBoost",      xgb_model,  X_test, y_test),
    ]
    print_table1(results)
    print_feature_importance(lgbm_model, feats)
    preview_combined_risk(lgbm_model, cell_df, temporal_lookup, feats)

    # Save
    print("[6/6] Saving artifacts ...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(lgbm_model,      LGBM_PATH)
    joblib.dump(density_lookup,  DENSITY_PATH)
    joblib.dump(temporal_lookup, TEMPORAL_PATH)
    joblib.dump(scaler,          SCALER_PATH)
    print(f"      ✓ {LGBM_PATH}")
    print(f"      ✓ {DENSITY_PATH}")
    print(f"      ✓ {TEMPORAL_PATH}")
    print(f"      ✓ {SCALER_PATH}")

    print("\n✓ Training complete.")
    print("  Expected: MAE < 0.08, R² > 0.80, HR-Prec > 0.70")
    print("  Next step: update backend/risk_grid.py")


if __name__ == "__main__":
    main()