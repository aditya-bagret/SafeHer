// frontend/src/components/HeatMap.jsx
// ─────────────────────────────────────────────────────────────────────────────
// SafeHer — Google Maps HeatmapLayer component.
// Re-fetches /api/heatmap every time hour or day prop changes.
// Renders a green→yellow→orange→red gradient over Chicago.
// Novel Contribution 5: heatmap visibly changes as user drags the hour slider.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect, useRef, useState, useCallback } from "react";
import { fetchHeatmap } from "../api/heatmap";

// Chicago centre
const CHICAGO_CENTER = { lat: 41.8781, lng: -87.6298 };

// HeatmapLayer gradient: transparent → green → yellow → orange → red
// Matches risk_to_label() thresholds in risk_grid.py
const HEATMAP_GRADIENT = [
  "rgba(0,0,0,0)",         // 0.0 — transparent (no risk)
  "rgba(34,197,94,0.3)",   // 0.2 — safe (green, faint)
  "rgba(34,197,94,0.8)",   // 0.3 — safe (green)
  "rgba(245,158,11,0.7)",  // 0.45 — moderate (amber)
  "rgba(249,115,22,0.85)", // 0.6  — high moderate (orange)
  "rgba(239,68,68,0.9)",   // 0.75 — high (red)
  "rgba(220,38,38,1.0)",   // 1.0  — maximum risk (deep red)
];

// Dark map style — makes heatmap colours pop against the dark background
const DARK_MAP_STYLE = [
  { elementType: "geometry",          stylers: [{ color: "#0f1218" }] },
  { elementType: "labels.text.fill",  stylers: [{ color: "#5a6380" }] },
  { elementType: "labels.text.stroke",stylers: [{ color: "#0a0c10" }] },
  {
    featureType: "road",
    elementType: "geometry",
    stylers: [{ color: "#1e2330" }],
  },
  {
    featureType: "road.arterial",
    elementType: "geometry",
    stylers: [{ color: "#252d3d" }],
  },
  {
    featureType: "road.highway",
    elementType: "geometry",
    stylers: [{ color: "#2d3748" }],
  },
  {
    featureType: "road.highway",
    elementType: "geometry.stroke",
    stylers: [{ color: "#1a2035" }],
  },
  {
    featureType: "water",
    elementType: "geometry",
    stylers: [{ color: "#0a0e1a" }],
  },
  {
    featureType: "poi",
    stylers: [{ visibility: "off" }],
  },
  {
    featureType: "transit",
    stylers: [{ visibility: "simplified" }],
  },
  {
    featureType: "administrative.locality",
    elementType: "labels.text.fill",
    stylers: [{ color: "#8b92a8" }],
  },
  {
    featureType: "administrative.neighborhood",
    elementType: "labels.text.fill",
    stylers: [{ color: "#3a4055" }],
  },
];

