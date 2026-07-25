import { Panel, StatCard, EmptyState } from "../../common/ui";
import { ChartCanvas } from "../../common/charts";
import { PalRing } from "../PalRing";
import {
  formatPercent,
  getScoreColor,
  titleize,
  formatDateTime,
} from "../../../utils/formatters";
import { Badge } from "../../common/ui";

/**
 * PalProgressSection - PAL score analysis and progress tracking
 */
export function PalProgressSection({ hero, palBreakdown }) {
  const trend = palBreakdown.progress_trend || [];
  const timeline = palBreakdown.completion_timeline || [];

  return (
    <section id="section-pal" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div
        className="hero-banner"
        style={{
          background: "linear-gradient(135deg, var(--warning, #f59e0b), var(--accent, #7C3AED))",
          padding: "48px 24px",
          borderRadius: "16px",
          boxShadow: "var(--shadow-card, 0 4px 20px rgba(0,0,0,0.15))",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          textAlign: "center",
          position: "relative",
          overflow: "hidden"
        }}
      >
        {/* Subtle decorative glow */}
        <div style={{
          position: "absolute",
          top: "-50%",
          left: "-50%",
          width: "200%",
          height: "200%",
          background: "radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 60%)",
          pointerEvents: "none"
        }} />

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "20px",
            zIndex: 1,
            width: "100%",
            maxWidth: "600px"
          }}
        >
          <div style={{ transform: "scale(1.1)", transformOrigin: "center" }}>
            <PalRing score={Math.round(Number(hero.pal_score) || 0)} size={130} />
          </div>
          <div>
            <h2 style={{ fontSize: "clamp(1.6rem, 4vw, 2.2rem)", fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 8px 0", color: "#ffffff" }}>
              PAL Score Analysis
            </h2>
            <p style={{ fontSize: "clamp(0.95rem, 2vw, 1.1rem)", margin: 0, opacity: 0.95, color: "#ffffff", lineHeight: 1.5, fontWeight: 400 }}>
              Your holistic performance rating across all modules.
            </p>
          </div>
        </div>
      </div>

      <Panel title="PAL Dimensions" subtitle="How your score is calculated">
        <div style={{ display: "flex", flexDirection: "column", gap: "16px", width: "100%" }}>
          {[
            {
              label: "Course Completion",
              value: palBreakdown.completion || 0,
              weight: 0.3,
            },
            {
              label: "Quiz Average",
              value: palBreakdown.pal_quiz_avg || 0,
              weight: 0.3,
            },
            {
              label: "Assignment Average",
              value: palBreakdown.assignment_average || 0,
              weight: 0.2,
            },
            {
              label: "Task Completion",
              value: palBreakdown.task_completion || 0,
              weight: 0.2,
            },
          ].map((dim) => (
            <div 
              key={dim.label}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr",
                gap: "8px",
                padding: "16px",
                borderRadius: "12px",
                background: "var(--surface-raised, rgba(255,255,255,0.02))",
                border: "1px solid var(--border-subtle, rgba(255,255,255,0.08))",
                boxShadow: "var(--shadow-sm, 0 1px 2px rgba(0,0,0,0.05))"
              }}
              className="pal-dimension-item"
            >
              {/* Top Row: Metric Name & weight / value for mobile or base flex container */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                <span style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }}>{dim.label}</span>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 500 }}>Weight: {dim.weight * 100}%</span>
                  <span className="mono" style={{ fontSize: "14px", fontWeight: 700, color: getScoreColor(dim.value) }}>
                    {formatPercent(dim.value)}
                  </span>
                </div>
              </div>
              {/* Progress bar */}
              <div 
                style={{
                  width: "100%",
                  height: "8px",
                  background: "var(--surface-3, rgba(255,255,255,0.1))",
                  borderRadius: "999px",
                  overflow: "hidden"
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${dim.value}%`,
                    background: getScoreColor(dim.value),
                    borderRadius: "inherit",
                    transition: "width 0.8s cubic-bezier(0.16, 1, 0.3, 1)"
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <style dangerouslySetInnerHTML={{__html: `
        @media (min-width: 640px) {
          .pal-dimension-item {
            grid-template-columns: 180px 1fr 60px 100px !important;
            align-items: center !important;
            gap: 20px !important;
            padding: 16px 20px !important;
          }
          .pal-dimension-item > div:first-of-type {
            display: contents !important;
          }
        }
      `}} />

      <div className="grid-4">
        <StatCard
          accent="var(--primary, #2563EB)"
          label="Current Rank"
          value={
            palBreakdown.current_rank
              ? `#${palBreakdown.current_rank}`
              : "-"
          }
          meta="Category leaderboard"
        />
        <StatCard
          accent="var(--success, #059669)"
          label="Leaderboard Position"
          value={
            palBreakdown.leaderboard_position
              ? `#${palBreakdown.leaderboard_position}`
              : "-"
          }
          meta="Dynamic PAL score"
        />
        <StatCard
          accent="var(--accent, #7C3AED)"
          label="Highest Strength"
          value={(palBreakdown.strengths || [])[0] || "Building"}
          meta={`${(palBreakdown.strengths || []).length} strong areas`}
        />
        <StatCard
          accent="var(--warning, #D97706)"
          label="Focus Area"
          value={(palBreakdown.weak_areas || [])[0] || "Balanced"}
          meta={`${(palBreakdown.weak_areas || []).length} weak areas`}
        />
      </div>

      <div className="grid-2">
        <Panel title="Progress Trend" subtitle="Recent learning activity">
          {trend.length ? (
            <ChartCanvas
              type="bar"
              height={180}
              labels={trend.map((item) => item.label)}
              datasets={[
                {
                  label: "Activity",
                  data: trend.map((item) => item.value),
                  backgroundColor: "#2563EB",
                  borderRadius: 8,
                },
              ]}
            />
          ) : (
            <EmptyState
              title="No trend yet"
              body="Learning activity will appear here automatically."
            />
          )}
        </Panel>
        <Panel title="Completion Timeline" subtitle="Latest modules, quizzes, and submissions">
          {timeline.length ? (
            <div className="activity-list">
              {timeline.slice(0, 5).map((item, index) => (
                <div
                  className="activity-item"
                  key={`${item.type}-${item.created_at}-${index}`}
                >
                  <div className="activity-item__main">
                    <div className="activity-item__title">
                      {titleize(
                        String(item.type || "").replaceAll("_", " ")
                      )}
                    </div>
                    <div className="activity-item__meta">
                      {item.created_at
                        ? formatDateTime(item.created_at)
                        : "Recently"}
                    </div>
                  </div>
                  {item.payload?.score !== undefined ? (
                    <Badge tone="info">{Math.round(item.payload.score)}%</Badge>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No completions yet"
              body="Completed activities will appear here automatically."
            />
          )}
        </Panel>
      </div>
    </section>
  );
}
