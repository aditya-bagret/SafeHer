# backend/routes_heatmap.py
# ─────────────────────────────────────────────────────────────────────────────
# SafeHer — Flask Blueprint for GET /api/heatmap
#
# Called by HeatMap.jsx every time the user moves the hour slider.
# Uses generate_risk_grid() from risk_grid.py — same grid object as
# the safe-route endpoint, ensuring mathematical consistency.
#
# Query params:
#   hour  (int, 0–23)   — required
#   day   (int, 0–6)    — optional, defaults to today
#   month (int, 1–12)   — optional, defaults to current month
#
# Response JSON:
# [
#   { "lat": 41.88, "lon": -87.63, "risk": 0.72 },
#   ...
# ]
# ─────────────────────────────────────────────────────────────────────────────

from flask import Blueprint, request, jsonify
from datetime import datetime
from risk_grid import generate_risk_grid

heatmap_bp = Blueprint("heatmap", __name__)


@heatmap_bp.route("/api/heatmap", methods=["GET"])
def get_heatmap():
    """
    Returns a list of {lat, lon, risk} dicts for every ~200m grid cell
    in the Chicago bounding box, scored for the requested hour/day/month.
    """

    # ── Parse query params ────────────────────────────────────────────────────
    now = datetime.now()

    try:
        hour = int(request.args.get("hour", now.hour))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid 'hour' param. Must be integer 0–23."}), 400

    try:
        day = int(request.args.get("day", now.weekday()))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid 'day' param. Must be integer 0–6."}), 400

    try:
        month = int(request.args.get("month", now.month))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid 'month' param. Must be integer 1–12."}), 400

    # ── Validate ranges ───────────────────────────────────────────────────────
    if not (0 <= hour <= 23):
        return jsonify({"error": "hour must be 0–23."}), 400
    if not (0 <= day <= 6):
        return jsonify({"error": "day must be 0–6 (Mon–Sun)."}), 400
    if not (1 <= month <= 12):
        return jsonify({"error": "month must be 1–12."}), 400

    # ── Generate risk grid ────────────────────────────────────────────────────
    try:
        df = generate_risk_grid(hour=hour, day=day, month=month)
    except Exception as e:
        return jsonify({"error": f"Grid generation failed: {str(e)}"}), 500

    # ── Filter out zero-risk cells to reduce payload size ─────────────────────
    # The frontend only needs cells with risk > 0 for the HeatmapLayer weights
    df_filtered = df[df["risk"] > 0.0]

    # ── Serialise ─────────────────────────────────────────────────────────────
    payload = df_filtered[["lat", "lon", "risk"]].to_dict(orient="records")

    return jsonify(payload), 200