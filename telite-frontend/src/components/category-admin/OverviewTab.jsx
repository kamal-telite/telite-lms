import { StatCard, Panel, Button, Avatar, Badge, EmptyState, IconButton } from "../../components/common/ui";
import { formatMonthDate, formatPercent, getCompletionColor, getInitials, getScoreColor, titleize } from "../../utils/formatters";

export default function OverviewTab({ 
  dashboard, 
  labels, 
  handleTabChange, 
  handleApprove, 
  handleReject, 
  handleQuickEnroll, 
  manualQuickInput, 
  setManualQuickInput, 
  quickError, 
  setQuickError, 
  learners, 
  totalLearners, 
  setDetailLearner, 
  setDeleteLearnerId, 
  deleteLearnerId, 
  handleDeleteLearner, 
  toggleTask, 
  setTaskModal,
  navigate,
  slug,
  kpiPulse
}) {
  return (
    <>
      <div className="grid-4">
        <StatCard accent="#2563EB" label="Total Courses" value={dashboard?.kpis?.total_courses || 0} meta="↑ 2 this quarter" pulse={Boolean(kpiPulse?.total_courses)} />
        <StatCard
          label={`Active ${labels.users}`}
          value={dashboard?.kpis?.active_learners || 0}
          delta={kpiPulse?.active_learners || 0}
          icon="users"
        />
        <StatCard
          label={`Avg PAL Score (${labels.users})`}
          value={formatPercent(dashboard?.kpis?.avg_pal_score || 0)}
          delta={kpiPulse?.avg_pal_score || 0}
          icon="pal"
        />
      </div>

      <div className="grid-2-wide">
        <Panel
          title="Top Courses"
          subtitle={`${dashboard?.courses?.length || 0} total`}
          action={<button className="panel-link" type="button" onClick={() => handleTabChange("courses")}>View all</button>}
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Course</th>
                  <th>Tier</th>
                  <th>Enrolled</th>
                  <th>Completion</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {(dashboard?.courses || []).slice(0, 5).map((course) => (
                  <tr key={course.id}>
                    <td>
                      <div className="row-title">{course.name}</div>
                      <div className="row-subtitle">{course.description}</div>
                    </td>
                    <td>
                      <Badge tone={course.tier === "Advanced" ? "accent" : "brand"}>{course.tier}</Badge>
                    </td>
                    <td className="mono">{course.enrolled_count}</td>
                    <td>
                      <div className="progress-track" style={{ width: 90 }}>
                        <div
                          className="progress-fill"
                          style={{ width: `${course.completion_rate}%`, background: getCompletionColor(course.completion_rate) }}
                        />
                      </div>
                      <div className="row-subtitle mono">{formatPercent(course.completion_rate)}</div>
                    </td>
                    <td>
                      <Badge tone={course.status === "published" || course.status === "active" ? "success" : course.status === "draft" ? "neutral" : "warn"}>{titleize(course.status)}</Badge>
                    </td>
                    <td>
                      <div className="split-actions">
                        <Button tone="primary" size="sm" onClick={() => navigate(`/categories/${slug}/builder/${course.id}`)}>Edit</Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Pending enrollment" subtitle="Needs review">
          <div className="activity-list" style={{ maxHeight: "300px", overflowY: "auto" }}>
            {!dashboard?.pending_enrollment?.length ? (
              <EmptyState title="No pending requests" description="All signups for your organization have been processed." icon="shield" />
            ) : (
              (dashboard?.pending_enrollment || []).slice(0, 3).map((request) => (
                <div className="activity-item" key={request.id}>
                  <Avatar
                    initials={getInitials(request.full_name)}
                    gradient={request.domain_verified ? ["#7C3AED", "#2563EB"] : ["#D97706", "#92400E"]}
                    size={32}
                  />
                  <div style={{ flex: 1 }}>
                    <div className="row-title">{request.full_name}</div>
                    <div className="row-subtitle">
                      {request.request_type} · {formatMonthDate(request.requested_at)} · {request.company_domain}
                      {!request.domain_verified ? " ⚠" : ""}
                    </div>
                  </div>
                  <div className="split-actions">
                    <Button tone="success" size="sm" onClick={() => handleApprove(request.id)}>Approve</Button>
                    <Button tone="danger" size="sm" onClick={() => handleReject(request.id)}>Deny</Button>
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="soft-card soft-card--tinted" style={{ marginTop: 16 }}>
            <div className="row-title" style={{ marginBottom: 10 }}>Manual enrollment</div>
            <div className="split-actions" style={{ alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <input
                  className={`field__input ${quickError ? "is-invalid" : ""}`}
                  value={manualQuickInput}
                  onChange={(event) => {
                    setManualQuickInput(event.target.value);
                    setQuickError("");
                  }}
                  placeholder={`Search ${labels.user.toLowerCase()} by name or email...`}
                />
                {quickError ? <div className="field__error">{quickError}</div> : null}
              </div>
              <Button tone="primary" onClick={handleQuickEnroll}>Enroll</Button>
            </div>
          </div>
        </Panel>
      </div>

      <div className="grid-2-wide">
        <Panel title={`Active ${labels.users}`} subtitle={`${totalLearners} enrolled`} action={<button className="panel-link" type="button" onClick={() => handleTabChange("learners")}>Manage all</button>}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{labels.user}</th>
                  <th>Enrolled</th>
                  <th>Courses</th>
                  <th>PAL Score</th>
                  <th>Type</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {learners.slice(0, 4).map((learner) => (
                  <tr key={learner.id}>
                    <td>
                      <div className="leaderboard-row" style={{ padding: 0, borderBottom: 0 }}>
                        <Avatar initials={learner.avatar_initials || getInitials(learner.full_name)} gradient={learner.avatar_gradient} size={26} />
                        <div>
                          <div className="row-title">{learner.full_name}</div>
                          <div className="row-subtitle">{learner.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="mono">{formatMonthDate(learner.created_at)}</td>
                    <td className="mono">{learner.courses_completed}/{learner.total_courses}</td>
                    <td className="mono" style={{ color: getScoreColor(learner.pal_score) }}>{formatPercent(learner.pal_score)}</td>
                    <td><Badge tone={learner.enrollment_type === "self" ? "accent" : "brand"}>{learner.enrollment_type}</Badge></td>
                    <td>
                      <div className="split-actions">
                        <IconButton label="View learner" icon="eye" onClick={() => setDetailLearner(learner)} />
                        <IconButton label="Delete learner" icon="trash" onClick={() => setDeleteLearnerId((value) => (value === learner.id ? null : learner.id))} />
                      </div>
                      {deleteLearnerId === learner.id ? (
                        <div className="inline-confirm">
                          <span>Remove this {labels.user.toLowerCase()}?</span>
                          <div className="split-actions">
                            <Button tone="danger" onClick={() => handleDeleteLearner(learner.id)}>Confirm delete</Button>
                            <Button tone="ghost" onClick={() => setDeleteLearnerId(null)}>Cancel</Button>
                          </div>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: 16 }}>
            <Button tone="ghost" className="btn--block" onClick={() => handleTabChange("learners")}>
              Show all {totalLearners} {labels.users.toLowerCase()}
            </Button>
          </div>
        </Panel>

        <Panel title="Task board" subtitle="Category assignments" action={<button className="panel-link" type="button" onClick={() => setTaskModal({ open: true, item: null })}>+ Assign task</button>}>
          <div className="activity-list">
            {(dashboard?.tasks || []).map((task) => (
              <label className="task-row" key={task.id}>
                <input
                  type="checkbox"
                  checked={task.status === "completed"}
                  onChange={() => toggleTask(task)}
                />
                <div style={{ flex: 1 }}>
                  <div className="row-title">{task.title}</div>
                  <div className="row-subtitle">
                    {task.assigned_label} · {task.status === "completed" ? `done · ${formatMonthDate(task.due_at)}` : task.status === "overdue" ? "Overdue!" : `due ${formatMonthDate(task.due_at)}`}
                  </div>
                </div>
              </label>
            ))}
          </div>
          <div style={{ marginTop: 16 }}>
            <Button tone="ghost" className="btn--block" onClick={() => handleTabChange("tasks")}>
              View full task board
            </Button>
          </div>
        </Panel>
      </div>
    </>
  );
}
