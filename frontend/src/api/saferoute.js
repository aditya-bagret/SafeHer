// frontend/src/api/saferoute.js
// ─────────────────────────────────────────────────────────────────────────────
// SafeHer — Fetch wrapper for GET /api/safe-route
// Called by RouteMap.jsx when the user clicks "Find Safe Route".
// ─────────────────────────────────────────────────────────────────────────────

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:5000";

/**
 * Fetch ranked safe route alternatives between origin and destination.
 *
 * @param {string} origin       — address string or "lat,lon"
 * @param {string} destination  — address string or "lat,lon"
 * @param {number} hour         — 0–23 (from shared hour slider)
 * @param {number} day          — 0–6  (Mon=0, Sun=6)
 * @returns {Promise<Array<{
 *   route_index:   number,
 *   label:         "safe"|"moderate"|"high",
 *   avg_risk:      number,
 *   duration_text: string,
 *   distance_text: string,
 *   polyline:      string,
 *   color:         string,
 * }>>}
 */
export async function fetchSafeRoute(origin, destination, hour, day) {
  const params = new URLSearchParams({
    origin,
    destination,
    hour:  String(hour),
    day:   String(day),
  });

  const url = `${BASE_URL}/api/safe-route?${params.toString()}`;

  const response = await fetch(url, {
    method:  "GET",
    headers: { "Content-Type": "application/json" },
    signal:  AbortSignal.timeout(75_000), // 75s — Render cold start + Google Directions
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || `Safe-route API error: ${response.status}`);
  }

  const data = await response.json();

  if (!Array.isArray(data) || data.length === 0) {
    throw new Error("No routes found between origin and destination.");
  }

  return data; // sorted by avg_risk ascending — safest route is index 0
}