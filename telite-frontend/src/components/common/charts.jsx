import { useRef } from "react";
import { Chart as ChartJS, registerables } from "chart.js";
import { Chart } from "react-chartjs-2";
import PropTypes from "prop-types";

ChartJS.register(...registerables);

export function ChartCanvas({
  type,
  labels,
  datasets,
  options,
  height = 180,
  className = "",
  centerLabel,
}) {
  const chartRef = useRef(null);

  const plugins = [];
  if (centerLabel) {
    plugins.push({
      id: "centerLabel",
      afterDraw(chart) {
        const { ctx, chartArea } = chart;
        if (!chartArea) {
          return;
        }
        const centerX = (chartArea.left + chartArea.right) / 2;
        const centerY = (chartArea.top + chartArea.bottom) / 2;
        ctx.save();
        ctx.textAlign = "center";
        ctx.fillStyle = "var(--text-primary)";
        ctx.font = "600 12px Geist, sans-serif";
        ctx.fillText(centerLabel.title, centerX, centerY - 4);
        ctx.fillStyle = "var(--text-muted)";
        ctx.font = "500 10px Geist Mono, monospace";
        ctx.fillText(centerLabel.subtitle, centerX, centerY + 14);
        ctx.restore();
      },
    });
  }

  // To prevent the UI glitch (auto-scroll) from Chart.js resizing/re-rendering on every pulse,
  // we let react-chartjs-2 handle the update lifecycle natively instead of destroying and recreating.
  return (
    <div className={className} style={{ height, position: "relative" }}>
      <Chart
        ref={chartRef}
        type={type}
        data={{ labels, datasets }}
        options={{ ...options, maintainAspectRatio: false }}
        plugins={plugins}
      />
    </div>
  );
}

ChartCanvas.propTypes = {
  type: PropTypes.oneOf(["line", "bar", "pie", "doughnut", "radar", "polarArea", "bubble", "scatter"]).isRequired,
  labels: PropTypes.arrayOf(PropTypes.string).isRequired,
  datasets: PropTypes.arrayOf(PropTypes.object).isRequired,
  options: PropTypes.object,
  height: PropTypes.number,
  className: PropTypes.string,
  centerLabel: PropTypes.shape({
    title: PropTypes.string.isRequired,
    subtitle: PropTypes.string.isRequired,
  }),
};
