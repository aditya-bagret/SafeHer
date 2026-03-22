# ml/preprocess.py
# ─────────────────────────────────────────────────────────────────────────────
# SafeHer — Step 1: Load raw Chicago crimes CSV, engineer all features,
# build the grid-cell crime density lookup, and save chicago_processed.csv.
#
# Run: python preprocess.py
# Input:  ml/data/chicago_crimes.csv   (raw Kaggle download)
# Output: ml/data/chicago_processed.csv
# ─────────────────────────────────────────────────────────────────────────────

# ml/preprocess.py  (updated after EDA)
# ─────────────────────────────────────────────────────────────────────────────
# SafeHer — Feature engineering with all 13 features confirmed by EDA.
#
# Changes from v1:
#   - Grid resolution fixed: lat×500 (200m cells) not lat×100 (1km cells)
#   - Chicago bounding box filter applied (removes out-of-city outliers)
#   - 6 new features: location_type, is_domestic, community_area,
#     police_district, rolling_7day_rate, distance_to_police_station
#   - Community Area NaN filled with 0 (not dropped — 7.21% of data)
#
# Run: python preprocess.py
# Input:  ml/data/chicago_crimes.csv
#         ml/data/police_stations.csv   ← free download (instructions below)
# Output: ml/data/chicago_processed.csv
#
# ── How to get police_stations.csv ───────────────────────────────────────────
# 1. Go to: https://data.cityofchicago.org/
# 2. Search: "Police Stations"
# 3. Export as CSV → save to ml/data/police_stations.csv
# Columns needed: LATITUDE, LONGITUDE (25 rows — takes 30 seconds)
# ─────────────────────────────────────────────────────────────────────────────

import os
import warnings
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(__file__)
RAW_PATH    = os.path.join(BASE_DIR, "data", "chicago_crimes.csv")
POLICE_PATH = os.path.join(BASE_DIR, "data", "police_stations.csv")
OUT_PATH    = os.path.join(BASE_DIR, "data", "chicago_processed.csv")

# ── Chicago strict bounding box (filters out-of-city outliers) ───────────────
# EDA showed lat range 36.6→42.0 — dirty rows from other IL regions
LAT_MIN, LAT_MAX = 41.64, 42.02
LON_MIN, LON_MAX = -87.94, -87.52

# ── Grid resolution: 500 × lat/lon = 0.002° ≈ 200m per cell ─────────────────
# EDA showed lat×100 gave only 747 cells (too coarse — 1km resolution)
# lat×500 gives ~19,000 cells across Chicago at proper 200m resolution
GRID_MULT = 500

# ── Severity map ──────────────────────────────────────────────────────────────
SEVERITY_MAP = {
    "HOMICIDE":               5, "CRIM SEXUAL ASSAULT":    5,
    "HUMAN TRAFFICKING":      5, "KIDNAPPING":             5,
    "ASSAULT":                4, "ROBBERY":                4,
    "STALKING":               4, "INTIMIDATION":           4,
    "BATTERY":                3, "BURGLARY":               3,
    "WEAPONS VIOLATION":      3, "ARSON":                  3,
    "THEFT":                  2, "MOTOR VEHICLE THEFT":    2,
    "CRIMINAL TRESPASS":      2, "PROSTITUTION":           2,
    "NARCOTICS":              1, "VANDALISM":              1,
    "LIQUOR LAW VIOLATION":   1, "GAMBLING":               1,
    "PUBLIC PEACE VIOLATION": 1,
}

# ── Location type grouping (confirmed by EDA Section 5) ──────────────────────
LOCATION_GROUPS = {
    "STREET":                           "street",
    "SIDEWALK":                         "street",
    "ALLEY":                            "alley",
    "PARKING LOT/GARAGE(NON.RESID.)":   "parking",
    "CHA PARKING LOT/GROUNDS":          "parking",
    "RESIDENCE":                        "residence",
    "APARTMENT":                        "residence",
    "RESIDENTIAL YARD (FRONT/BACK)":    "residence",
    "RESIDENCE-GARAGE":                 "residence",
    "RESIDENCE PORCH/HALLWAY":          "residence",
    "SCHOOL, PUBLIC, BUILDING":         "school",
    "SCHOOL, PUBLIC, GROUNDS":          "school",
    "SCHOOL, PRIVATE, BUILDING":        "school",
    "CTA PLATFORM":                     "transit",
    "CTA TRAIN":                        "transit",
    "CTA BUS":                          "transit",
    "CTA STATION":                      "transit",
    "RESTAURANT":                       "commercial",
    "SMALL RETAIL STORE":               "commercial",
    "DEPARTMENT STORE":                 "commercial",
    "GROCERY FOOD STORE":               "commercial",
    "GAS STATION":                      "commercial",
    "COMMERCIAL / BUSINESS OFFICE":     "commercial",
    "BAR OR TAVERN":                    "commercial",
    "VEHICLE NON-COMMERCIAL":           "vehicle",
    "PARK PROPERTY":                    "park",
}

