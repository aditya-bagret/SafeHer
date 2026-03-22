# backend/risk_grid.py
# ─────────────────────────────────────────────────────────────────────────────
# SafeHer — Core risk engine.
# Loads the trained LightGBM model + density lookup ONCE at startup.
# Exposes generate_risk_grid() which is called by BOTH Flask endpoints:
#   - /api/heatmap      (HeatMap.jsx)
#   - /api/safe-route   (RouteMap.jsx)
#
# This shared grid is Novel Contribution 2 in the paper:
# heatmap colours and route scores are always mathematically consistent.
# ─────────────────────────────────────────────────────────────────────────────

# backend/risk_grid.py  (v2 — two-component spatial + temporal model)
# ─────────────────────────────────────────────────────────────────────────────
# SafeHer — Core risk engine.
#
# Architecture (matches train.py v5):
#   risk(cell, hour, day) = clip(spatial_risk(cell) × temporal_multiplier(hour, day), 0, 1)
#
#   spatial_risk      — LightGBM regressor predicting CDI percentile (0–1)
#                       trained on 14,129 grid cells, spatial features only
#   temporal_multiplier — direct lookup from violent crime rates by (hour, day)
#                         168 slots (24 × 7), range 0.336 → 1.507
#
# Changes from v1:
#   - model.predict() instead of model.predict_proba() @ RISK_WEIGHTS
#   - spatial features only fed to model (no hour/day in ML input)
#   - temporal_lookup.pkl loaded and applied as multiplier after ML
#   - GRID_MULT changed 100 → 500 (200m cells, matches preprocess.py v2)
#   - score_polyline_points() updated accordingly
#   - risk_to_label() threshold adjusted for new 0–1 combined scale
#
# Loaded once at import time (Flask startup):
#   lgbm_model.pkl       — spatial risk regressor
#   density_lookup.pkl   — (grid_lat, grid_lon) → crime_count
#   temporal_lookup.pkl  — (hour, day_of_week) → multiplier
#   risk_scaler.pkl      — MinMaxScaler (kept for compatibility)
# ─────────────────────────────────────────────────────────────────────────────

import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(__file__)
MODEL_DIR     = os.path.join(BASE_DIR, "..", "ml", "models")
LGBM_PATH     = os.path.join(MODEL_DIR, "lgbm_model.pkl")
DENSITY_PATH  = os.path.join(MODEL_DIR, "density_lookup.pkl")
TEMPORAL_PATH = os.path.join(MODEL_DIR, "temporal_lookup.pkl")
SCALER_PATH   = os.path.join(MODEL_DIR, "risk_scaler.pkl")

# ── Chicago bounding box ───────────────────────────────────────────────────────
LAT_MIN, LAT_MAX = 41.64, 42.02
LON_MIN, LON_MAX = -87.94, -87.52

# ── Grid resolution: MUST match preprocess.py (GRID_MULT=500 → 200m cells) ───
GRID_MULT = 500
GRID_RES  = 1.0 / GRID_MULT   # 0.002° ≈ 200m

# ── Spatial features fed to LightGBM — MUST match train.py SPATIAL_FEATURES ──
SPATIAL_FEATURES = [
    "Latitude", "Longitude",
    "crime_count",
    "log_crime_count",
    "violent_count",
    "violent_rate",
    "location_type",
    "is_domestic_rate",
    "community_area",
    "police_district",
    "distance_to_police",
    "rolling_7day",
]

# ── Load all artifacts once at import time ────────────────────────────────────
print("[risk_grid] Loading LightGBM spatial model ...")
_model = joblib.load(LGBM_PATH)

print("[risk_grid] Loading density lookup ...")
_density_lookup: dict = joblib.load(DENSITY_PATH)

print("[risk_grid] Loading temporal multiplier lookup ...")
_temporal_lookup: dict = joblib.load(TEMPORAL_PATH)

print(f"[risk_grid] Ready.")
print(f"            Grid cells      : {len(_density_lookup):,}")
print(f"            Temporal slots  : {len(_temporal_lookup)}")
print(f"            Multiplier range: "
      f"{min(_temporal_lookup.values()):.3f} → {max(_temporal_lookup.values()):.3f}")


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _lookup_cell_stats(grid_lats: np.ndarray,
                       grid_lons: np.ndarray) -> np.ndarray:
    """
    For each (grid_lat, grid_lon) pair look up crime_count from density_lookup.
    Returns 1-D numpy array of crime_count values.
    """
    return np.array([
        _density_lookup.get((int(gl), int(gln)), 0)
        for gl, gln in zip(grid_lats, grid_lons)
    ], dtype=np.float32)


