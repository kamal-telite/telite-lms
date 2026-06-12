import { useRef } from "react";
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
} from "chart.js";
import { Chart } from "react-chartjs-2";

let chartRegistered = false;

function ensureChartRegistered() {
  if (chartRegistered) {
    return;
  }
  ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    ArcElement,
    Title,
    Tooltip,
    Legend,
    Filler
  );
  chartRegistered = true;
}

export function ChartCanvas({
  type,
  labels,
  datasets,
  options,
  height = 180,
  className = "",
  centerLabel,
}) {
  ensureChartRegistered();
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
