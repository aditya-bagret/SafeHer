# backend/routes_saferoute.py
# ─────────────────────────────────────────────────────────────────────────────
# SafeHer — Flask Blueprint for GET /api/safe-route
#
# Called by RouteMap.jsx when the user clicks "Find Safe Route".
# Fetches up to 3 alternative routes from Google Directions API,
# decodes each polyline, scores every waypoint using score_polyline_points()
# from the SAME risk_grid module used by /api/heatmap.
# Sorts routes by avg_risk and returns colour labels.
#
# Query params:
#   origin      (str)  — e.g. "41.8827,-87.6233"  or  "Chicago Union Station"
#   destination (str)  — e.g. "41.9742,-87.6684"  or  "Wrigley Field Chicago"
#   hour        (int)  — 0–23, matches the heatmap slider value
#   day         (int)  — 0–6, optional, defaults to today
#   month       (int)  — 1–12, optional, defaults to current month
#
# Response JSON:
# [
#   {
#     "route_index": 0,
#     "label": "safe",            ← "safe" | "moderate" | "high"
#     "avg_risk": 0.21,
#     "duration_text": "18 mins",
#     "distance_text": "4.2 mi",
#     "polyline": "ekp~Fb...",    ← encoded polyline string for Maps JS API
#     "color": "#22c55e"          ← hex colour for the polyline stroke
#   },
#   ...
# ]
# ─────────────────────────────────────────────────────────────────────────────

import os
import requests as http_requests
import polyline as pl

from flask import Blueprint, request, jsonify
from datetime import datetime
from risk_grid import score_polyline_points, risk_to_label

saferoute_bp = Blueprint("saferoute", __name__)

# ── Google Directions API ─────────────────────────────────────────────────────
DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
GOOGLE_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")

# Risk label → hex colour for the frontend polyline stroke
LABEL_COLORS = {
    "safe":     "#22c55e",   # green
    "moderate": "#f59e0b",   # amber
    "high":     "#ef4444",   # red
}


# ─────────────────────────────────────────────────────────────────────────────

def _fetch_directions(origin: str, destination: str) -> list:
    """
    Call Google Directions API with alternatives=true.
    Returns raw list of route dicts or raises on failure.
    """
    if not GOOGLE_API_KEY:
        raise EnvironmentError("GOOGLE_MAPS_API_KEY is not set in environment.")

    params = {
        "origin":       origin,
        "destination":  destination,
        "alternatives": "true",
        "mode":         "driving",
        "key":          GOOGLE_API_KEY,
    }
    resp = http_requests.get(DIRECTIONS_URL, params=params, timeout=8)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "OK":
        raise ValueError(f"Directions API returned status: {data.get('status')} "
                         f"— {data.get('error_message', '')}")

    return data["routes"]


def _decode_route(route: dict) -> list[tuple[float, float]]:
    """
    Decode the overview_polyline of a route into a list of (lat, lon) tuples.
    We sample every 5th point to keep scoring fast without losing accuracy.
    """
    encoded = route["overview_polyline"]["points"]
    points  = pl.decode(encoded)        # [(lat, lon), ...]
    return points[::5] if len(points) > 5 else points


def _format_route(route: dict, index: int, avg_risk: float) -> dict:
    """Build the response dict for one route."""
    leg         = route["legs"][0]
    label       = risk_to_label(avg_risk)

    return {
        "route_index":   index,
        "label":         label,
        "avg_risk":      avg_risk,
        "duration_text": leg["duration"]["text"],
        "distance_text": leg["distance"]["text"],
        "polyline":      route["overview_polyline"]["points"],
        "color":         LABEL_COLORS[label],
    }


# ─────────────────────────────────────────────────────────────────────────────

@saferoute_bp.route("/api/safe-route", methods=["GET"])
def get_safe_route():
    """
    Fetch Google Directions alternatives, score each route against the
    shared LightGBM risk grid, sort by safety, return ranked list.
    """

    # ── Parse params ──────────────────────────────────────────────────────────
    origin      = request.args.get("origin",      "").strip()
    destination = request.args.get("destination", "").strip()

    if not origin or not destination:
        return jsonify({"error": "Both 'origin' and 'destination' are required."}), 400

    now = datetime.now()

    try:
        hour  = int(request.args.get("hour",  now.hour))
        day   = int(request.args.get("day",   now.weekday()))
        month = int(request.args.get("month", now.month))
    except (ValueError, TypeError):
        return jsonify({"error": "hour, day, month must be integers."}), 400

    if not (0 <= hour <= 23):
        return jsonify({"error": "hour must be 0–23."}), 400
    if not (0 <= day <= 6):
        return jsonify({"error": "day must be 0–6."}), 400
    if not (1 <= month <= 12):
        return jsonify({"error": "month must be 1–12."}), 400

    # ── Fetch directions ──────────────────────────────────────────────────────
    try:
        raw_routes = _fetch_directions(origin, destination)
    except EnvironmentError as e:
        return jsonify({"error": str(e)}), 500
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Directions fetch failed: {str(e)}"}), 502

    if not raw_routes:
        return jsonify({"error": "No routes found between origin and destination."}), 404

    # ── Score each route ──────────────────────────────────────────────────────
    scored = []
    for i, route in enumerate(raw_routes):
        points   = _decode_route(route)
        avg_risk = score_polyline_points(points, hour, day, month)
        scored.append(_format_route(route, i, avg_risk))

    # ── Sort by risk ascending (safest first) ─────────────────────────────────
    scored.sort(key=lambda r: r["avg_risk"])

    return jsonify(scored), 200