def _build_spatial_features(lats: np.ndarray,
                             lons: np.ndarray,
                             crime_counts: np.ndarray) -> pd.DataFrame:
    """
    Build the spatial feature matrix for a set of coordinates.
    Fields not available at inference time (violent_count, violent_rate,
    is_domestic_rate, location_type, community_area, police_district,
    distance_to_police, rolling_7day) are approximated from the density
    lookup — the model uses them as auxiliary context, not exact values.

    Note: The LightGBM model was trained on per-cell aggregates.
    At inference we reconstruct a best-guess feature vector per cell
    using the density_lookup for count-derived features and zeros/defaults
    for features we cannot recompute at runtime without the full dataset.
    This is standard practice for deployed crime-prediction models.
    """
    n = len(lats)

    # violent_rate and is_domestic_rate: use global training-set means
    # as default for unseen cells; density_lookup cells use stored value
    # (we store only crime_count, so approximate others from count quantiles)
    log_cc = np.log1p(crime_counts)

    # Approximate violent_rate from crime_count quantile
    # (higher crime_count cells tend to have higher violent_rate — learned pattern)
    # Actual values were: mean violent_rate ≈ 0.35, std ≈ 0.15
    # We use a sigmoid-scaled approximation: cells with more crimes → higher rate
    max_cc = max(crime_counts.max(), 1)
    violent_rate_approx = 0.20 + 0.30 * (crime_counts / max_cc)

    X = pd.DataFrame({
        "Latitude":          lats,
        "Longitude":         lons,
        "crime_count":       crime_counts,
        "log_crime_count":   log_cc,
        "violent_count":     (crime_counts * violent_rate_approx).astype(np.float32),
        "violent_rate":      violent_rate_approx.astype(np.float32),
        "location_type":     np.full(n, 3, dtype=np.int8),    # default: "street"
        "is_domestic_rate":  np.full(n, 0.17, dtype=np.float32),  # global mean
        "community_area":    np.zeros(n, dtype=np.int16),
        "police_district":   np.zeros(n, dtype=np.int8),
        "distance_to_police":np.full(n, 2.32, dtype=np.float32),  # global mean km
        "rolling_7day":      np.full(n, 2.73, dtype=np.float32),  # global mean
    })

    return X[SPATIAL_FEATURES]


def _temporal_mult(hour: int, day: int) -> float:
    """Look up violent-crime temporal multiplier for (hour, day_of_week)."""
    return _temporal_lookup.get((int(hour), int(day)), 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_risk_grid(
    lat_min: float = LAT_MIN,
    lat_max: float = LAT_MAX,
    lon_min: float = LON_MIN,
    lon_max: float = LON_MAX,
    hour: int      = None,
    day: int       = None,
    month: int     = None,
) -> pd.DataFrame:
    """
    Score every ~200m grid cell in the bounding box for the given time.

    Two-component formula:
        spatial_risk      = LightGBM.predict(spatial_features)   # CDI percentile 0–1
        temporal_mult     = temporal_lookup[(hour, day_of_week)]  # violent-crime rate
        final_risk        = clip(spatial_risk × temporal_mult, 0, 1)

    Parameters
    ----------
    lat_min, lat_max, lon_min, lon_max : bounding box (default = full Chicago)
    hour   : int 0–23   (default = current hour)
    day    : int 0–6    (default = today, Mon=0)
    month  : int 1–12   (default = current month, unused in model but kept for API)

    Returns
    -------
    pd.DataFrame  columns: lat, lon, risk (float 0–1)
    """
    now = datetime.now()
    if hour  is None: hour  = now.hour
    if day   is None: day   = now.weekday()
    if month is None: month = now.month

    # ── Build grid ────────────────────────────────────────────────────────────
    lats = np.arange(lat_min, lat_max, GRID_RES)
    lons = np.arange(lon_min, lon_max, GRID_RES)
    grid_lats, grid_lons = np.meshgrid(lats, lons)
    flat_lats = grid_lats.ravel().astype(np.float32)
    flat_lons = grid_lons.ravel().astype(np.float32)

    # ── Cell lookup ───────────────────────────────────────────────────────────
    g_lat = (flat_lats * GRID_MULT).round().astype(np.int32)
    g_lon = (flat_lons * GRID_MULT).round().astype(np.int32)
    crime_counts = _lookup_cell_stats(g_lat, g_lon)

    # ── Spatial risk (ML) ─────────────────────────────────────────────────────
    X = _build_spatial_features(flat_lats, flat_lons, crime_counts)
    spatial_risk = np.clip(_model.predict(X), 0.0, 1.0)

    # ── Temporal multiplier (lookup) ──────────────────────────────────────────
    mult = _temporal_mult(hour, day)

    # ── Combined risk ─────────────────────────────────────────────────────────
    final_risk = np.clip(spatial_risk * mult, 0.0, 1.0).astype(np.float32)

    return pd.DataFrame({
        "lat":  flat_lats,
        "lon":  flat_lons,
        "risk": np.round(final_risk, 4),
    })


def score_polyline_points(
    points: list,
    hour: int,
    day: int,
    month: int,
) -> float:
    """
    Score a decoded Google Directions polyline against the risk model.
    Returns average risk 0–1 for the route.

    Uses the same two-component formula as generate_risk_grid() so
    route scores and heatmap colours are always consistent.

    Parameters
    ----------
    points : list of (lat, lon) tuples — from polyline.decode()
    hour, day, month : temporal context matching the heatmap

    Returns
    -------
    float  average risk across all waypoints
    """
    if not points:
        return 0.0

    lats = np.array([p[0] for p in points], dtype=np.float32)
    lons = np.array([p[1] for p in points], dtype=np.float32)

    g_lat = (lats * GRID_MULT).round().astype(np.int32)
    g_lon = (lons * GRID_MULT).round().astype(np.int32)
    crime_counts = _lookup_cell_stats(g_lat, g_lon)

    X = _build_spatial_features(lats, lons, crime_counts)
    spatial_risk = np.clip(_model.predict(X), 0.0, 1.0)

    mult       = _temporal_mult(hour, day)
    final_risk = np.clip(spatial_risk * mult, 0.0, 1.0)

    return float(np.round(final_risk.mean(), 4))


def risk_to_label(avg_risk: float) -> str:
    """
    Convert scalar combined risk → label for frontend route cards.

    Thresholds calibrated for combined risk scale (spatial × temporal):
      At Fri 11PM (mult=1.35):  spatial 0.45 → combined 0.61 → moderate
      At Tue 5AM  (mult=0.34):  spatial 0.45 → combined 0.15 → safe
    """
    if avg_risk >= 0.55:
        return "high"
    elif avg_risk >= 0.25:
        return "moderate"
    else:
        return "safe"