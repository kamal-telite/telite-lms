import { Panel, Badge, Avatar, EmptyState } from "../../components/common/ui";
import { ChartCanvas } from "../../components/common/charts";
import { formatPercent, getInitials, getRankColor, getScoreColor } from "../../utils/formatters";

export default function PALSection({ 
  dashboard, 
  isMoodleSource, 
  navigate 
}) {
  return (
    <section id="section-pal">
      <Panel
        className="panel"
        action={
          isMoodleSource ? (
            <Badge tone="neutral">live Moodle</Badge>
          ) : (
            <>
              <Badge tone="neutral">all-time</Badge>
              {dashboard.categories && dashboard.categories.length > 0 && (
                <button className="panel-link" type="button" onClick={() => navigate(`/categories/${dashboard.categories[0].slug}/stats`)}>
                  Full report
                </button>
              )}
            </>
          )
        }
      >
        <div id="section-pal" className="bar-list">
          {isMoodleSource ? (
            <EmptyState title="PAL data unavailable" body={dashboard.notes?.pal || "No PAL data returned from Moodle."} />
          ) : (
            dashboard.leaderboard.slice(0, 6).map((user, index) => (
              <div className="leaderboard-row" key={user.id}>
                <div className="leaderboard-rank" style={{ color: getRankColor(index + 1), fontWeight: 700 }}>
                  #{index + 1}
                </div>
                <Avatar
                  initials={user.avatar_initials || getInitials(user.full_name)}
                  gradient={user.avatar_gradient}
                  size={26}
                />
                <div style={{ flex: 1 }}>
                  <div className="row-title">{user.full_name}</div>
                  <div className="row-subtitle">{user.category_scope}</div>
                </div>
                <div className="bar-score">
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{ width: `${user.pal_score}%`, background: getScoreColor(user.pal_score) }}
                    />
                  </div>
                </div>
                <div className="mono" style={{ color: getScoreColor(user.pal_score), fontWeight: 700 }}>
                  {formatPercent(user.pal_score)}
                </div>
              </div>
            ))
          )}
        </div>

        <div style={{ marginTop: 18 }}>
          <div className="row-title" style={{ marginBottom: 12 }}>
            {isMoodleSource ? "Courses per managed category" : "PAL Score Distribution by Category"}
          </div>
          <ChartCanvas
            type="bar"
            height={190}
            labels={(isMoodleSource
              ? dashboard.analytics.courses_per_category
              : dashboard.analytics.avg_pal_per_category
            ).map((item) => item.category)}
            datasets={[
              {
                label: isMoodleSource ? "Courses" : "Average PAL",
                data: (isMoodleSource
                  ? dashboard.analytics.courses_per_category
                  : dashboard.analytics.avg_pal_per_category
                ).map((item) => item.value),
                backgroundColor: (isMoodleSource
                  ? dashboard.analytics.courses_per_category
                  : dashboard.analytics.avg_pal_per_category
                ).map((item) => item.color),
                borderRadius: 8,
              },
            ]}
            options={{
              indexAxis: "y",
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { display: false } },
              scales: {
                x: {
                  min: 0,
                  max: isMoodleSource ? undefined : 100,
                  border: { display: false },
                  grid: { color: "#F2F4F8" },
                  ticks: { color: "#94A3B8", font: { family: "Geist Mono", size: 10 } },
                },
                y: {
                  border: { display: false },
                  grid: { display: false },
                  ticks: { color: "#475569", font: { family: "Geist", size: 11 } },
                },
              },
            }}
          />
        </div>
      </Panel>
    </section>
  );
}
