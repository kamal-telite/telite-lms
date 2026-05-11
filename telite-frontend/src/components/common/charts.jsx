import { useRef } from "react";
import { Chart as ChartJS, registerables } from "chart.js";
import { Chart } from "react-chartjs-2";

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
        ctx.fillStyle = "#0F172A";
        ctx.font = "600 12px Geist, sans-serif";
        ctx.fillText(centerLabel.title, centerX, centerY - 4);
        ctx.fillStyle = "#94A3B8";
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
