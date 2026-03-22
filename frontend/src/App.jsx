// frontend/src/App.jsx
// ─────────────────────────────────────────────────────────────────────────────
// SafeHer — Root component.
// Owns the shared hour + day state that drives both HeatMap and RouteMap.
// When the user moves the hour slider, both components re-fetch simultaneously.
// This is Novel Contribution 5 — dynamic temporal heatmap.
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useEffect, useCallback } from "react";
import HeatMap    from "./components/HeatMap";
import RouteMap   from "./components/RouteMap";
import HourSlider from "./components/HourSlider";

// ── Constants ─────────────────────────────────────────────────────────────────
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const RISK_FACTS = [
  "Alleys carry 3× higher risk than main streets at night.",
  "Violent crime peaks between midnight and 2AM on weekends.",
  "Areas within 500m of police stations show 28% lower risk.",
  "Friday and Saturday nights have the highest temporal multipliers.",
  "Community area 25 (Austin) has the highest historical crime density.",
  "Domestic crimes cluster in residential zones — affects route scoring.",
  "Risk scores update every hour based on temporal multipliers.",
];

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatHour(h) {
  if (h === 0)  return "12:00 AM";
  if (h === 12) return "12:00 PM";
  return h < 12 ? `${h}:00 AM` : `${h - 12}:00 PM`;
}

function getRiskPeriod(h) {
  if (h >= 0  && h <= 5)  return { label: "Late Night",  color: "#ef4444", icon: "🌙" };
  if (h >= 6  && h <= 11) return { label: "Morning",     color: "#22c55e", icon: "🌅" };
  if (h >= 12 && h <= 17) return { label: "Afternoon",   color: "#f59e0b", icon: "☀️"  };
  if (h >= 18 && h <= 20) return { label: "Evening",     color: "#f59e0b", icon: "🌆" };
  return                          { label: "Night",       color: "#ef4444", icon: "🌃" };
}

// ─────────────────────────────────────────────────────────────────────────────

