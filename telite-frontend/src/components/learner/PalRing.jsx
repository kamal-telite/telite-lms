import { useEffect, useMemo, useState } from "react";

/**
 * PalRing - Animated circular progress ring for PAL score visualization
 * 
 * @param {number} score - PAL score (0-100)
 * @param {number} size - SVG dimensions in pixels (default: 120)
 */
export function PalRing({ score, size = 120 }) {
  const radius = 50;
  const stroke = 8;
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const next = Math.max(0, Math.min(100, Number(score) || 0));
    const id = window.requestAnimationFrame(() => setAnimatedScore(next));
    return () => window.cancelAnimationFrame(id);
  }, [score]);

  const dashOffset = useMemo(() => {
    return circumference - (animatedScore / 100) * circumference;
  }, [animatedScore, circumference]);

  return (
    <div className="pal-ring" style={{ width: size, height: size, position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <svg height={size} width={size} style={{ transform: "rotate(-90deg)", position: "absolute", top: 0, left: 0 }}>
        <circle
          className="pal-ring__track"
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={size / 2}
          cy={size / 2}
          stroke="var(--border-subtle, rgba(255,255,255,0.1))"
        />
        <circle
          className="pal-ring__fill"
          fill="transparent"
          strokeWidth={stroke}
          strokeDasharray={`${circumference} ${circumference}`}
          style={{ strokeDashoffset: dashOffset }}
          strokeLinecap="round"
          r={normalizedRadius}
          cx={size / 2}
          cy={size / 2}
          stroke="currentColor"
        />
      </svg>
      <div className="pal-ring__label" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", zIndex: 2, textAlign: "center" }}>
        <div className="pal-ring__value mono" style={{ fontSize: `${size * 0.22}px`, fontWeight: 800, color: "#ffffff", lineHeight: 1.1 }}>
          {Math.round(animatedScore)}%
        </div>
        <div className="pal-ring__caption" style={{ fontSize: `${size * 0.09}px`, fontWeight: 600, color: "rgba(255,255,255,0.7)", textTransform: "uppercase", letterSpacing: "0.05em", marginTop: "2px" }}>
          PAL
        </div>
      </div>
    </div>
  );
}
