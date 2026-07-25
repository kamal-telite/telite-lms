import { StatCard, Panel, EmptyState, LoadingState } from "../../components/common/ui";
import { ChartCanvas } from "../../components/common/charts";
import { getScoreColor } from "../../utils/formatters";

export default function GradingSection({ 
  gradingAnalytics, 
  gradingLoading 
}) {
  if (gradingLoading) {
    return <LoadingState title="Loading grading analytics..." body="Fetching grade data across the organization." />;
  }

  if (!gradingAnalytics) {
    return null;
  }

  return (
    <section id="section-grading">
      <div className="grid-4">
        <StatCard accent="#7C3AED" label="Overall Average Grade" value={`${gradingAnalytics.overall_average}%`} meta="Across all courses" />
        <StatCard accent="#059669" label="Pass Rate" value={`${gradingAnalytics.pass_rate}%`} meta="Grades ≥ 60%" />
        <StatCard accent="#DC2626" label="Fail Rate" value={`${gradingAnalytics.fail_rate}%`} meta="Grades < 60%" />
        <StatCard accent="#2563EB" label="Total Assessments" value={gradingAnalytics.total_assessments} meta="Grade items created" />
      </div>

      <div className="grid-2-wide" style={{ marginTop: 18 }}>
        <Panel title="Grade Distribution" subtitle="Letter grade breakdown">
          <ChartCanvas
            type="bar"
            height={200}
            labels={gradingAnalytics.grade_distribution.map(d => d.label)}
            datasets={[
              {
                label: "Count",
                data: gradingAnalytics.grade_distribution.map(d => d.count),
                backgroundColor: ["#059669", "#2563EB", "#7C3AED", "#F59E0B", "#DC2626"],
                borderRadius: 8,
              },
            ]}
            options={{
              indexAxis: "y",
              plugins: { legend: { display: false } },
              scales: { x: { beginAtZero: true } },
            }}
          />
        </Panel>

        <Panel title="Top Performing Categories" subtitle="By average grade">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Category</th>
                  <th style={{ textAlign: "right" }}>Average</th>
                </tr>
              </thead>
              <tbody>
                {gradingAnalytics.top_categories.length > 0 ? (
                  gradingAnalytics.top_categories.map((cat, idx) => (
                    <tr key={idx}>
                      <td>{cat.name}</td>
                      <td className="mono" style={{ textAlign: "right", color: getScoreColor(cat.average) }}>
                        {cat.average}%
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="2">
                      <EmptyState title="No category data" body="Grade categories will appear here once grading is active." />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      <div className="grid-2-wide" style={{ marginTop: 18 }}>
        <Panel title="Lowest Performing Categories" subtitle="Categories needing attention">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Category</th>
                  <th style={{ textAlign: "right" }}>Average</th>
                </tr>
              </thead>
              <tbody>
                {gradingAnalytics.lowest_categories.length > 0 ? (
                  gradingAnalytics.lowest_categories.map((cat, idx) => (
                    <tr key={idx}>
                      <td>{cat.name}</td>
                      <td className="mono" style={{ textAlign: "right", color: getScoreColor(cat.average) }}>
                        {cat.average}%
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="2">
                      <EmptyState title="No data" body="Insufficient data for lowest performers." />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Organization Grade Trend" subtitle="Last 6 months">
          <ChartCanvas
            type="line"
            height={200}
            labels={gradingAnalytics.grade_trend.map(t => t.month)}
            datasets={[
              {
                label: "Average Grade",
                data: gradingAnalytics.grade_trend.map(t => t.average),
                borderColor: "#7C3AED",
                backgroundColor: "rgba(124, 58, 237, 0.1)",
                fill: true,
                tension: 0.4,
              },
            ]}
            options={{
              plugins: { legend: { display: false } },
              scales: { y: { beginAtZero: true, max: 100 } },
            }}
          />
        </Panel>
      </div>

      <Panel title="Grading Summary" subtitle="Key metrics" style={{ marginTop: 18 }}>
        <div className="grid-3">
          <div className="soft-card">
            <div className="row-title">Total Graded Learners</div>
            <div className="row-subtitle mono" style={{ fontSize: "24px", fontWeight: 700, color: "#7C3AED" }}>
              {gradingAnalytics.total_graded_learners}
            </div>
          </div>
          <div className="soft-card">
            <div className="row-title">Total Assessments</div>
            <div className="row-subtitle mono" style={{ fontSize: "24px", fontWeight: 700, color: "#2563EB" }}>
              {gradingAnalytics.total_assessments}
            </div>
          </div>
          <div className="soft-card">
            <div className="row-title">Overall Average</div>
            <div className="row-subtitle mono" style={{ fontSize: "24px", fontWeight: 700, color: "#059669" }}>
              {gradingAnalytics.overall_average}%
            </div>
          </div>
        </div>
      </Panel>
    </section>
  );
}
