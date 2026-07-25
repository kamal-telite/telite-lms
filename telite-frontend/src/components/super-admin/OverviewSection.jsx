import { StatCard, Panel, Button, Avatar, Badge, EmptyState } from "../../components/common/ui";
import { formatShortDate, formatPercent, getInitials, getRankColor, getScoreColor, getStatusTone } from "../../utils/formatters";

export default function OverviewSection({ 
  dashboard, 
  kpiPulse, 
  handleApprove, 
  handleReject 
}) {
  return (
    <section className="dashboard-stack">
      <div className="grid-4">
        <StatCard
          accent="#7C3AED"
          label="Total Categories"
          value={dashboard.kpis.total_categories}
          meta={`${dashboard.kpis?.total_categories || 0} active`}
          pulse={kpiPulse.total_categories}
        />
        <StatCard
          accent="#2563EB"
          label="Total Courses"
          value={dashboard.kpis.total_courses}
          meta="Across all categories"
          pulse={kpiPulse.total_courses}
        />
        <StatCard
          accent="#059669"
          label="Total Learners"
          value={dashboard?.kpis?.total_users || 0}
          meta="Enrolled this quarter"
          pulse={kpiPulse.total_learners}
        />
        <StatCard
          accent="#D97706"
          label="Pending Approvals"
          value={dashboard.kpis.pending_approvals}
          meta="Requires action"
          pulse={kpiPulse.pending_approvals}
        />
      </div>

      <div className="grid-2" style={{ marginTop: 18 }}>
        <Panel title="Recent enrollments" subtitle="Latest 10 enrollment requests">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Requested</th>
                </tr>
              </thead>
              <tbody>
                {(dashboard.enrollment_audit?.rows || []).slice(0, 10).map((row) => (
                  <tr key={row.request_id}>
                    <td>
                      <div className="row-title">{row.full_name}</div>
                      <div className="row-subtitle">{row.email || ""}</div>
                    </td>
                    <td className="muted">{row.category}</td>
                    <td>
                      <Badge tone={getStatusTone(row.status)}>{row.status}</Badge>
                    </td>
                    <td className="mono" style={{ whiteSpace: "nowrap" }}>
                      {formatShortDate(row.requested_at || row.created_at || "") || "—"}
                    </td>
                  </tr>
                ))}
                {(dashboard.enrollment_audit?.rows || []).length === 0 ? (
                  <tr>
                    <td colSpan="4">
                      <EmptyState title="No enrollments yet" body="Enrollment requests will show up here once learners start joining." />
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Top learners by PAL score" subtitle="Current leaders across categories">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 60, textAlign: "center" }}>Rank</th>
                  <th>Learner</th>
                  <th style={{ textAlign: "right" }}>PAL</th>
                </tr>
              </thead>
              <tbody>
                {(dashboard.leaderboard || []).slice(0, 5).map((user, idx) => (
                  <tr key={user.id || `${user.full_name}-${idx}`}>
                    <td style={{ textAlign: "center", fontWeight: 700, color: getRankColor(idx + 1) }}>
                      #{idx + 1}
                    </td>
                    <td>
                      <div className="leaderboard-row" style={{ padding: 0, borderBottom: 0 }}>
                        <Avatar
                          initials={user.avatar_initials || getInitials(user.full_name)}
                          gradient={user.avatar_gradient || ["#2563EB", "#7C3AED"]}
                          size={26}
                        />
                        <div>
                          <div className="row-title">{user.full_name}</div>
                          <div className="row-subtitle">{user.category_scope}</div>
                        </div>
                      </div>
                    </td>
                    <td className="mono" style={{ textAlign: "right", fontWeight: 700, color: getScoreColor(user.pal_score) }}>
                      {formatPercent(user.pal_score)}
                    </td>
                  </tr>
                ))}
                {(dashboard.leaderboard || []).length === 0 ? (
                  <tr>
                    <td colSpan="3">
                      <EmptyState title="No PAL data yet" body="Once learners start progressing, this leaderboard will populate automatically." />
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </section>
  );
}
