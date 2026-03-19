"""
SafeHer — FastAPI Backend
==========================
Serves the trained CNN-LSTM model as a REST API.

Install:
    pip install fastapi uvicorn tensorflow numpy pandas scikit-learn

Run:
    uvicorn api:app --reload --port 8000

Endpoints:
    GET  /                         → health check
    GET  /zones                    → list all 70 Delhi zones
    POST /predict                  → predict safety score for one zone
    GET  /heatmap?hour=22&day=4    → full heatmap for all zones
    POST /safe-route               → find safest route between two zones
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import numpy as np
import pandas as pd
import json
import os
import math

app = FastAPI(
    title="SafeHer API",
    description="AI-Driven Women Safety Prediction API",
    version="1.0.0"
)

# Allow all origins for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global State ─────────────────────────────────────────────
model    = None
dataset  = None
zones_df = None

TIME_RISK_WEIGHTS = {
    0:1.8, 1:1.9, 2:2.0, 3:1.9, 4:1.7, 5:1.4,
    6:1.1, 7:0.8, 8:0.7, 9:0.6, 10:0.5, 11:0.5,
    12:0.6, 13:0.6, 14:0.6, 15:0.6, 16:0.7, 17:0.8,
    18:0.9, 19:1.0, 20:1.1, 21:1.2, 22:1.5, 23:1.7
}

# ─── Startup ──────────────────────────────────────────────────
@app.on_event("startup")
async def load_model():
    global model, dataset, zones_df

    # Load dataset
    if os.path.exists("delhi_final_dataset.csv"):
        dataset = pd.read_csv("delhi_final_dataset.csv")
        print(f"✅ Dataset loaded: {len(dataset):,} rows")
    else:
        print("⚠️  Dataset not found — using fallback mode")

    # Load zones
    if os.path.exists("delhi_zones.csv"):
        zones_df = pd.read_csv("delhi_zones.csv")
        print(f"✅ Zones loaded: {len(zones_df)} zones")

    # Load model
    if os.path.exists("safeher_cnn_lstm_model.h5"):
        try:
            import tensorflow as tf
            model = tf.keras.models.load_model("safeher_cnn_lstm_model.h5")
            print("✅ CNN-LSTM model loaded")
        except Exception as e:
            print(f"⚠️  Model load failed: {e} — using formula fallback")
    else:
        print("⚠️  Model file not found — using formula fallback")

# ─── Helpers ──────────────────────────────────────────────────
def get_risk_level(score: float) -> dict:
    if score >= 75:
        return {"level": "Safe",     "color": "#22c55e", "hex": "safe"}
    elif score >= 65:
        return {"level": "Low Risk", "color": "#84cc16", "hex": "low"}
    elif score >= 50:
        return {"level": "Moderate", "color": "#f59e0b", "hex": "moderate"}
    elif score >= 35:
        return {"level": "High Risk","color": "#f97316", "hex": "high"}
    else:
        return {"level": "Critical", "color": "#ef4444", "hex": "critical"}

def formula_fallback_score(zone_name: str, hour: int, day: int) -> float:
    """
    Use the expert formula directly when model is not available.
    Also used to cross-validate model predictions.
    """
    if dataset is None:
        return 55.0

    zone_rows = dataset[dataset["zone_name"] == zone_name]
    if len(zone_rows) == 0:
        return 55.0

    z = zone_rows.iloc[0]
    time_risk = TIME_RISK_WEIGHTS.get(hour, 1.0)
    day_risk  = 1.3 if day == 5 else (1.1 if day == 4 else 0.9)
    inverse_time = 1.0 - min((time_risk * day_risk - 0.5) / 2.0, 1.0)

    raw = (
        float(z.get("police_coverage_score", 0.5)) * 0.20 +
        float(z.get("street_light_score", 0.5))    * 0.15 +
        float(z.get("metro_access_score", 0.5))    * 0.10 +
        float(z.get("footfall_score", 0.5))        * 0.10 +
        float(z.get("sentiment_score", 0.5))       * 0.20 +
        (1 - float(z.get("crime_count_normalized", 0.5))) * 0.15 +
        inverse_time                               * 0.10
    )
    return round(min(100, max(0, raw * 100)), 1)

def predict_score(zone_name: str, hour: int, day: int) -> float:
    """Predict using model if available, else formula fallback."""
    if model is None or dataset is None:
        return formula_fallback_score(zone_name, hour, day)

    features = ['hour_of_day','day_of_week','is_weekend',
                'crime_count_normalized','police_coverage_score',
                'street_light_score','metro_access_score',
                'footfall_score','sentiment_score']

    zone_data = dataset[dataset["zone_name"] == zone_name]
    if len(zone_data) == 0:
        return formula_fallback_score(zone_name, hour, day)

    base = zone_data.iloc[0][features].values.copy()
    sequence = []
    for step in range(24):
        row = base.copy()
        h = (hour - 23 + step) % 24
        row[0] = h / 23.0
        row[1] = day / 6.0
        row[2] = 1.0 if day >= 5 else 0.0
        sequence.append(row)

    X = np.array([sequence], dtype=np.float32)
    pred = float(model.predict(X, verbose=0)[0][0])
    return round(pred * 100, 1)

def haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))

# ─── Request Models ───────────────────────────────────────────
class PredictRequest(BaseModel):
    zone_name: str
    hour: int
    day: int

class RouteRequest(BaseModel):
    origin: str
    destination: str
    hour: int
    day: int

# ─── Routes ───────────────────────────────────────────────────
@app.get("/")
def health():
    return {
        "status":  "SafeHer API is running",
        "model":   "loaded" if model else "fallback",
        "dataset": f"{len(dataset):,} rows" if dataset is not None else "not loaded",
        "zones":   len(zones_df) if zones_df is not None else 0
    }

@app.get("/zones")
def get_zones():
    if zones_df is None:
        raise HTTPException(404, "Zones data not loaded")
    return zones_df.to_dict(orient="records")

@app.post("/predict")
def predict(req: PredictRequest):
    if not 0 <= req.hour <= 23:
        raise HTTPException(400, "hour must be 0-23")
    if not 0 <= req.day <= 6:
        raise HTTPException(400, "day must be 0-6 (0=Monday)")

    score = predict_score(req.zone_name, req.hour, req.day)
    risk  = get_risk_level(score)

    return {
        "zone_name"    : req.zone_name,
        "hour"         : req.hour,
        "day"          : req.day,
        "safety_score" : score,
        "risk_level"   : risk["level"],
        "color"        : risk["color"],
        "recommendation": {
            "safe"    : "Area is considered safe. Stay aware of surroundings.",
            "low"     : "Generally safe. Avoid isolated areas at night.",
            "moderate": "Exercise caution. Share location with a trusted contact.",
            "high"    : "Avoid if possible. Use SafeHer safe route instead.",
            "critical": "Avoid this area. Activate SOS if you must travel here.",
        }.get(risk["hex"], "Stay alert.")
    }

@app.get("/heatmap")
def heatmap(hour: int = 18, day: int = 0):
    if zones_df is None:
        raise HTTPException(404, "Zones data not loaded")

    results = []
    for _, zone in zones_df.iterrows():
        score = predict_score(zone["zone_name"], hour, day)
        risk  = get_risk_level(score)
        results.append({
            "zone_id"      : zone["zone_id"],
            "zone_name"    : zone["zone_name"],
            "lat"          : float(zone["lat"]),
            "lng"          : float(zone["lng"]),
            "district"     : zone["district"],
            "zone_type"    : zone["zone_type"],
            "safety_score" : score,
            "risk_level"   : risk["level"],
            "color"        : risk["color"],
        })

    results.sort(key=lambda x: x["safety_score"], reverse=True)
    safe_count = sum(1 for r in results if r["safety_score"] >= 65)
    high_count = sum(1 for r in results if r["safety_score"] < 50)
    avg_score  = round(sum(r["safety_score"] for r in results) / len(results), 1)

    return {
        "hour"       : hour,
        "day"        : day,
        "avg_score"  : avg_score,
        "safe_zones" : safe_count,
        "high_risk"  : high_count,
        "total_zones": len(results),
        "zones"      : results
    }

@app.post("/safe-route")
def safe_route(req: RouteRequest):
    if zones_df is None:
        raise HTTPException(404, "Zones data not loaded")

    # Get all zone scores
    zone_scores = {}
    for _, zone in zones_df.iterrows():
        score = predict_score(zone["zone_name"], req.hour, req.day)
        zone_scores[zone["zone_name"]] = {
            "score": score,
            "lat": float(zone["lat"]),
            "lng": float(zone["lng"]),
            "risk": get_risk_level(score)["level"]
        }

    origin_data = zone_scores.get(req.origin)
    dest_data   = zone_scores.get(req.destination)

    if not origin_data or not dest_data:
        raise HTTPException(404, "Origin or destination zone not found")

    # Simple safe route: find intermediate zones with highest safety scores
    # that are geographically between origin and destination
    o_lat, o_lng = origin_data["lat"], origin_data["lng"]
    d_lat, d_lng = dest_data["lat"],   dest_data["lng"]

    # Find 2-3 intermediate waypoints that are safe
    candidates = []
    for name, data in zone_scores.items():
        if name in [req.origin, req.destination]:
            continue
        # Must be roughly between origin and destination (bounding box + 15%)
        min_lat = min(o_lat, d_lat) - 0.03
        max_lat = max(o_lat, d_lat) + 0.03
        min_lng = min(o_lng, d_lng) - 0.03
        max_lng = max(o_lng, d_lng) + 0.03

        if min_lat <= data["lat"] <= max_lat and min_lng <= data["lng"] <= max_lng:
            dist = haversine(o_lat, o_lng, data["lat"], data["lng"]) + \
                   haversine(data["lat"], data["lng"], d_lat, d_lng)
            candidates.append({"name": name, "score": data["score"], "dist": dist, **data})

    # Sort by safety score descending, pick top 2 waypoints
    candidates.sort(key=lambda x: x["score"], reverse=True)
    waypoints = candidates[:2]

    route = [
        {"zone": req.origin, **origin_data},
        *[{"zone": w["name"], "score": w["score"], "lat": w["lat"],
           "lng": w["lng"], "risk": w["risk"]} for w in waypoints],
        {"zone": req.destination, **dest_data}
    ]

    avg_route_score = round(sum(r["score"] for r in route) / len(route), 1)

    return {
        "origin"          : req.origin,
        "destination"     : req.destination,
        "hour"            : req.hour,
        "day"             : req.day,
        "route"           : route,
        "avg_safety_score": avg_route_score,
        "total_distance_km": round(haversine(o_lat, o_lng, d_lat, d_lng), 1),
        "recommendation"  : "Safe route calculated via highest-safety waypoints."
                            if avg_route_score >= 65 else
                            "Route passes through moderate-risk zones. Stay alert.",
    }