export default function App() {
  const now = new Date();

  // Shared temporal state — drives both HeatMap and RouteMap
  const [hour, setHour]   = useState(now.getHours());
  const [day,  setDay]    = useState(now.getDay() === 0 ? 6 : now.getDay() - 1); // JS Sun=0 → Mon=0

  // UI state
  const [activeTab,   setActiveTab]   = useState("heatmap"); // "heatmap" | "route"
  const [mapsReady,   setMapsReady]   = useState(false);
  const [factIndex,   setFactIndex]   = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Wait for Google Maps to load
  useEffect(() => {
    const check = setInterval(() => {
      if (window.google && window.google.maps) {
        setMapsReady(true);
        clearInterval(check);
      }
    }, 200);
    return () => clearInterval(check);
  }, []);

  // Rotate risk facts every 8s
  useEffect(() => {
    const t = setInterval(() => {
      setFactIndex(i => (i + 1) % RISK_FACTS.length);
    }, 8000);
    return () => clearInterval(t);
  }, []);

  const period = getRiskPeriod(hour);

  return (
    <div style={styles.shell}>

      {/* ── Top bar ─────────────────────────────────────────────────────── */}
      <header style={styles.topbar}>
        <div style={styles.topbarLeft}>
          <span style={styles.logo}>🛡️ SafeHer</span>
          <span style={styles.logoSub}>Chicago · AI Safety Navigation</span>
        </div>

        <div style={styles.topbarCenter}>
          {/* Tab switcher */}
          <div style={styles.tabs}>
            {["heatmap", "route"].map(tab => (
              <button
                key={tab}
                style={{
                  ...styles.tab,
                  ...(activeTab === tab ? styles.tabActive : {}),
                }}
                onClick={() => setActiveTab(tab)}
              >
                {tab === "heatmap" ? "🗺 Risk Heatmap" : "🧭 Safe Route"}
              </button>
            ))}
          </div>
        </div>

        <div style={styles.topbarRight}>
          <div style={styles.timeChip}>
            <span style={{ color: period.color }}>{period.icon}</span>
            <span style={styles.timeChipText}>{formatHour(hour)}</span>
            <span style={{ color: period.color, fontSize: 11 }}>{period.label}</span>
          </div>
          <div style={styles.dayChip}>
            {DAYS.map((d, i) => (
              <button
                key={d}
                style={{
                  ...styles.dayBtn,
                  ...(day === i ? { background: "#6366f1", color: "#fff" } : {}),
                }}
                onClick={() => setDay(i)}
              >
                {d}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* ── Main content ─────────────────────────────────────────────────── */}
      <div style={styles.main}>

        {/* Sidebar */}
        <aside style={{
          ...styles.sidebar,
          ...(sidebarOpen ? {} : { width: 0, minWidth: 0, overflow: "hidden", padding: 0 }),
        }}>

          {/* Hour slider */}
          <div style={styles.sliderCard}>
            <div style={styles.sliderLabel}>
              <span style={styles.sliderTitle}>Time of Day</span>
              <span style={{ color: period.color, fontWeight: 600 }}>
                {period.icon} {formatHour(hour)}
              </span>
            </div>
            <HourSlider
              hour={hour}
              onChange={setHour}
              period={period}
            />
            <div style={styles.sliderHints}>
              <span style={{ color: "#22c55e" }}>Safe 6AM</span>
              <span style={{ color: "#f59e0b" }}>9PM</span>
              <span style={{ color: "#ef4444" }}>High Risk 12AM</span>
            </div>
          </div>

          {/* Risk legend */}
          <div style={styles.legendCard}>
            <div style={styles.legendTitle}>Risk Level</div>
            {[
              { label: "High Risk",  color: "#ef4444", desc: "Avoid — elevated violent crime" },
              { label: "Moderate",   color: "#f59e0b", desc: "Caution — stay alert"          },
              { label: "Safe",       color: "#22c55e", desc: "Lower historical crime rate"    },
            ].map(item => (
              <div key={item.label} style={styles.legendRow}>
                <div style={{ ...styles.legendDot, background: item.color }} />
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: item.color }}>
                    {item.label}
                  </div>
                  <div style={{ fontSize: 11, color: "#5a6380" }}>{item.desc}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Model info */}
          <div style={styles.modelCard}>
            <div style={styles.modelTitle}>Model Info</div>
            <div style={styles.modelRow}>
              <span style={styles.modelKey}>Algorithm</span>
              <span style={styles.modelVal}>LightGBM</span>
            </div>
            <div style={styles.modelRow}>
              <span style={styles.modelKey}>Grid cells</span>
              <span style={styles.modelVal}>14,129</span>
            </div>
            <div style={styles.modelRow}>
              <span style={styles.modelKey}>Resolution</span>
              <span style={styles.modelVal}>~200m</span>
            </div>
            <div style={styles.modelRow}>
              <span style={styles.modelKey}>R² score</span>
              <span style={{ ...styles.modelVal, color: "#22c55e" }}>0.9997</span>
            </div>
            <div style={styles.modelRow}>
              <span style={styles.modelKey}>Temporal slots</span>
              <span style={styles.modelVal}>168 (24×7)</span>
            </div>
            <div style={styles.modelRow}>
              <span style={styles.modelKey}>Architecture</span>
              <span style={styles.modelVal}>Spatial × Temporal</span>
            </div>
          </div>

          {/* Rotating risk fact */}
          <div style={styles.factCard}>
            <div style={styles.factLabel}>📊 Did you know?</div>
            <div style={styles.factText}>{RISK_FACTS[factIndex]}</div>
          </div>

        </aside>

        {/* Sidebar toggle */}
        <button
          style={styles.sidebarToggle}
          onClick={() => setSidebarOpen(o => !o)}
          title={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
        >
          {sidebarOpen ? "◀" : "▶"}
        </button>

        {/* Map area */}
        <div style={styles.mapArea}>
          {!mapsReady ? (
            <div style={styles.loading}>
              <div style={styles.loadingSpinner} />
              <div style={styles.loadingText}>Loading Google Maps…</div>
              <div style={styles.loadingHint}>
                If this persists, check your API key in public/index.html
              </div>
            </div>
          ) : (
            <>
              {activeTab === "heatmap" && (
                <HeatMap hour={hour} day={day} />
              )}
              {activeTab === "route" && (
                <RouteMap hour={hour} day={day} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Styles
// ─────────────────────────────────────────────────────────────────────────────

const styles = {
  shell: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    background: "#0a0c10",
    color: "#e8eaf2",
    fontFamily: "'Outfit', sans-serif",
    overflow: "hidden",
  },

  // ── Top bar ────────────────────────────────────────────────────────────────
  topbar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 20px",
    height: 56,
    background: "#111318",
    borderBottom: "1px solid #1e2330",
    flexShrink: 0,
    gap: 16,
    zIndex: 10,
  },
  topbarLeft: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    flexShrink: 0,
  },
  logo: {
    fontSize: 18,
    fontWeight: 700,
    letterSpacing: "-0.3px",
    color: "#e8eaf2",
  },
  logoSub: {
    fontSize: 11,
    color: "#5a6380",
    fontFamily: "'DM Mono', monospace",
  },
  topbarCenter: {
    flex: 1,
    display: "flex",
    justifyContent: "center",
  },
  tabs: {
    display: "flex",
    background: "#0a0c10",
    borderRadius: 8,
    padding: 3,
    gap: 2,
    border: "1px solid #1e2330",
  },
  tab: {
    padding: "5px 16px",
    borderRadius: 6,
    border: "none",
    background: "transparent",
    color: "#5a6380",
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
    fontFamily: "'Outfit', sans-serif",
    transition: "all 0.15s",
  },
  tabActive: {
    background: "#1e2330",
    color: "#e8eaf2",
  },
  topbarRight: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    flexShrink: 0,
  },
  timeChip: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    background: "#0a0c10",
    border: "1px solid #1e2330",
    borderRadius: 8,
    padding: "4px 12px",
  },
  timeChipText: {
    fontSize: 13,
    fontFamily: "'DM Mono', monospace",
    color: "#e8eaf2",
  },
  dayChip: {
    display: "flex",
    gap: 2,
    background: "#0a0c10",
    border: "1px solid #1e2330",
    borderRadius: 8,
    padding: 3,
  },
  dayBtn: {
    padding: "3px 7px",
    borderRadius: 5,
    border: "none",
    background: "transparent",
    color: "#5a6380",
    fontSize: 11,
    fontWeight: 500,
    cursor: "pointer",
    fontFamily: "'Outfit', sans-serif",
    transition: "all 0.15s",
  },

  // ── Main ───────────────────────────────────────────────────────────────────
  main: {
    display: "flex",
    flex: 1,
    overflow: "hidden",
    position: "relative",
  },

  // ── Sidebar ────────────────────────────────────────────────────────────────
  sidebar: {
    width: 260,
    minWidth: 260,
    background: "#111318",
    borderRight: "1px solid #1e2330",
    display: "flex",
    flexDirection: "column",
    gap: 12,
    padding: "14px 12px",
    overflowY: "auto",
    flexShrink: 0,
    transition: "width 0.2s, min-width 0.2s, padding 0.2s",
  },
  sidebarToggle: {
    position: "absolute",
    left: 260,
    top: "50%",
    transform: "translateY(-50%)",
    zIndex: 5,
    width: 18,
    height: 40,
    background: "#1e2330",
    border: "1px solid #252d3d",
    borderLeft: "none",
    borderRadius: "0 6px 6px 0",
    cursor: "pointer",
    color: "#5a6380",
    fontSize: 9,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "left 0.2s",
  },

  // ── Slider card ────────────────────────────────────────────────────────────
  sliderCard: {
    background: "#0a0c10",
    border: "1px solid #1e2330",
    borderRadius: 10,
    padding: "14px 14px 10px",
  },
  sliderLabel: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  sliderTitle: {
    fontSize: 12,
    fontWeight: 600,
    color: "#8b92a8",
    textTransform: "uppercase",
    letterSpacing: "0.8px",
  },
  sliderHints: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: 10,
    marginTop: 6,
    fontFamily: "'DM Mono', monospace",
  },

  // ── Legend card ────────────────────────────────────────────────────────────
  legendCard: {
    background: "#0a0c10",
    border: "1px solid #1e2330",
    borderRadius: 10,
    padding: "14px",
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  legendTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: "#8b92a8",
    textTransform: "uppercase",
    letterSpacing: "0.8px",
    marginBottom: 2,
  },
  legendRow: {
    display: "flex",
    alignItems: "flex-start",
    gap: 10,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: "50%",
    marginTop: 3,
    flexShrink: 0,
  },

  // ── Model card ─────────────────────────────────────────────────────────────
  modelCard: {
    background: "#0a0c10",
    border: "1px solid #1e2330",
    borderRadius: 10,
    padding: "14px",
  },
  modelTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: "#8b92a8",
    textTransform: "uppercase",
    letterSpacing: "0.8px",
    marginBottom: 10,
  },
  modelRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  modelKey: {
    fontSize: 11,
    color: "#5a6380",
  },
  modelVal: {
    fontSize: 11,
    fontFamily: "'DM Mono', monospace",
    color: "#e8eaf2",
  },

  // ── Fact card ──────────────────────────────────────────────────────────────
  factCard: {
    background: "linear-gradient(135deg, #0d1020, #111827)",
    border: "1px solid #252d3d",
    borderRadius: 10,
    padding: "12px 14px",
  },
  factLabel: {
    fontSize: 10,
    fontWeight: 600,
    color: "#6366f1",
    textTransform: "uppercase",
    letterSpacing: "0.8px",
    marginBottom: 6,
  },
  factText: {
    fontSize: 12,
    color: "#8b92a8",
    lineHeight: 1.6,
  },

  // ── Map area ───────────────────────────────────────────────────────────────
  mapArea: {
    flex: 1,
    position: "relative",
    overflow: "hidden",
  },

  // ── Loading state ──────────────────────────────────────────────────────────
  loading: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    height: "100%",
    gap: 16,
  },
  loadingSpinner: {
    width: 36,
    height: 36,
    border: "3px solid #1e2330",
    borderTop: "3px solid #6366f1",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  loadingText: {
    fontSize: 14,
    color: "#8b92a8",
    fontWeight: 500,
  },
  loadingHint: {
    fontSize: 11,
    color: "#5a6380",
    fontFamily: "'DM Mono', monospace",
  },
};

// Inject spinner keyframe
const style = document.createElement("style");
style.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`;
document.head.appendChild(style);
