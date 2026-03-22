// frontend/src/api/heatmap.js
// ─────────────────────────────────────────────────────────────────────────────
// SafeHer — Fetch wrapper for GET /api/heatmap
// Called by HeatMap.jsx every time the hour or day prop changes.
// ─────────────────────────────────────────────────────────────────────────────

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:5000";

/**
 * Fetch risk scores for all ~200m grid cells in Chicago at a given time.
 *
 * @param {number} hour  0–23
 * @param {number} day   0–6 (Mon=0, Sun=6)
 * @returns {Promise<Array<{lat: number, lon: number, risk: number}>>}
 */
export async function fetchHeatmap(hour, day) {
  const url = `${BASE_URL}/api/heatmap?hour=${hour}&day=${day}`;

  const response = await fetch(url, {
    method:  "GET",
    headers: { "Content-Type": "application/json" },
    signal:  AbortSignal.timeout(15_000), // 15s timeout
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || `Heatmap API error: ${response.status}`);
  }

  const data = await response.json();

  // Validate response shape
  if (!Array.isArray(data)) {
    throw new Error("Heatmap API returned unexpected format.");
  }

  return data; // [{lat, lon, risk}, ...]
}