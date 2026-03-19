"""
SafeHer — Flask Backend
========================
Install:  pip install flask flask-cors pandas numpy
Run:      python api.py

Endpoints:
    GET  /                          → health check
    GET  /zones                     → all 70 Delhi zones
    GET  /heatmap?hour=22&day=4     → full heatmap
    POST /predict                   → single zone prediction
    POST /safe-route                → safe route between zones
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import pandas as pd
import math
import os

app = Flask(__name__)
CORS(app)

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

def load_resources():
    global model, dataset, zones_df

    if os.path.exists("delhi_final_dataset.csv"):
        dataset = pd.read_csv("delhi_final_dataset.csv")
        print(f"✅ Dataset loaded: {len(dataset):,} rows")

    if os.path.exists("delhi_zones.csv"):
        zones_df = pd.read_csv("delhi_zones.csv")
        print(f"✅ Zones loaded: {len(zones_df)} zones")

    if not os.path.exists("safeher_cnn_lstm_model.h5"):
        print("⚠️  Model file not found — formula fallback active")
        return

    # Strategy 1: standard load
    try:
        import tensorflow as tf
        model = tf.keras.models.load_model("safeher_cnn_lstm_model.h5")
        print("✅ CNN-LSTM model loaded")
        return
    except Exception as e:
        print(f"   Standard load failed: {e}")

    # Strategy 2: rebuild + load weights
    try:
        import tensorflow as tf
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import Conv1D, MaxPooling1D, LSTM, Dense, Dropout, BatchNormalization
        m = Sequential([
            Conv1D(64, 3, activation="relu", padding="same", input_shape=(24, 9)),
            BatchNormalization(), MaxPooling1D(2),
            Conv1D(128, 3, activation="relu", padding="same"),
            BatchNormalization(), MaxPooling1D(2),
            LSTM(128, return_sequences=False),
            Dropout(0.3), Dense(64, activation="relu"),
            Dropout(0.2), Dense(1, activation="sigmoid")
        ])
        m.load_weights("safeher_cnn_lstm_model.h5")
        model = m
        print("✅ CNN-LSTM loaded via weight reconstruction")
        return
    except Exception as e:
        print(f"   Weight reconstruction failed: {e}")

    print("ℹ️  Using expert formula fallback")

# ─── Helpers ──────────────────────────────────────────────────
def get_risk_level(score):
    if score >= 75: return {"level": "Safe",      "color": "#22c55e", "hex": "safe"}
    if score >= 65: return {"level": "Low Risk",  "color": "#84cc16", "hex": "low"}
    if score >= 50: return {"level": "Moderate",  "color": "#f59e0b", "hex": "moderate"}
    if score >= 35: return {"level": "High Risk", "color": "#f97316", "hex": "high"}
    return             {"level": "Critical",   "color": "#ef4444", "hex": "critical"}

def formula_score(zone_name, hour, day):
    if dataset is None: return 55.0
    rows = dataset[dataset["zone_name"] == zone_name]
    if len(rows) == 0: return 55.0
    z = rows.iloc[0]
    time_risk    = TIME_RISK_WEIGHTS.get(hour, 1.0)
    day_risk     = 1.3 if day == 5 else (1.1 if day == 4 else 0.9)
    inverse_time = 1.0 - min((time_risk * day_risk - 0.5) / 2.0, 1.0)
    raw = (
        float(z.get("police_coverage_score", 0.5)) * 0.20 +
        float(z.get("street_light_score",    0.5)) * 0.15 +
        float(z.get("metro_access_score",    0.5)) * 0.10 +
        float(z.get("footfall_score",        0.5)) * 0.10 +
        float(z.get("sentiment_score",       0.5)) * 0.20 +
        (1 - float(z.get("crime_count_normalized", 0.5))) * 0.15 +
        inverse_time * 0.10
    )
    return round(min(100, max(0, raw * 100)), 1)

def predict_score(zone_name, hour, day):
    if model is None or dataset is None:
        return formula_score(zone_name, hour, day)
    features = ['hour_of_day','day_of_week','is_weekend','crime_count_normalized',
                'police_coverage_score','street_light_score','metro_access_score',
                'footfall_score','sentiment_score']
    rows = dataset[dataset["zone_name"] == zone_name]
    if len(rows) == 0: return formula_score(zone_name, hour, day)
    base = rows.iloc[0][features].values.copy().astype(float)
    sequence = []
    for step in range(24):
        row = base.copy()
        h = (hour - 23 + step) % 24
        row[0] = h / 23.0
        row[1] = day / 6.0
        row[2] = 1.0 if day >= 5 else 0.0
        sequence.append(row)
    X    = np.array([sequence], dtype=np.float32)
    pred = float(model.predict(X, verbose=0)[0][0])
    return round(pred * 100, 1)

def haversine(lat1, lng1, lat2, lng2):
    R    = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a    = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))

# ─── Routes ───────────────────────────────────────────────────
@app.route("/")
def health():
    return jsonify({
        "status" : "SafeHer API running ✅",
        "model"  : "CNN-LSTM loaded" if model else "formula fallback",
        "dataset": f"{len(dataset):,} rows" if dataset is not None else "not loaded",
        "zones"  : len(zones_df) if zones_df is not None else 0
    })

@app.route("/zones")
def get_zones():
    if zones_df is None:
        return jsonify({"error": "Zones not loaded"}), 404
    return jsonify(zones_df.to_dict(orient="records"))

@app.route("/predict", methods=["POST"])
def predict():
    body      = request.get_json() or {}
    zone_name = body.get("zone_name")
    hour      = int(body.get("hour", 18))
    day       = int(body.get("day",  0))
    if not zone_name:
        return jsonify({"error": "zone_name required"}), 400
    score = predict_score(zone_name, hour, day)
    risk  = get_risk_level(score)
    recs  = {
        "safe":"Area is considered safe. Stay aware of surroundings.",
        "low":"Generally safe. Avoid isolated areas at night.",
        "moderate":"Exercise caution. Share location with a trusted contact.",
        "high":"Avoid if possible. Use SafeHer safe route instead.",
        "critical":"Avoid this area. Activate SOS if you must travel here.",
    }
    return jsonify({
        "zone_name":"safe_score", "hour":hour, "day":day,
        "zone_name":zone_name, "safety_score":score,
        "risk_level":risk["level"], "color":risk["color"],
        "recommendation":recs.get(risk["hex"],"Stay alert.")
    })

@app.route("/heatmap")
def heatmap():
    if zones_df is None:
        return jsonify({"error": "Zones not loaded"}), 404
    hour    = int(request.args.get("hour", 18))
    day     = int(request.args.get("day",  0))
    results = []
    for _, zone in zones_df.iterrows():
        score = predict_score(zone["zone_name"], hour, day)
        risk  = get_risk_level(score)
        results.append({
            "zone_id":zone["zone_id"], "zone_name":zone["zone_name"],
            "lat":float(zone["lat"]), "lng":float(zone["lng"]),
            "district":zone["district"], "zone_type":zone["zone_type"],
            "safety_score":score, "risk_level":risk["level"], "color":risk["color"],
        })
    results.sort(key=lambda x: x["safety_score"], reverse=True)
    avg  = round(sum(r["safety_score"] for r in results) / len(results), 1)
    safe = sum(1 for r in results if r["safety_score"] >= 65)
    high = sum(1 for r in results if r["safety_score"] < 50)
    return jsonify({"hour":hour,"day":day,"avg_score":avg,"safe_zones":safe,
                    "high_risk":high,"total_zones":len(results),"zones":results})

@app.route("/safe-route", methods=["POST"])
def safe_route():
    if zones_df is None:
        return jsonify({"error": "Zones not loaded"}), 404
    body        = request.get_json() or {}
    origin      = body.get("origin")
    destination = body.get("destination")
    hour        = int(body.get("hour", 18))
    day         = int(body.get("day",  0))
    if not origin or not destination:
        return jsonify({"error": "origin and destination required"}), 400

    zone_scores = {}
    for _, zone in zones_df.iterrows():
        score = predict_score(zone["zone_name"], hour, day)
        zone_scores[zone["zone_name"]] = {
            "score":score, "lat":float(zone["lat"]),
            "lng":float(zone["lng"]), "risk":get_risk_level(score)["level"]
        }

    o = zone_scores.get(origin)
    d = zone_scores.get(destination)
    if not o or not d:
        return jsonify({"error": "Zone not found"}), 404

    candidates = []
    for name, z in zone_scores.items():
        if name in [origin, destination]: continue
        if (min(o["lat"],d["lat"])-0.04 <= z["lat"] <= max(o["lat"],d["lat"])+0.04 and
            min(o["lng"],d["lng"])-0.04 <= z["lng"] <= max(o["lng"],d["lng"])+0.04):
            dist = haversine(o["lat"],o["lng"],z["lat"],z["lng"]) + \
                   haversine(z["lat"],z["lng"],d["lat"],d["lng"])
            candidates.append({**z, "name":name, "dist":dist})

    candidates.sort(key=lambda x: x["score"], reverse=True)
    waypoints = candidates[:2]
    route = ([{"zone":origin,**o}] +
             [{"zone":w["name"],"score":w["score"],"lat":w["lat"],"lng":w["lng"],"risk":w["risk"]} for w in waypoints] +
             [{"zone":destination,**d}])
    avg = round(sum(r["score"] for r in route) / len(route), 1)

    return jsonify({
        "origin":origin, "destination":destination,
        "route":route, "avg_safety_score":avg,
        "total_distance_km":round(haversine(o["lat"],o["lng"],d["lat"],d["lng"]),1),
        "recommendation":"Safe route calculated." if avg >= 65 else "Route passes moderate-risk zones. Stay alert."
    })

# ─── Entry Point ──────────────────────────────────────────────
if __name__ == "__main__":
    load_resources()
    print("\n🛡️  SafeHer Flask API → http://127.0.0.1:8000\n")
    app.run(host="0.0.0.0", port=8000, debug=True)