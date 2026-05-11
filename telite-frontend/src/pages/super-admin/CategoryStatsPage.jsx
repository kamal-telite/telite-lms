import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { createTask, fetchStatsDashboard, getErrorMessage } from "../../services/client";
import { ChartCanvas } from "../../components/common/charts";
import { DashboardShell, ProfileDropdown } from "../../layouts/DashboardLayout";
import {
  Avatar,
  Badge,
  Button,
  EmptyState,
  ErrorState,
  LoadingState,
  Modal,
  Panel,
  StatCard,
  useToast,
} from "../../components/common/ui";
import {
  formatDateTime,
  formatMonthDate,
  formatPercent,
  getCompletionColor,
  getInitials,
  getRankColor,
  getScoreColor,
} from "../../utils/formatters";

const QUICK_TASK_INITIAL = {
  assigned_to_user_id: "",
  title: "",
  due_at: "",
};

const TASK_MODAL_INITIAL = {
  assigned_to_user_id: "all",
  title: "",
  due_at: "",
  priority: "medium",
  note: "",
};

export default function CategoryStatsPage({ session, onLogout }) {
  const { slug = "ats" } = useParams();
  const { showToast } = useToast();
  const scrollRef = useRef(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [courseFilter, setCourseFilter] = useState("all");
  const [learnerFilter, setLearnerFilter] = useState("active");
  const [activeNav, setActiveNav] = useState("section-overview");
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [leaderboardExpanded, setLeaderboardExpanded] = useState(false);
  const [timelineExpanded, setTimelineExpanded] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [quickTask, setQuickTask] = useState(QUICK_TASK_INITIAL);
  const [quickErrors, setQuickErrors] = useState({});
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [taskModal, setTaskModal] = useState(TASK_MODAL_INITIAL);
  const [taskModalErrors, setTaskModalErrors] = useState({});
  const [dynamicTimeline, setDynamicTimeline] = useState([]);

  useEffect(() => {
    load();
  }, [slug]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const payload = await fetchStatsDashboard(slug);
      setData(payload);
      setDynamicTimeline([]);
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to load the ATS stats dashboard."));
    } finally {
      setLoading(false);
    }
  }

  function scrollToSection(item) {
    setActiveNav(item.id);
    setExportOpen(false);
    const section = scrollRef.current?.querySelector(`#${item.id}`);
    section?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const navGroups = [
    {
      label: "Stats",
      items: [
        { id: "section-overview", label: "Overview", icon: "dashboard" },
        { id: "section-courses", label: "Course count", icon: "course" },
        { id: "section-users", label: "User count", icon: "users", badge: String(data?.kpis?.enrolled_learners || 0), badgeTone: "accent" },
        { id: "section-leaderboard", label: "PAL leaderboard", icon: "leaderboard" },
        { id: "section-tasks", label: "Task assignment", icon: "task" },
      ],
    },
    {
      label: "Analysis",
      items: [
        { id: "section-activity", label: "Activity log", icon: "reports" },
        { id: "section-overview", label: "Export data", icon: "download" },
      ],
    },
  ];

  const learners = useMemo(() => {
    return [...(data?.full_leaderboard || [])];
  }, [data]);

  const courseRows = useMemo(() => {
    const rows = data?.course_completion || [];
    if (courseFilter === "all") {
      return rows;
    }
    return rows.filter((row) => row.data_course === courseFilter);
  }, [courseFilter, data]);

  const leaderboardRows = learnerFilter === "archived" ? [] : data?.leaderboard || [];
  const fullLeaderboardRows = learnerFilter === "archived" ? [] : data?.full_leaderboard || [];
  const visibleTimeline = timelineExpanded
    ? [...dynamicTimeline, ...(data?.recent_activity || [])]
    : [...dynamicTimeline, ...(data?.recent_activity || []).slice(0, 5)];

  async function submitTaskAssignment(form, reset) {
    const errors = {};
    if (!form.assigned_to_user_id) errors.assigned_to_user_id = "Select a learner.";
    if (!form.title.trim()) errors.title = "Task description is required.";
    if (!form.due_at) errors.due_at = "Due date is required.";
    if (Object.keys(errors).length) {
      reset(errors);
      return;
    }

    const learner = learners.find((entry) => entry.id === form.assigned_to_user_id);
    const payload = {
      title: form.title,
      description: form.note || form.title,
      assigned_label: learner?.full_name || "All learners",
      assigned_to_user_id: learner?.id || null,
      assignment_scope: learner ? "individual" : "all_learners",
      category_slug: slug,
      due_at: form.due_at,
      status: "pending",
      notes: form.note || "",
      is_cross_category: false,
    };

    try {
      await createTask(payload);
      const timelineEntry = {
        id: `dynamic-${Date.now()}`,
        dot_bg: "#0891B2",
        symbol: "↗",
        text: `Admin assigned task '${form.title}' to ${learner?.full_name || "All learners"}`,
        meta: "just now",
      };
      setDynamicTimeline((current) => [timelineEntry, ...current]);
      showToast(`Task assigned to ${learner?.full_name || "All learners"}`, "info");
      reset({});
      return true;
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to assign task."), "error");
      return false;
    }
  }

  if (loading) {
    return <LoadingState title="Loading ATS Stats dashboard..." body="Preparing course analytics, PAL distributions, and activity trends." />;
  }

  if (error || !data) {
    return <ErrorState body={error || "The ATS stats dashboard did not return data."} action={<Button tone="primary" onClick={load}>Retry</Button>} />;
  }

  return (
    <>
      <DashboardShell
        theme="stats"
        brandMark={{ label: "ATS", background: "linear-gradient(135deg, #0891B2, #2563EB)" }}
        brandTitle="Telite LMS"
        brandSubtitle="ats · stats panel"
        navGroups={navGroups}
        activeNav={activeNav}
        onNavClick={scrollToSection}
        profile={{
          initials: "AK",
          gradient: ["#0891B2", "#2563EB"],
          name: session?.user?.name || "Anika Kapoor",
          roleLabel: "ats-stats",
        }}
        title="ATS Stats Dashboard"
        subtitle="ATS Learning Category · Apr 2026"
        topbarActions={
          <>
            <div className="menu-wrap">
              <Button tone="ghost" icon="download" onClick={() => setExportOpen((value) => !value)}>
                Export CSV
              </Button>
              {exportOpen ? (
                <div className="menu-popover">
                  <button type="button" onClick={() => { setExportOpen(false); showToast("Data export initiated...", "info"); }}>
                    Export as CSV
                  </button>
                  <button type="button" onClick={() => { setExportOpen(false); showToast("Data export initiated...", "info"); }}>
                    Export as PDF
                  </button>
                </div>
              ) : null}
            </div>
            <Button tone="primary" icon="plus" onClick={() => setTaskModalOpen(true)}>
              Assign task
            </Button>
            <ProfileDropdown profile={{
              initials: getInitials(session?.user?.name || "Category Admin"),
              gradient: ["#2563EB", "#059669"],
              name: session?.user?.name || "Category Admin",
              roleLabel: "category-admin",
            }} onLogout={onLogout} />
          </>
        }
        scrollRef={scrollRef}
      >
        <div className="dashboard-stack">
          <div className="filter-bar">
            <div className="quick-pills">
              {data.filters.course_filters.map((filter, index) => (
                <button
                  key={`course-filter-${filter}-${index}`}
                  type="button"
                  className={`chip ${courseFilter === filter ? "is-active" : ""}`}
                  onClick={() => setCourseFilter(filter)}
                >
                  {filter === "all" ? "All courses" : titleizeFilter(filter)}
                </button>
              ))}
            </div>
            <div className="filter-divider" />
            <div className="quick-pills">
              {data.filters.learner_filters.map((filter, index) => (
                <button
                  key={`learner-filter-${filter}-${index}`}
                  type="button"
                  className={`chip ${learnerFilter === filter ? "is-active" : ""}`}
                  onClick={() => setLearnerFilter(filter)}
                >
                  {filter === "active" ? "Active learners" : "Archived"}
                </button>
              ))}
            </div>
          </div>

          <section id="section-overview" className="grid-4">
            <BottomAccentStatCard label="Active Courses" value={data.kpis.active_courses} accent="#2563EB" meta="1 draft · Adv. PostgreSQL" />
            <BottomAccentStatCard label="Enrolled Learners" value={data.kpis.enrolled_learners} accent="#0891B2" meta="↑ 4 vs last month" />
            <BottomAccentStatCard label="Pending Learners" value={data.kpis.pending_learners} accent="#D97706" meta="⚠ awaiting approval" />
            <BottomAccentStatCard label="Avg PAL Score" value={data.kpis.avg_pal_score} suffix="%" accent="#7C3AED" meta="↑ 6% cohort average" />
          </section>

          <section id="section-courses" className="grid-2-wide">
            <Panel
              title="Course completion rate"
              subtitle="active courses"
              action={<button className="panel-link" type="button" onClick={() => setDetailsOpen((value) => !value)}>{detailsOpen ? "Hide details" : "Details"}</button>}
            >
              <div className="bar-list">
                {courseRows.map((row, index) => (
                  <div className="course-bar-row" key={`course-row-${row.course_name}-${index}`}>
                    <div className="course-bar-row__label">{row.course_name}</div>
                    <div className="progress-track" style={{ height: 8 }}>
                      <div
                        className="progress-fill"
                        style={{ width: `${row.completion_rate}%`, background: getCompletionColor(row.completion_rate) }}
                      />
                    </div>
                    <div className="course-bar-row__score" style={{ color: getCompletionColor(row.completion_rate) }}>
                      {formatPercent(row.completion_rate)}
                    </div>
                    <div className="course-bar-row__count">{row.completed_count}✓</div>
                  </div>
                ))}
              </div>

              {detailsOpen ? (
                <div className="table-wrap" style={{ marginTop: 16 }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Course</th>
                        <th>Tier</th>
                        <th>Enrolled</th>
                        <th>Completions</th>
                        <th>Avg Quiz Score</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.course_completion.map((row, index) => (
                        <tr key={`course-detail-${row.course_name}-${index}`}>
                          <td>{row.course_name}</td>
                          <td>{row.tier}</td>
                          <td className="mono">{row.enrolled_count}</td>
                          <td className="mono">{row.completed_count}</td>
                          <td className="mono">{row.avg_quiz_score}</td>
                          <td><Badge tone={row.status === "active" ? "success" : "warn"}>{row.status}</Badge></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}

              <div style={{ marginTop: 18, borderTop: "1px solid var(--border)", paddingTop: 16 }}>
                <div className="row-title" style={{ marginBottom: 12 }}>Enrollment trend - last 6 months</div>
                <ChartCanvas
                  type="bar"
                  height={140}
                  labels={data.enrollment_trend.labels}
                  datasets={[
                    {
                      label: "Learners enrolled",
                      data: data.enrollment_trend.values,
                      backgroundColor: "rgba(37,99,235,0.15)",
                      borderColor: "#2563EB",
                      borderWidth: 2,
                      borderRadius: 5,
                      borderSkipped: false,
                    },
                  ]}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                      x: { border: { display: false }, grid: { display: false }, ticks: { color: "#94A3B8", font: { family: "Geist Mono", size: 10 } } },
                      y: {
                        border: { display: false },
                        grid: { color: "#F2F4F8" },
                        ticks: { stepSize: 5, color: "#94A3B8", font: { family: "Geist Mono", size: 10 } },
                      },
                    },
                  }}
                />
              </div>
            </Panel>

            <div className="dashboard-stack">
              <Panel title="User breakdown" subtitle="enrolled vs pending">
                <div id="section-users" className="grid-2" style={{ alignItems: "center" }}>
                  <ChartCanvas
                    type="doughnut"
                    height={160}
                    labels={["Enrolled", "Pending"]}
                    datasets={[
                      {
                        data: [data.user_breakdown.enrolled, data.user_breakdown.pending],
                        backgroundColor: ["#2563EB", "#D97706"],
                        borderWidth: 0,
                        hoverOffset: 4,
                      },
                    ]}
                    centerLabel={{ title: `${data.user_breakdown.enrolled + data.user_breakdown.pending}`, subtitle: "users" }}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      cutout: "72%",
                      plugins: { legend: { display: false } },
                    }}
                  />
                  <div className="legend-list">
                    <LegendRow color="#2563EB" label="Enrolled" value={data.user_breakdown.enrolled} />
                    <LegendRow color="#D97706" label="Pending" value={data.user_breakdown.pending} />
                    <div style={{ borderTop: "1px solid var(--border)", marginTop: 6, paddingTop: 6 }}>
                      <LegendRow color="#7C3AED" label="Self-enrol" value={data.user_breakdown.self_enrol} />
                      <LegendRow color="#67E8F9" label="Manual" value={data.user_breakdown.manual} />
                    </div>
                  </div>
                </div>
              </Panel>

              <Panel title="PAL score distribution" subtitle={data.insight}>
                <div className="distribution-list">
                  {data.pal_distribution.map((row, index) => (
                    <div className="course-bar-row" key={`distribution-${row.range}-${index}`}>
                      <div className="course-bar-row__label" style={{ width: 70 }}>{row.range}</div>
                      <div className="distribution-track">
                        <div className="distribution-fill" style={{ width: `${row.width}%`, background: row.color }} />
                      </div>
                      <div className="course-bar-row__score" style={{ color: row.color }}>{row.count}</div>
                    </div>
                  ))}
                </div>
                <div className="stats-callout">{data.insight}</div>
              </Panel>
            </div>
          </section>

          <section id="section-leaderboard" className="grid-3-equal">
            <Panel title="PAL leaderboard" subtitle="Top ATS learners" action={<button className="panel-link" type="button" onClick={() => setLeaderboardExpanded((value) => !value)}>{leaderboardExpanded ? "Collapse" : "Full report"}</button>}>
              {learnerFilter === "archived" ? (
                <EmptyState title="No archived learners" body={data.archived_message} />
              ) : (
                <>
                  <div className="activity-list">
                    {(leaderboardExpanded ? fullLeaderboardRows : leaderboardRows).map((learner, index) => (
                      <div className="leaderboard-row" key={`leader-${learner.id || learner.full_name}-${index}`}>
                        <div className="leaderboard-rank" style={{ color: getRankColor(index + 1), fontWeight: 700 }}>
                          #{index + 1}
                        </div>
                        <Avatar initials={learner.avatar_initials || getInitials(learner.full_name)} gradient={learner.avatar_gradient} size={26} />
                        <div style={{ flex: 1 }}>
                          <div className="row-title">{learner.full_name}</div>
                          <div className="row-subtitle">{learner.courses_completed}/6 courses</div>
                        </div>
                        <div className="bar-score">
                          <div className="progress-track" style={{ height: 4 }}>
                            <div className="progress-fill" style={{ width: `${learner.pal_score}%`, background: getScoreColor(learner.pal_score) }} />
                          </div>
                        </div>
                        <div className="mono" style={{ color: getScoreColor(learner.pal_score) }}>{formatPercent(learner.pal_score)}</div>
                      </div>
                    ))}
                  </div>
                  <div style={{ marginTop: 16 }}>
                    <Button tone="ghost" className="btn--block" onClick={() => scrollToSection({ id: "section-users" })}>
                      Show all {data.kpis.enrolled_learners} learners
                    </Button>
                  </div>
                </>
              )}
            </Panel>

            <Panel title="Login activity" subtitle="last 12 weeks">
              <div id="section-tasks">
                <div className="row-subtitle" style={{ marginBottom: 10 }}>Daily logins · hover for details</div>
                <div className="heatmap-grid">
                  {data.heatmap_weights.slice(0, 84).map((value, index) => (
                    <div
                      key={`${index}-${value}`}
                      className="heatmap-cell"
                      style={{
                        background: value === 0 ? "var(--surface-3)" : `rgba(8, 145, 178, ${(0.15 + value * 0.85).toFixed(2)})`,
                      }}
                      title={`Week ${Math.floor(index / 7) + 1}, Day ${(index % 7) + 1}: ${Math.round(value * 18)} logins`}
                    />
                  ))}
                </div>
                <div className="heatmap-legend">
                  <span>Less</span>
                  {["var(--surface-3)", "rgba(8,145,178,.2)", "rgba(8,145,178,.45)", "rgba(8,145,178,.7)", "var(--teal)"].map((color, index) => (
                    <div key={`legend-${index}`} className="heatmap-legend__box" style={{ background: color }} />
                  ))}
                  <span>More</span>
                </div>
              </div>

              <div className="soft-card soft-card--tinted" style={{ marginTop: 16 }}>
                <div className="row-title" style={{ marginBottom: 10 }}>Quick task assignment</div>
                <form
                  className="task-form"
                  onSubmit={async (event) => {
                    event.preventDefault();
                    const success = await submitTaskAssignment(quickTask, setQuickErrors);
                    if (success) {
                      setQuickTask(QUICK_TASK_INITIAL);
                    }
                  }}
                >
                  <select
                    className={`field__select ${quickErrors.assigned_to_user_id ? "is-invalid" : ""}`}
                    value={quickTask.assigned_to_user_id}
                    onChange={(event) => {
                      setQuickTask((current) => ({ ...current, assigned_to_user_id: event.target.value }));
                      setQuickErrors((current) => ({ ...current, assigned_to_user_id: "" }));
                    }}
                  >
                    <option value="">Select learner...</option>
                    {learners.map((learner, index) => (
                      <option key={`quick-learner-${learner.id || learner.full_name}-${index}`} value={learner.id}>{learner.full_name}</option>
                    ))}
                  </select>
                  <input
                    className={`field__input ${quickErrors.title ? "is-invalid" : ""}`}
                    placeholder="Task description..."
                    value={quickTask.title}
                    onChange={(event) => {
                      setQuickTask((current) => ({ ...current, title: event.target.value }));
                      setQuickErrors((current) => ({ ...current, title: "" }));
                    }}
                  />
                  <input
                    className={`field__input ${quickErrors.due_at ? "is-invalid" : ""}`}
                    type="date"
                    value={quickTask.due_at}
                    onChange={(event) => {
                      setQuickTask((current) => ({ ...current, due_at: event.target.value }));
                      setQuickErrors((current) => ({ ...current, due_at: "" }));
                    }}
                  />
                  <Button tone="primary" type="submit" className="btn--block">Assign task</Button>
                </form>
              </div>
            </Panel>

            <Panel title="Recent activity" subtitle="Latest ATS events" action={<button className="panel-link" type="button" onClick={() => setTimelineExpanded((value) => !value)}>{timelineExpanded ? "Collapse" : "View all"}</button>}>
              <div id="section-activity" className="timeline-list">
                {learnerFilter === "archived" ? (
                  <EmptyState title="No archived learners" body={data.archived_message} />
                ) : (
                  visibleTimeline.map((item, index) => (
                    <div className="timeline-item" key={item.id || `${item.text}-${item.meta}-${index}`}>
                      <div className="timeline-dot" style={{ background: item.dot_bg }}>
                        {item.symbol}
                      </div>
                      <div className="timeline-content">
                        <p>{item.text}</p>
                        <small>{item.meta}</small>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Panel>
          </section>
        </div>
      </DashboardShell>

      <Modal
        open={taskModalOpen}
        onClose={() => setTaskModalOpen(false)}
        title="Assign Task"
        description="Create an ATS practice task with due date and priority."
        footer={
          <>
            <Button tone="ghost" onClick={() => setTaskModalOpen(false)}>Cancel</Button>
            <Button
              tone="primary"
              onClick={async (event) => {
                const success = await submitTaskAssignment(taskModal, setTaskModalErrors);
                if (success) {
                  setTaskModal(TASK_MODAL_INITIAL);
                  setTaskModalOpen(false);
                }
              }}
            >
              Assign Task
            </Button>
          </>
        }
      >
        <form
          className="form-stack"
          onSubmit={async (event) => {
            event.preventDefault();
            const success = await submitTaskAssignment(taskModal, setTaskModalErrors);
            if (success) {
              setTaskModal(TASK_MODAL_INITIAL);
              setTaskModalOpen(false);
            }
          }}
        >
          <label className="field">
            <span className="field__label">Assign to</span>
            <select
              className={`field__select ${taskModalErrors.assigned_to_user_id ? "is-invalid" : ""}`}
              value={taskModal.assigned_to_user_id}
              onChange={(event) => {
                setTaskModal((current) => ({ ...current, assigned_to_user_id: event.target.value }));
                setTaskModalErrors((current) => ({ ...current, assigned_to_user_id: "" }));
              }}
            >
              <option value="all">All learners</option>
              {learners.map((learner, index) => (
                <option key={`modal-learner-${learner.id || learner.full_name}-${index}`} value={learner.id}>{learner.full_name}</option>
              ))}
            </select>
            {taskModalErrors.assigned_to_user_id ? <span className="field__error">{taskModalErrors.assigned_to_user_id}</span> : null}
          </label>
          <label className="field">
            <span className="field__label">Task description</span>
            <input
              className={`field__input ${taskModalErrors.title ? "is-invalid" : ""}`}
              value={taskModal.title}
              onChange={(event) => {
                setTaskModal((current) => ({ ...current, title: event.target.value }));
                setTaskModalErrors((current) => ({ ...current, title: "" }));
              }}
              placeholder="What should they do?"
            />
            {taskModalErrors.title ? <span className="field__error">{taskModalErrors.title}</span> : null}
          </label>
          <div className="field-grid">
            <label className="field">
              <span className="field__label">Due date</span>
              <input
                className={`field__input ${taskModalErrors.due_at ? "is-invalid" : ""}`}
                type="date"
                value={taskModal.due_at}
                onChange={(event) => {
                  setTaskModal((current) => ({ ...current, due_at: event.target.value }));
                  setTaskModalErrors((current) => ({ ...current, due_at: "" }));
                }}
              />
              {taskModalErrors.due_at ? <span className="field__error">{taskModalErrors.due_at}</span> : null}
            </label>
            <label className="field">
              <span className="field__label">Priority</span>
              <select className="field__select" value={taskModal.priority} onChange={(event) => setTaskModal((current) => ({ ...current, priority: event.target.value }))}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </label>
          </div>
          <label className="field">
            <span className="field__label">Note</span>
            <textarea
              className="field__textarea"
              value={taskModal.note}
              onChange={(event) => setTaskModal((current) => ({ ...current, note: event.target.value }))}
              placeholder="Optional note or context..."
            />
          </label>
        </form>
      </Modal>
    </>
  );
}

function BottomAccentStatCard({ label, value, suffix, accent, meta }) {
  return (
    <article className="stat-card stat-card--bottom">
      <div className="stat-card__label">{label}</div>
      <div className="stat-card__value">
        <span>{value}</span>
        {suffix ? <small>{suffix}</small> : null}
      </div>
      <div className="stat-card__meta">{meta}</div>
      <span className="stat-card__accent stat-card__accent--bottom" style={{ background: accent }} />
    </article>
  );
}

function LegendRow({ color, label, value }) {
  return (
    <div className="legend-row">
      <span className="legend-dot" style={{ background: color }} />
      <span>{label}</span>
      <strong className="mono" style={{ marginLeft: "auto" }}>{value}</strong>
    </div>
  );
}

function titleizeFilter(value) {
  if (value === "frontend") return "Frontend";
  if (value === "backend") return "Backend";
  if (value === "postgresql") return "PostgreSQL";
  return value;
}
