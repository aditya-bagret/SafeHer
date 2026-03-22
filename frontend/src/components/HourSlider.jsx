// frontend/src/components/HourSlider.jsx
// ─────────────────────────────────────────────────────────────────────────────
// SafeHer — Hour slider (0–23).
// Shared control — moving it triggers re-fetch in both HeatMap and RouteMap.
// Visual gradient reflects risk: green (morning) → amber (evening) → red (night)
// ─────────────────────────────────────────────────────────────────────────────

import { useRef, useCallback } from "react";

// Risk colour at each hour — matches temporal_lookup multiplier pattern
// High at midnight/1AM (weekend violent crime peaks), low at 5–6AM
const HOUR_COLORS = [
  "#ef4444", // 0  — midnight    HIGH
  "#ef4444", // 1  — 1AM         HIGH
  "#f97316", // 2  — 2AM
  "#f97316", // 3  — 3AM
  "#f59e0b", // 4  — 4AM
  "#84cc16", // 5  — 5AM         LOW
  "#22c55e", // 6  — 6AM         SAFE
  "#22c55e", // 7  — 7AM
  "#22c55e", // 8  — 8AM
  "#22c55e", // 9  — 9AM
  "#22c55e", // 10 — 10AM
  "#22c55e", // 11 — 11AM
  "#22c55e", // 12 — noon
  "#22c55e", // 13 — 1PM
  "#22c55e", // 14 — 2PM
  "#f59e0b", // 15 — 3PM         MODERATE (Fri 3PM spike per temporal_lookup)
  "#f59e0b", // 16 — 4PM
  "#f59e0b", // 17 — 5PM
  "#f97316", // 18 — 6PM
  "#f97316", // 19 — 7PM
  "#ef4444", // 20 — 8PM
  "#ef4444", // 21 — 9PM         HIGH
  "#ef4444", // 22 — 10PM
  "#ef4444", // 23 — 11PM
];

const HOUR_LABELS = [
  "12A","1A","2A","3A","4A","5A",
  "6A","7A","8A","9A","10A","11A",
  "12P","1P","2P","3P","4P","5P",
  "6P","7P","8P","9P","10P","11P",
];

function formatHour(h) {
  if (h === 0)  return "12:00 AM";
  if (h === 12) return "12:00 PM";
  return h < 12 ? `${h}:00 AM` : `${h - 12}:00 PM`;
}