export default function HeatMap({ hour, day }) {
  const mapRef       = useRef(null);   // DOM div ref
  const mapObj       = useRef(null);   // google.maps.Map instance
  const heatmapLayer = useRef(null);   // google.maps.visualization.HeatmapLayer

  const [status,    setStatus]    = useState("idle");   // idle | loading | error
  const [cellCount, setCellCount] = useState(0);
  const [highCount, setHighCount] = useState(0);
  const [loadMs,    setLoadMs]    = useState(null);
  const [error,     setError]     = useState(null);

  // ── Initialise map once ──────────────────────────────────────────────────
  useEffect(() => {
    if (!window.google || mapObj.current) return;

    mapObj.current = new window.google.maps.Map(mapRef.current, {
      center:            CHICAGO_CENTER,
      zoom:              12,
      styles:            DARK_MAP_STYLE,
      disableDefaultUI:  false,
      zoomControl:       true,
      mapTypeControl:    false,
      streetViewControl: false,
      fullscreenControl: true,
    });

    // Initialise empty heatmap layer
    heatmapLayer.current = new window.google.maps.visualization.HeatmapLayer({
      data:     [],
      map:      mapObj.current,
      radius:   25,
      opacity:  0.85,
      gradient: HEATMAP_GRADIENT,
    });
  }, []);

  // ── Fetch + update heatmap when hour or day changes ──────────────────────
  const loadHeatmap = useCallback(async () => {
    if (!heatmapLayer.current) return;

    setStatus("loading");
    setError(null);
    const t0 = Date.now();

    try {
      const points = await fetchHeatmap(hour, day);

      // Convert API response to google.maps.visualization.WeightedLocation[]
      const weighted = points.map(p => ({
        location: new window.google.maps.LatLng(p.lat, p.lon),
        weight:   p.risk,
      }));

      heatmapLayer.current.setData(weighted);

      const elapsed = Date.now() - t0;
      const highRisk = points.filter(p => p.risk > 0.55).length;

      setCellCount(points.length);
      setHighCount(highRisk);
      setLoadMs(elapsed);
      setStatus("ready");

    } catch (err) {
      console.error("[HeatMap] fetch error:", err);
      setError(err.message || "Failed to load heatmap");
      setStatus("error");
    }
  }, [hour, day]);

  // Re-fetch whenever hour or day changes
  useEffect(() => {
    loadHeatmap();
  }, [loadHeatmap]);

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div style={styles.root}>

      {/* Map */}
      <div ref={mapRef} style={styles.map} />

      {/* Status overlay — top left */}
      <div style={styles.statusBar}>
        {status === "loading" && (
          <div style={styles.statusChip}>
            <div style={styles.spinner} />
            <span style={{ color: "#8b92a8" }}>Updating heatmap…</span>
          </div>
        )}
        {status === "error" && (
          <div style={{ ...styles.statusChip, borderColor: "#ef4444" }}>
            <span style={{ color: "#ef4444" }}>⚠ {error}</span>
            <button style={styles.retryBtn} onClick={loadHeatmap}>Retry</button>
          </div>
        )}
        {status === "ready" && (
          <div style={styles.statsRow}>
            <div style={styles.statChip}>
              <span style={styles.statLabel}>Cells scored</span>
              <span style={styles.statVal}>{cellCount.toLocaleString()}</span>
            </div>
            <div style={{ ...styles.statChip, borderColor: "#ef444433" }}>
              <span style={styles.statLabel}>High-risk zones</span>
              <span style={{ ...styles.statVal, color: "#ef4444" }}>
                {highCount.toLocaleString()}
              </span>
            </div>
            <div style={styles.statChip}>
              <span style={styles.statLabel}>Load time</span>
              <span style={{ ...styles.statVal, color: "#22c55e" }}>
                {loadMs}ms
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Info panel — bottom left */}
      <div style={styles.infoPanel}>
        <div style={styles.infoPanelTitle}>🗺 Risk Heatmap</div>
        <div style={styles.infoPanelText}>
          Each cell (~200m) is scored by a LightGBM model trained on
          8.4M Chicago crime incidents. Risk = spatial danger × time multiplier.
          Drag the hour slider to see the city change in real time.
        </div>
      </div>

    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Styles
// ─────────────────────────────────────────────────────────────────────────────

const styles = {
  root: {
    position: "relative",
    width: "100%",
    height: "100%",
  },

  map: {
    width: "100%",
    height: "100%",
  },

  // ── Status bar ─────────────────────────────────────────────────────────────
  statusBar: {
    position: "absolute",
    top: 12,
    left: 12,
    zIndex: 5,
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  statusChip: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    background: "rgba(10,12,16,0.92)",
    border: "1px solid #1e2330",
    borderRadius: 8,
    padding: "6px 12px",
    fontSize: 12,
    backdropFilter: "blur(8px)",
  },
  spinner: {
    width: 12,
    height: 12,
    border: "2px solid #1e2330",
    borderTop: "2px solid #6366f1",
    borderRadius: "50%",
    animation: "spin 0.7s linear infinite",
  },
  retryBtn: {
    marginLeft: 8,
    padding: "2px 8px",
    borderRadius: 4,
    border: "1px solid #ef4444",
    background: "transparent",
    color: "#ef4444",
    fontSize: 11,
    cursor: "pointer",
    fontFamily: "'Outfit', sans-serif",
  },
  statsRow: {
    display: "flex",
    gap: 6,
  },
  statChip: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
    background: "rgba(10,12,16,0.92)",
    border: "1px solid #1e2330",
    borderRadius: 8,
    padding: "6px 12px",
    backdropFilter: "blur(8px)",
  },
  statLabel: {
    fontSize: 10,
    color: "#5a6380",
    fontFamily: "'DM Mono', monospace",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  statVal: {
    fontSize: 14,
    fontWeight: 600,
    color: "#e8eaf2",
    fontFamily: "'DM Mono', monospace",
  },

  // ── Info panel ─────────────────────────────────────────────────────────────
  infoPanel: {
    position: "absolute",
    bottom: 24,
    left: 12,
    zIndex: 5,
    background: "rgba(10,12,16,0.92)",
    border: "1px solid #1e2330",
    borderRadius: 10,
    padding: "10px 14px",
    maxWidth: 280,
    backdropFilter: "blur(8px)",
  },
  infoPanelTitle: {
    fontSize: 12,
    fontWeight: 600,
    color: "#e8eaf2",
    marginBottom: 6,
  },
  infoPanelText: {
    fontSize: 11,
    color: "#5a6380",
    lineHeight: 1.6,
  },
};