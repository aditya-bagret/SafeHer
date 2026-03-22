// frontend/src/components/RouteMap.jsx
// ─────────────────────────────────────────────────────────────────────────────
// SafeHer — Safe route finder.
// Fetches up to 3 Google Directions alternatives, scores each with the
// LightGBM risk model, draws coloured polylines, shows risk score cards.
// Uses the SAME risk model as HeatMap — Novel Contribution 2.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect, useRef, useState, useCallback } from "react";
import { fetchSafeRoute } from "../api/saferoute";

const CHICAGO_CENTER = { lat: 41.8781, lng: -87.6298 };

const DARK_MAP_STYLE = [
  { elementType: "geometry",           stylers: [{ color: "#0f1218" }] },
  { elementType: "labels.text.fill",   stylers: [{ color: "#5a6380" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#0a0c10" }] },
  { featureType: "road", elementType: "geometry",
    stylers: [{ color: "#1e2330" }] },
  { featureType: "road.arterial", elementType: "geometry",
    stylers: [{ color: "#252d3d" }] },
  { featureType: "road.highway", elementType: "geometry",
    stylers: [{ color: "#2d3748" }] },
  { featureType: "water", elementType: "geometry",
    stylers: [{ color: "#0a0e1a" }] },
  { featureType: "poi", stylers: [{ visibility: "off" }] },
  { featureType: "administrative.locality",
    elementType: "labels.text.fill",
    stylers: [{ color: "#8b92a8" }] },
];

const LABEL_META = {
  safe:     { color: "#22c55e", bg: "#22c55e18", icon: "✅", text: "Safest Route"   },
  moderate: { color: "#f59e0b", bg: "#f59e0b18", icon: "⚠️",  text: "Moderate Risk"  },
  high:     { color: "#ef4444", bg: "#ef444418", icon: "🚨", text: "High Risk"       },
};

// Demo presets — useful for judges / testing
const DEMO_ROUTES = [
  {
    label: "Downtown → Wicker Park",
    origin:      "Chicago Union Station, Chicago, IL",
    destination: "Wicker Park, Chicago, IL",
  },
  {
    label: "O'Hare → The Loop",
    origin:      "O'Hare International Airport, Chicago, IL",
    destination: "The Loop, Chicago, IL",
  },
  {
    label: "Hyde Park → Lincoln Park",
    origin:      "Hyde Park, Chicago, IL",
    destination: "Lincoln Park, Chicago, IL",
  },
];

export default function RouteMap({ hour, day }) {
  const mapRef      = useRef(null);
  const mapObj      = useRef(null);
  const polylinesRef= useRef([]);
  const markersRef  = useRef([]);
  const autocOrigin = useRef(null);
  const autocDest   = useRef(null);
  const originInput = useRef(null);
  const destInput   = useRef(null);

  const [origin,      setOrigin]      = useState("");
  const [destination, setDestination] = useState("");
  const [routes,      setRoutes]      = useState([]);
  const [status,      setStatus]      = useState("idle");
  const [error,       setError]       = useState(null);
  const [activeRoute, setActiveRoute] = useState(0);

  // ── Init map ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!window.google || mapObj.current) return;

    mapObj.current = new window.google.maps.Map(mapRef.current, {
      center:            CHICAGO_CENTER,
      zoom:              12,
      styles:            DARK_MAP_STYLE,
      mapTypeControl:    false,
      streetViewControl: false,
      fullscreenControl: true,
    });
  }, []);

  // ── Init Google Places Autocomplete ───────────────────────────────────────
  useEffect(() => {
    if (!window.google || autocOrigin.current) return;

    const bounds = new window.google.maps.LatLngBounds(
      new window.google.maps.LatLng(41.64, -87.94),
      new window.google.maps.LatLng(42.02, -87.52)
    );

    autocOrigin.current = new window.google.maps.places.Autocomplete(
      originInput.current,
      { bounds, strictBounds: false, componentRestrictions: { country: "us" } }
    );
    autocOrigin.current.addListener("place_changed", () => {
      const place = autocOrigin.current.getPlace();
      if (place?.formatted_address) setOrigin(place.formatted_address);
    });

    autocDest.current = new window.google.maps.places.Autocomplete(
      destInput.current,
      { bounds, strictBounds: false, componentRestrictions: { country: "us" } }
    );
    autocDest.current.addListener("place_changed", () => {
      const place = autocDest.current.getPlace();
      if (place?.formatted_address) setDestination(place.formatted_address);
    });
  }, []);

  // ── Clear map overlays ────────────────────────────────────────────────────
  const clearMap = useCallback(() => {
    polylinesRef.current.forEach(p => p.setMap(null));
    polylinesRef.current = [];
    markersRef.current.forEach(m => m.setMap(null));
    markersRef.current = [];
  }, []);

  // ── Draw routes on map ────────────────────────────────────────────────────
  const drawRoutes = useCallback((routes, active) => {
    if (!mapObj.current || !window.google) return;
    clearMap();

    const bounds = new window.google.maps.LatLngBounds();

    routes.forEach((route, i) => {
      const isActive = i === active;
      const meta     = LABEL_META[route.label];

      // Decode overview polyline
      const path = window.google.maps.geometry.encoding.decodePath(
        route.polyline
      );
      path.forEach(p => bounds.extend(p));

      // Draw shadow (thicker, darker) for active route
      if (isActive) {
        polylinesRef.current.push(
          new window.google.maps.Polyline({
            path,
            map:          mapObj.current,
            strokeColor:  meta.color,
            strokeOpacity:0.15,
            strokeWeight: 14,
            zIndex:       1,
          })
        );
      }

      // Main polyline
      polylinesRef.current.push(
        new window.google.maps.Polyline({
          path,
          map:           mapObj.current,
          strokeColor:   meta.color,
          strokeOpacity: isActive ? 0.95 : 0.35,
          strokeWeight:  isActive ? 5    : 3,
          zIndex:        isActive ? 3    : 2,
          icons: isActive ? [{
            icon:   { path: window.google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
                      scale: 3, fillColor: meta.color, fillOpacity: 1,
                      strokeWeight: 0 },
            repeat: "120px",
            offset: "50%",
          }] : [],
        })
      );
    });

    // Origin marker
    const startPath = routes[active]?.polyline
      ? window.google.maps.geometry.encoding.decodePath(routes[active].polyline)[0]
      : null;
    const endPath = routes[active]?.polyline
      ? window.google.maps.geometry.encoding.decodePath(routes[active].polyline).slice(-1)[0]
      : null;

    [{ pos: startPath, label: "A" }, { pos: endPath, label: "B" }]
      .filter(m => m.pos)
      .forEach(({ pos, label }) => {
        markersRef.current.push(
          new window.google.maps.Marker({
            position: pos,
            map:      mapObj.current,
            label: {
              text:      label,
              color:     "#fff",
              fontWeight:"bold",
              fontSize:  "12px",
            },
            icon: {
              path:        window.google.maps.SymbolPath.CIRCLE,
              scale:       10,
              fillColor:   label === "A" ? "#6366f1" : "#22c55e",
              fillOpacity: 1,
              strokeColor: "#fff",
              strokeWeight:2,
            },
          })
        );
      });

    mapObj.current.fitBounds(bounds, { top: 60, bottom: 20, left: 20, right: 20 });
  }, [clearMap]);

  // ── Re-draw when active route changes ────────────────────────────────────
  useEffect(() => {
    if (routes.length > 0) drawRoutes(routes, activeRoute);
  }, [activeRoute, routes, drawRoutes]);

  // ── Find safe route ───────────────────────────────────────────────────────
  const handleFind = useCallback(async (orig, dest) => {
    const o = orig ?? origin;
    const d = dest ?? destination;

    if (!o.trim() || !d.trim()) {
      setError("Please enter both origin and destination.");
      return;
    }

    setStatus("loading");
    setError(null);
    setRoutes([]);
    clearMap();

    try {
      const data = await fetchSafeRoute(o, d, hour, day);
      setRoutes(data);
      setActiveRoute(0);
      drawRoutes(data, 0);
      setStatus("ready");
    } catch (err) {
      console.error("[RouteMap] fetch error:", err);
      setError(err.message || "Failed to fetch routes. Check Flask is running.");
      setStatus("error");
    }
  }, [origin, destination, hour, day, clearMap, drawRoutes]);

  // ── Load demo route ───────────────────────────────────────────────────────
  const loadDemo = useCallback((demo) => {
    setOrigin(demo.origin);
    setDestination(demo.destination);
    if (originInput.current) originInput.current.value = demo.origin;
    if (destInput.current)   destInput.current.value   = demo.destination;
    handleFind(demo.origin, demo.destination);
  }, [handleFind]);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div style={styles.root}>

      {/* Map */}
      <div ref={mapRef} style={styles.map} />

      {/* Search panel — top overlay */}
      <div style={styles.searchPanel}>

        {/* Inputs */}
        <div style={styles.inputGroup}>
          <div style={styles.inputRow}>
            <span style={{ ...styles.inputDot, background: "#6366f1" }} />
            <input
              ref={originInput}
              style={styles.input}
              placeholder="Origin — e.g. Chicago Union Station"
              defaultValue={origin}
              onChange={e => setOrigin(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleFind()}
            />
          </div>
          <div style={styles.inputDivider} />
          <div style={styles.inputRow}>
            <span style={{ ...styles.inputDot, background: "#22c55e" }} />
            <input
              ref={destInput}
              style={styles.input}
              placeholder="Destination — e.g. Wicker Park"
              defaultValue={destination}
              onChange={e => setDestination(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleFind()}
            />
          </div>
        </div>

        {/* Find button */}
        <button
          style={{
            ...styles.findBtn,
            ...(status === "loading" ? styles.findBtnLoading : {}),
          }}
          onClick={() => handleFind()}
          disabled={status === "loading"}
        >
          {status === "loading" ? (
            <><div style={styles.btnSpinner} /> Scoring routes…</>
          ) : (
            "🧭 Find Safe Route"
          )}
        </button>

        {/* Demo presets */}
        <div style={styles.demoRow}>
          <span style={styles.demoLabel}>Try:</span>
          {DEMO_ROUTES.map(d => (
            <button
              key={d.label}
              style={styles.demoBtn}
              onClick={() => loadDemo(d)}
            >
              {d.label}
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div style={styles.errorBar}>
            ⚠ {error}
          </div>
        )}
      </div>

      {/* Route cards — bottom overlay */}
      {routes.length > 0 && (
        <div style={styles.routeCards}>
          <div style={styles.routeCardsTitle}>
            Routes ranked by safety — {routes.length} alternatives
            <span style={styles.routeCardsHour}>
              at {hour === 0 ? "12AM" : hour < 12 ? `${hour}AM` : hour === 12 ? "12PM" : `${hour-12}PM`}
            </span>
          </div>
          <div style={styles.cardRow}>
            {routes.map((route, i) => {
              const meta = LABEL_META[route.label];
              const isActive = i === activeRoute;
              return (
                <div
                  key={i}
                  style={{
                    ...styles.card,
                    borderColor: isActive ? meta.color : "#1e2330",
                    background:  isActive ? meta.bg    : "#0a0c10",
                    cursor: "pointer",
                  }}
                  onClick={() => setActiveRoute(i)}
                >
                  {/* Rank badge */}
                  <div style={styles.cardRank}>
                    {i === 0 && <span style={styles.recommendBadge}>RECOMMENDED</span>}
                    <span style={{ ...styles.rankNum,
                      color: isActive ? meta.color : "#3a4055" }}>
                      #{i + 1}
                    </span>
                  </div>

                  {/* Risk label */}
                  <div style={styles.cardLabelRow}>
                    <span style={{ fontSize: 16 }}>{meta.icon}</span>
                    <span style={{ ...styles.cardLabel, color: meta.color }}>
                      {meta.text}
                    </span>
                  </div>

                  {/* Risk score bar */}
                  <div style={styles.riskBarTrack}>
                    <div style={{
                      ...styles.riskBarFill,
                      width: `${route.avg_risk * 100}%`,
                      background: meta.color,
                    }} />
                  </div>
                  <div style={styles.riskScore}>
                    Risk score: <span style={{ color: meta.color, fontWeight: 600 }}>
                      {(route.avg_risk * 100).toFixed(1)}%
                    </span>
                  </div>

                  {/* Route stats */}
                  <div style={styles.cardStats}>
                    <div style={styles.cardStat}>
                      <span style={styles.cardStatLabel}>Duration</span>
                      <span style={styles.cardStatVal}>{route.duration_text}</span>
                    </div>
                    <div style={styles.cardStat}>
                      <span style={styles.cardStatLabel}>Distance</span>
                      <span style={styles.cardStatVal}>{route.distance_text}</span>
                    </div>
                  </div>

                  {/* Select indicator */}
                  {isActive && (
                    <div style={{ ...styles.activeIndicator,
                      background: meta.color }} />
                  )}
                </div>
              );
            })}
          </div>

          {/* Disclaimer */}
          <div style={styles.disclaimer}>
            Risk scores are based on historical Chicago crime data (2001–2025).
            Always use personal judgement when navigating.
          </div>
        </div>
      )}

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

  // ── Search panel ───────────────────────────────────────────────────────────
  searchPanel: {
    position: "absolute",
    top: 12,
    left: 12,
    zIndex: 5,
    background: "rgba(10,12,16,0.95)",
    border: "1px solid #1e2330",
    borderRadius: 12,
    padding: "14px",
    width: 360,
    backdropFilter: "blur(12px)",
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  inputGroup: {
    background: "#111318",
    border: "1px solid #1e2330",
    borderRadius: 8,
    overflow: "hidden",
  },
  inputRow: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "8px 12px",
  },
  inputDot: {
    width: 10,
    height: 10,
    borderRadius: "50%",
    flexShrink: 0,
  },
  inputDivider: {
    height: 1,
    background: "#1e2330",
    marginLeft: 32,
  },
  input: {
    flex: 1,
    background: "transparent",
    border: "none",
    outline: "none",
    color: "#e8eaf2",
    fontSize: 13,
    fontFamily: "'Outfit', sans-serif",
  },
  findBtn: {
    width: "100%",
    padding: "10px 0",
    borderRadius: 8,
    border: "none",
    background: "#6366f1",
    color: "#fff",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
    fontFamily: "'Outfit', sans-serif",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    transition: "opacity 0.15s",
  },
  findBtnLoading: {
    opacity: 0.7,
    cursor: "not-allowed",
  },
  btnSpinner: {
    width: 14,
    height: 14,
    border: "2px solid rgba(255,255,255,0.3)",
    borderTop: "2px solid #fff",
    borderRadius: "50%",
    animation: "spin 0.7s linear infinite",
  },
  demoRow: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    flexWrap: "wrap",
  },
  demoLabel: {
    fontSize: 11,
    color: "#5a6380",
    flexShrink: 0,
  },
  demoBtn: {
    padding: "3px 8px",
    borderRadius: 5,
    border: "1px solid #1e2330",
    background: "transparent",
    color: "#8b92a8",
    fontSize: 11,
    cursor: "pointer",
    fontFamily: "'Outfit', sans-serif",
    transition: "all 0.15s",
    whiteSpace: "nowrap",
  },
  errorBar: {
    padding: "8px 12px",
    borderRadius: 8,
    background: "#ef444418",
    border: "1px solid #ef444433",
    color: "#ef4444",
    fontSize: 12,
  },

  // ── Route cards ────────────────────────────────────────────────────────────
  routeCards: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    zIndex: 5,
    background: "rgba(10,12,16,0.96)",
    borderTop: "1px solid #1e2330",
    padding: "12px 16px 16px",
    backdropFilter: "blur(12px)",
  },
  routeCardsTitle: {
    fontSize: 12,
    fontWeight: 600,
    color: "#8b92a8",
    marginBottom: 10,
    display: "flex",
    alignItems: "center",
    gap: 8,
    textTransform: "uppercase",
    letterSpacing: "0.6px",
  },
  routeCardsHour: {
    fontFamily: "'DM Mono', monospace",
    color: "#6366f1",
    fontWeight: 400,
    textTransform: "none",
    letterSpacing: 0,
  },
  cardRow: {
    display: "flex",
    gap: 10,
    overflowX: "auto",
    paddingBottom: 4,
  },
  card: {
    flex: "0 0 220px",
    border: "1.5px solid",
    borderRadius: 10,
    padding: "12px 14px",
    cursor: "pointer",
    position: "relative",
    overflow: "hidden",
    transition: "border-color 0.2s, background 0.2s",
  },
  cardRank: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  recommendBadge: {
    fontSize: 9,
    fontWeight: 700,
    color: "#22c55e",
    background: "#22c55e18",
    border: "1px solid #22c55e33",
    borderRadius: 4,
    padding: "2px 6px",
    letterSpacing: "0.5px",
  },
  rankNum: {
    fontSize: 11,
    fontFamily: "'DM Mono', monospace",
    fontWeight: 600,
    marginLeft: "auto",
  },
  cardLabelRow: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    marginBottom: 10,
  },
  cardLabel: {
    fontSize: 13,
    fontWeight: 600,
  },
  riskBarTrack: {
    height: 4,
    background: "#1e2330",
    borderRadius: 4,
    marginBottom: 4,
    overflow: "hidden",
  },
  riskBarFill: {
    height: "100%",
    borderRadius: 4,
    transition: "width 0.4s ease",
  },
  riskScore: {
    fontSize: 11,
    color: "#5a6380",
    fontFamily: "'DM Mono', monospace",
    marginBottom: 10,
  },
  cardStats: {
    display: "flex",
    gap: 12,
  },
  cardStat: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
  },
  cardStatLabel: {
    fontSize: 10,
    color: "#5a6380",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  cardStatVal: {
    fontSize: 13,
    fontWeight: 600,
    color: "#e8eaf2",
    fontFamily: "'DM Mono', monospace",
  },
  activeIndicator: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    height: 3,
    borderRadius: "0 0 10px 10px",
  },
  disclaimer: {
    marginTop: 10,
    fontSize: 10,
    color: "#3a4055",
    textAlign: "center",
    fontStyle: "italic",
  },
};