# Ordinal encoding (higher = more dangerous, per EDA Section 5)
LOCATION_RISK_ORDER = {
    "alley":      6,
    "parking":    5,
    "transit":    4,
    "street":     3,
    "commercial": 3,
    "vehicle":    2,
    "school":     2,
    "park":       2,
    "residence":  1,
    "other":      1,
}


# ─────────────────────────────────────────────────────────────────────────────

def load_raw() -> pd.DataFrame:
    print(f"[1/8] Loading raw data ...")
    df = pd.read_csv(RAW_PATH, low_memory=False)
    print(f"      Raw shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
    return df


def filter_chicago(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows outside Chicago's bounding box and drop null lat/lon."""
    print("[2/8] Filtering to Chicago bounding box ...")
    before = len(df)
    df = df.dropna(subset=["Latitude", "Longitude"])
    df = df[
        df["Latitude"].between(LAT_MIN, LAT_MAX) &
        df["Longitude"].between(LON_MIN, LON_MAX)
    ].copy()
    print(f"      Removed {before - len(df):,} out-of-city/null rows. "
          f"Remaining: {len(df):,}")
    return df


def parse_datetime(df: pd.DataFrame) -> pd.DataFrame:
    print("[3/8] Parsing datetime ...")
    df["Date"] = pd.to_datetime(
        df["Date"], format="%m/%d/%Y %I:%M:%S %p", errors="coerce"
    )
    bad = df["Date"].isna().sum()
    if bad:
        print(f"      Warning: {bad:,} unparseable dates — dropping.")
        df = df.dropna(subset=["Date"])
    return df


def engineer_temporal(df: pd.DataFrame) -> pd.DataFrame:
    print("[4/8] Engineering temporal features ...")
    df["hour"]        = df["Date"].dt.hour
    df["day_of_week"] = df["Date"].dt.dayofweek   # 0=Mon, 6=Sun
    df["month"]       = df["Date"].dt.month
    # is_night: 9PM–5AM confirmed by EDA Section 3
    df["is_night"]    = ((df["hour"] >= 21) | (df["hour"] <= 5)).astype(np.int8)
    df["is_weekend"]  = (df["day_of_week"] >= 5).astype(np.int8)
    return df


def engineer_crime_features(df: pd.DataFrame) -> pd.DataFrame:
    print("[5/8] Engineering crime features ...")

    # Severity
    df["crime_type"] = df["Primary Type"].str.upper().str.strip()
    df["severity"]   = df["crime_type"].map(SEVERITY_MAP).fillna(1).astype(np.int8)

    # Location type (ordinal risk encoding)
    raw_loc = df["Location Description"].fillna("OTHER").str.upper().str.strip()
    df["location_type_str"] = raw_loc.map(LOCATION_GROUPS).fillna("other")
    df["location_type"]     = (
        df["location_type_str"].map(LOCATION_RISK_ORDER).astype(np.int8)
    )

    # is_domestic — strongest correlate per EDA (0.192)
    df["is_domestic"] = df["Domestic"].astype(np.int8)

    # Community area — fill NaN with 0 (7.21% missing, do NOT drop rows)
    df["community_area"] = df["Community Area"].fillna(0).astype(np.int16)

    # Police district — fill NaN with 0 (only 47 rows missing)
    df["police_district"] = df["District"].fillna(0).astype(np.int8)

    return df


def build_grid(df: pd.DataFrame) -> pd.DataFrame:
    """
    Snap incidents to 200m grid cells.
    Fix: GRID_MULT=500 (0.002° ≈ 200m) not 100 (0.01° ≈ 1km).
    EDA showed lat×100 only produced 747 cells — far too coarse.
    """
    print("[6/8] Building 200m grid cells (GRID_MULT=500) ...")
    df["grid_lat"] = (df["Latitude"]  * GRID_MULT).round().astype(np.int32)
    df["grid_lon"] = (df["Longitude"] * GRID_MULT).round().astype(np.int32)

    density = (
        df.groupby(["grid_lat", "grid_lon"])
          .size()
          .reset_index(name="crime_count")
    )
    df = df.merge(density, on=["grid_lat", "grid_lon"], how="left")
    print(f"      Grid cells (200m): {len(density):,}  "
          f"| Max crime_count: {density['crime_count'].max():,}")
    return df


def compute_rolling_rate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rolling 7-day crime rate per 200m grid cell.
    Captures recency — confirmed as valuable by EDA Section 7.
    Note: takes 3–5 min on 8.5M rows.
    """
    print("[7/8] Computing rolling 7-day crime rate per grid cell ...")
    print("      (Takes 3–5 minutes on 8.5M rows — please wait ...)")

    df = df.sort_values("Date").reset_index(drop=True)
    df["date_only"] = df["Date"].dt.normalize()   # midnight of each day

    # Daily count per cell
    daily = (
        df.groupby(["grid_lat", "grid_lon", "date_only"])
          .size()
          .reset_index(name="daily_count")
    )

    # Rolling 7-day sum per cell
    parts = []
    for (gl, gln), grp in daily.groupby(["grid_lat", "grid_lon"]):
        grp = grp.set_index("date_only").sort_index()
        grp["rolling_7day"] = grp["daily_count"].rolling("7D", min_periods=1).sum()
        grp["grid_lat"] = gl
        grp["grid_lon"] = gln
        parts.append(grp.reset_index()[
            ["date_only", "grid_lat", "grid_lon", "rolling_7day"]
        ])

    rolling_df = pd.concat(parts, ignore_index=True)

    df = df.merge(rolling_df, on=["grid_lat", "grid_lon", "date_only"], how="left")
    df["rolling_7day"] = df["rolling_7day"].fillna(1).astype(np.float32)

    print(f"      Rolling 7-day — "
          f"mean: {df['rolling_7day'].mean():.2f}, "
          f"max: {df['rolling_7day'].max():.0f}")
    return df


def add_distance_to_police(df: pd.DataFrame) -> pd.DataFrame:
    """
    KD-tree nearest-neighbour lookup to the 25 Chicago police stations.
    If police_stations.csv is missing, fills with -1 and warns.
    """
    print("[8/8] Adding distance_to_police_station ...")

    if not os.path.exists(POLICE_PATH):
        print(f"      ⚠ {POLICE_PATH} not found.")
        print("        Download: data.cityofchicago.org → search 'Police Stations'")
        print("        Filling with -1 for now. Re-run after downloading.")
        df["distance_to_police"] = np.float32(-1)
        return df

    stations = pd.read_csv(POLICE_PATH)
    stations.columns = [c.strip().upper() for c in stations.columns]
    lat_col = next((c for c in stations.columns if "LAT" in c), None)
    lon_col = next((c for c in stations.columns if "LON" in c), None)

    if not lat_col or not lon_col:
        print(f"      ⚠ Lat/lon columns not found. Available: {list(stations.columns)}")
        df["distance_to_police"] = np.float32(-1)
        return df

    stations  = stations.dropna(subset=[lat_col, lon_col])
    s_coords  = np.radians(stations[[lat_col, lon_col]].values)
    c_coords  = np.radians(df[["Latitude", "Longitude"]].values)

    tree = cKDTree(s_coords)
    dists, _ = tree.query(c_coords, k=1)

    # radians → km  (Earth radius 6371 km)
    df["distance_to_police"] = (dists * 6371).astype(np.float32)
    print(f"      Distance stats — "
          f"mean: {df['distance_to_police'].mean():.2f} km, "
          f"max: {df['distance_to_police'].max():.2f} km")
    return df


def save(df: pd.DataFrame) -> None:
    FINAL_COLS = [
        # Spatial
        "Latitude", "Longitude", "grid_lat", "grid_lon",
        # Temporal
        "hour", "day_of_week", "month", "is_night", "is_weekend",
        # Density features
        "crime_count", "rolling_7day",
        # Crime features
        "crime_type", "location_type", "is_domestic",
        # Zone features
        "community_area", "police_district",
        # External
        "distance_to_police",
        # Target
        "severity",
    ]
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df[FINAL_COLS].to_csv(OUT_PATH, index=False)
    print(f"\n✓ Saved {len(df):,} rows × {len(FINAL_COLS)} columns → {OUT_PATH}")


def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║   SafeHer — Preprocessing v2 (post-EDA)             ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    df = load_raw()
    df = filter_chicago(df)
    df = parse_datetime(df)
    df = engineer_temporal(df)
    df = engineer_crime_features(df)
    df = build_grid(df)
    df = compute_rolling_rate(df)
    df = add_distance_to_police(df)
    save(df)

    print("\n── Final feature summary ──────────────────────────────")
    print(f"  Total features : 17 columns (16 features + 1 target)")
    print(f"  Total rows     : {len(df):,}")
    print(f"  Severity dist  :")
    for s, cnt in df["severity"].value_counts().sort_index().items():
        print(f"    Severity {s}: {cnt:>8,}  ({cnt/len(df)*100:.1f}%)")
    print(f"\n  Grid cells (200m): {df.groupby(['grid_lat','grid_lon']).ngroups:,}")
    print("\n  Next step: python train.py")


if __name__ == "__main__":
    main()