export default function HourSlider({ hour, onChange, period }) {
  const trackRef = useRef(null);

  // Build gradient string from HOUR_COLORS
  const gradient = HOUR_COLORS.map(
    (c, i) => `${c} ${(i / 23) * 100}%`
  ).join(", ");

  // Click / drag on track
  const handleTrackInteraction = useCallback((e) => {
    const rect = trackRef.current.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    onChange(Math.round(pct * 23));
  }, [onChange]);

  const thumbLeft = `${(hour / 23) * 100}%`;
  const thumbColor = HOUR_COLORS[hour];

  return (
    <div style={styles.root}>

      {/* Tick marks for key hours */}
      <div style={styles.ticks}>
        {[0, 6, 12, 18, 23].map(h => (
          <div
            key={h}
            style={{
              ...styles.tick,
              left: `${(h / 23) * 100}%`,
              color: HOUR_COLORS[h],
            }}
            onClick={() => onChange(h)}
          >
            <div style={{
              ...styles.tickLine,
              background: HOUR_COLORS[h],
              opacity: h === hour ? 1 : 0.4,
            }} />
            <span style={{
              ...styles.tickLabel,
              color: h === hour ? HOUR_COLORS[h] : "#3a4055",
              fontWeight: h === hour ? 600 : 400,
            }}>
              {HOUR_LABELS[h]}
            </span>
          </div>
        ))}
      </div>

      {/* Track */}
      <div
        ref={trackRef}
        style={{
          ...styles.track,
          background: `linear-gradient(to right, ${gradient})`,
        }}
        onClick={handleTrackInteraction}
        onMouseDown={(e) => {
          handleTrackInteraction(e);
          const onMove = (ev) => handleTrackInteraction(ev);
          const onUp   = () => {
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onUp);
          };
          window.addEventListener("mousemove", onMove);
          window.addEventListener("mouseup", onUp);
        }}
        onTouchStart={handleTrackInteraction}
        onTouchMove={handleTrackInteraction}
      >
        {/* Filled portion */}
        <div style={{
          ...styles.fill,
          width: thumbLeft,
          background: `linear-gradient(to right, ${gradient})`,
          opacity: 0.6,
        }} />

        {/* Thumb */}
        <div style={{
          ...styles.thumb,
          left: thumbLeft,
          background: thumbColor,
          boxShadow: `0 0 12px ${thumbColor}88, 0 0 4px ${thumbColor}`,
        }}>
          <div style={styles.thumbInner} />
        </div>
      </div>

      {/* Hour buttons — quick jump to common times */}
      <div style={styles.quickJump}>
        {[
          { h: 5,  label: "5AM",  color: "#84cc16" },
          { h: 9,  label: "9AM",  color: "#22c55e" },
          { h: 14, label: "2PM",  color: "#22c55e" },
          { h: 18, label: "6PM",  color: "#f97316" },
          { h: 21, label: "9PM",  color: "#ef4444" },
          { h: 0,  label: "12AM", color: "#ef4444" },
        ].map(({ h, label, color }) => (
          <button
            key={label}
            style={{
              ...styles.quickBtn,
              ...(hour === h ? {
                background: color + "22",
                borderColor: color,
                color,
              } : {}),
            }}
            onClick={() => onChange(h)}
          >
            {label}
          </button>
        ))}
      </div>

    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Styles
// ─────────────────────────────────────────────────────────────────────────────

const styles = {
  root: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
    userSelect: "none",
  },

  // ── Ticks ──────────────────────────────────────────────────────────────────
  ticks: {
    position: "relative",
    height: 22,
    marginBottom: 2,
  },
  tick: {
    position: "absolute",
    transform: "translateX(-50%)",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 3,
    cursor: "pointer",
  },
  tickLine: {
    width: 1,
    height: 6,
    borderRadius: 1,
  },
  tickLabel: {
    fontSize: 9,
    fontFamily: "'DM Mono', monospace",
    letterSpacing: "0.3px",
    transition: "color 0.2s",
  },

  // ── Track ──────────────────────────────────────────────────────────────────
  track: {
    position: "relative",
    height: 6,
    borderRadius: 6,
    cursor: "pointer",
    overflow: "visible",
  },
  fill: {
    position: "absolute",
    left: 0,
    top: 0,
    height: "100%",
    borderRadius: 6,
    pointerEvents: "none",
  },

  // ── Thumb ──────────────────────────────────────────────────────────────────
  thumb: {
    position: "absolute",
    top: "50%",
    transform: "translate(-50%, -50%)",
    width: 18,
    height: 18,
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "grab",
    transition: "box-shadow 0.2s",
    zIndex: 2,
  },
  thumbInner: {
    width: 6,
    height: 6,
    borderRadius: "50%",
    background: "#fff",
    opacity: 0.9,
  },

  // ── Quick jump ─────────────────────────────────────────────────────────────
  quickJump: {
    display: "flex",
    gap: 4,
    flexWrap: "wrap",
    marginTop: 2,
  },
  quickBtn: {
    flex: 1,
    minWidth: 36,
    padding: "4px 2px",
    borderRadius: 5,
    border: "1px solid #1e2330",
    background: "transparent",
    color: "#3a4055",
    fontSize: 10,
    fontFamily: "'DM Mono', monospace",
    cursor: "pointer",
    transition: "all 0.15s",
    textAlign: "center",
  },
};