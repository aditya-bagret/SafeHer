import { useState } from "react";

function FiguresSection({ styles }) {
  const [hoverIndex, setHoverIndex] = useState(null);

  const figures = [
    { name: "Crime by Hour Chart", path: "/figures/crime_by_hour_chart.html" },
    { name: "Feature Importance", path: "/figures/feature_importance_chart.html" },
    { name: "Model Comparison Table", path: "/figures/model_comparison_table1.html" },
    { name: "Severity Imbalance Chart", path: "/figures/severity_imbalance_chart.html" },
    { name: "System Timing Table", path: "/figures/system_timing_table2.html" },
    { name: "Temporal Multiplier Heatmap", path: "/figures/temporal_multiplier_heatmap.html" }
  ];

  return (
    <div style={styles.figuresCard}>
      <div style={styles.figuresTitle}>Figures & Visualizations</div>

      <div style={styles.figureList}>
        {figures.map((fig, i) => (
          <a
            key={i}
            href={fig.path}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              ...styles.figureItem,
              ...(hoverIndex === i ? styles.figureItemHover : {})
            }}
            onMouseEnter={() => setHoverIndex(i)}
            onMouseLeave={() => setHoverIndex(null)}
          >
            📊 {fig.name}
          </a>
        ))}
      </div>
    </div>
  );
}

export default FiguresSection;