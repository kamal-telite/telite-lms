import { Panel } from "../../components/common/ui";
import { ChartCanvas } from "../../components/common/charts";

export default function AnalyticsSection({ 
  dashboard, 
  isMoodleSource 
}) {
  return (
    <section id="section-analytics">
      <Panel
        title="Analytics"
        subtitle={
          isMoodleSource
            ? "Live Moodle account and category distribution"
            : "Cross-category learner and PAL distribution"
        }
      >
        <div className="grid-2">
          <div className="soft-card">
            <div className="row-title" style={{ marginBottom: 12 }}>
              {isMoodleSource ? "Moodle account status" : "Learners per category"}
            </div>
            <ChartCanvas
              type="doughnut"
              height={240}
              labels={(isMoodleSource
                ? dashboard.analytics.user_status_distribution
                : dashboard.analytics.learners_per_category
              ).map((item) => item.category)}
              datasets={[
                {
                  data: (isMoodleSource
                    ? dashboard.analytics.user_status_distribution
                    : dashboard.analytics.learners_per_category
                  ).map((item) => item.value),
                  backgroundColor: (isMoodleSource
                    ? dashboard.analytics.user_status_distribution
                    : dashboard.analytics.learners_per_category
                  ).map((item) => item.color),
                  borderWidth: 0,
                  hoverOffset: 4,
                },
              ]}
              centerLabel={{
                title: isMoodleSource
                  ? `${dashboard.kpis.total_learners} Active`
                  : `${dashboard.kpis.total_learners} Learners`,
                subtitle: isMoodleSource ? "Moodle users" : "active",
              }}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                cutout: "72%",
                plugins: { legend: { position: "bottom" } },
              }}
            />
          </div>
          <div className="soft-card">
            <div className="row-title" style={{ marginBottom: 12 }}>
              {isMoodleSource ? "Courses per managed category" : "Avg PAL Score per category"}
            </div>
            <ChartCanvas
              type="bar"
              height={240}
              labels={(isMoodleSource
                ? dashboard.analytics.courses_per_category
                : dashboard.analytics.avg_pal_per_category
              ).map((item) => item.category)}
              datasets={[
                {
                  label: isMoodleSource ? "Courses" : "Avg PAL",
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
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                  x: {
                    border: { display: false },
                    grid: { display: false },
                    ticks: { color: "#475569", font: { family: "Geist", size: 11 } },
                  },
                  y: {
                    min: 0,
                    max: isMoodleSource ? undefined : 100,
                    border: { display: false },
                    grid: { color: "#F2F4F8" },
                    ticks: { color: "#94A3B8", font: { family: "Geist Mono", size: 10 } },
                  },
                },
              }}
            />
          </div>
        </div>
      </Panel>
    </section>
  );
}
