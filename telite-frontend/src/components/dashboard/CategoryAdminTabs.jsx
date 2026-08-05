import React, { useEffect, useMemo, useState } from "react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { Avatar, Badge, Button, EmptyState, Modal, Panel, useToast } from "../common/ui";
import { TaskBoardKanban } from "./TaskBoard";
import { AccountSettingsPanel } from "../common/AccountSettingsPanel";
import { ChartCanvas } from "../common/charts";
import { Icon } from "../common/icons";
import { formatDateTime, titleize, getScoreColor, getInitials, formatPercent, getRankColor } from "../../utils/formatters";
import {
  fetchArchivedCourses,
  getErrorMessage,
  permanentlyDeleteArchivedCourse,
  restoreArchivedCourse,
} from "../../services/client";

export function ActivityFeedTab({ events = [] }) {
  const [filter, setFilter] = useState("all");

  const displayEvents = events.length ? events.map(e => ({
    id: e.id,
    type: e.type || (e.icon === 'launch' || e.icon === 'check' ? 'task' : e.icon === 'plus' ? 'enrollment' : 'system'),
    status: e.status || (e.accent === 'emerald' || e.accent === 'teal' ? 'success' : e.accent === 'red' ? 'error' : e.accent === 'warning' ? 'warning' : 'info'),
    title: e.message || e.title,
    timestamp: e.created_at ? new Date(e.created_at) : e.timestamp
  })) : [];
  const filteredEvents = displayEvents.filter(e => filter === "all" || e.type === filter);

  const statusDotClass = (status) => {
    if (status === "success") return "activity-dot activity-dot--success";
    if (status === "error") return "activity-dot activity-dot--error";
    if (status === "warning") return "activity-dot activity-dot--warning";
    return "activity-dot activity-dot--info";
  };

  return (
    <Panel
      title="Activity Feed"
      subtitle="Real-time chronological event log across the category."
    >
      <div className="admin-tab-toolbar">
        {["all", "enrollment", "verification", "task", "pal", "course"].map(f => (
          <label className="chip" key={f}>
            <input
              type="radio"
              name="activity_filter"
              checked={filter === f}
              onChange={() => setFilter(f)}
            /> {titleize(f)}
          </label>
        ))}
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th style={{ width: 180 }}>Timestamp</th>
              <th>Event Details</th>
              <th style={{ width: 120 }}>Category</th>
            </tr>
          </thead>
          <tbody>
            {filteredEvents.map(evt => (
              <tr key={evt.id}>
                <td className="mono muted">{formatDateTime(evt.timestamp.toISOString ? evt.timestamp.toISOString() : evt.timestamp)}</td>
                <td>
                  <div className="activity-event-row">
                    <span className={statusDotClass(evt.status)} aria-hidden="true" />
                    <span>{evt.title}</span>
                  </div>
                </td>
                <td><Badge tone="neutral">{titleize(evt.type)}</Badge></td>
              </tr>
            ))}
            {filteredEvents.length === 0 && (
              <tr>
                <td colSpan="3" className="table-empty-cell">
                  <div className="muted">No activity matching the filter.</div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

export function SettingsTab({ dashboard }) {
  return (
    <div className="settings-layout">
      <Panel
        title="Category Settings"
        subtitle="Manage category configuration."
        footer={<Button tone="primary">Save Changes</Button>}
      >
        <div className="settings-form">
          <label className="field">
            <span className="field__label">Category Display Name</span>
            <input className="field__input" defaultValue={dashboard?.category?.name || "Category Name"} />
          </label>
          <label className="field">
            <span className="field__label">Category Description</span>
            <textarea className="field__textarea" rows={4} defaultValue={dashboard?.category?.description || ""} />
          </label>

          <div className="settings-form__section">
            <h4 className="settings-form__section-title">Enrollment Approval</h4>
            <div className="settings-form__options">
              <label className="chip"><input type="radio" name="enrollment_flow" defaultChecked /> Auto-approve</label>
              <label className="chip"><input type="radio" name="enrollment_flow" /> Manual Review</label>
            </div>
          </div>
        </div>
      </Panel>
    </div>
  );
}

export function ReportsTab({ dashboard, learners }) {
  const [reportType, setReportType] = useState("course_completion");
  const { showToast } = useToast();

  const handleExportCSV = () => {
    try {
      let csvContent = "";
      if (reportType === "course_completion") {
        csvContent = "Course,Enrolled,Completed,Completion %,Avg PAL Score\n" +
          (dashboard?.courses || []).map(c => `"${c.name}",${c.enrolled_count},${Math.round((c.completion_rate / 100) * c.enrolled_count)},${c.completion_rate}%,${c.avg_pal_score || 0}`).join("\n");
      } else if (reportType === "user_performance") {
        csvContent = "Student,Courses Enrolled,Completed,PAL Score,Last Active,Status\n" +
          (learners || []).map(l => `"${l.full_name}",${l.total_courses},${l.courses_completed},${l.pal_score}%,${l.last_active || "N/A"},${l.is_active ? "Active" : "Inactive"}`).join("\n");
      } else if (reportType === "enrollment_summary") {
        csvContent = "Period,New Enrollments,Approved,Denied,Manual,Self\n" +
          `"This Month",${dashboard?.kpis?.pending_enrollment || 0},${dashboard?.kpis?.active_learners || 0},0,0,0`;
      }
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `telite_report_${reportType}_${new Date().toISOString().slice(0,10)}.csv`;
      link.click();
      URL.revokeObjectURL(url);
      showToast("CSV exported successfully!", "success");
    } catch (err) {
      showToast("Export failed: " + err.message, "error");
    }
  };

  const handleExportPDF = () => {
    try {
      const doc = new jsPDF();
      doc.setFont("helvetica", "bold");
      doc.setFontSize(16);
      doc.text(`Telite LMS Export - ${titleize(reportType.replace("_", " "))}`, 14, 15);
      doc.setFontSize(10);
      doc.setFont("helvetica", "normal");
      doc.text(`Date: ${new Date().toLocaleDateString()}`, 14, 22);

      let head = [];
      let body = [];

      if (reportType === "course_completion") {
        head = [["Course", "Enrolled", "Completed", "Completion %", "Avg PAL Score"]];
        body = (dashboard?.courses || []).map(c => [
          c.name, c.enrolled_count, Math.round((c.completion_rate / 100) * c.enrolled_count), `${c.completion_rate}%`, `${c.avg_pal_score || 0}`
        ]);
      } else if (reportType === "user_performance") {
        head = [["Student", "Courses Enrolled", "Completed", "PAL Score", "Last Active", "Status"]];
        body = (learners || []).map(l => [
          l.full_name, l.total_courses, l.courses_completed, `${l.pal_score}%`, l.last_active || "N/A", l.is_active ? "Active" : "Inactive"
        ]);
      } else if (reportType === "enrollment_summary") {
        head = [["Period", "New Enrollments", "Approved", "Denied", "Manual", "Self"]];
        body = [["This Month", dashboard?.kpis?.pending_enrollment || 0, dashboard?.kpis?.active_learners || 0, 0, 0, 0]];
      }

      autoTable(doc, {
        startY: 28,
        head,
        body,
        theme: 'striped',
        headStyles: { fillColor: [37, 99, 235] },
      });
      
      doc.save(`telite_report_${reportType}_${new Date().toISOString().slice(0,10)}.pdf`);
      showToast("PDF exported successfully!", "success");
    } catch (err) {
      showToast("PDF export failed: " + err.message, "error");
    }
  };

  return (
    <Panel
      title="Reports Center"
      subtitle="Generate and export analytics data."
    >
      <div className="reports-toolbar">
        <div className="reports-toolbar__filters">
          {["course_completion", "user_performance", "enrollment_summary"].map(rt => (
            <label className="chip" key={rt}>
              <input type="radio" name="report_type" checked={reportType === rt} onChange={() => setReportType(rt)} />
              {titleize(rt.replace("_", " "))}
            </label>
          ))}
        </div>
        <div className="reports-toolbar__actions">
          <Button tone="ghost" icon="download" onClick={handleExportCSV}>Export CSV</Button>
          <Button tone="ghost" icon="download" onClick={handleExportPDF}>Export PDF</Button>
        </div>
      </div>

      {reportType === "course_completion" && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Course</th>
                <th>Enrolled</th>
                <th>Completed</th>
                <th>Completion %</th>
                <th>Avg PAL Score</th>
              </tr>
            </thead>
            <tbody>
              {(dashboard?.courses || []).length > 0 ? (dashboard?.courses || []).map(course => (
                <tr key={course.id}>
                  <td><div className="row-title">{course.name}</div></td>
                  <td>{course.enrolled_count}</td>
                  <td>{Math.round((course.completion_rate / 100) * course.enrolled_count)}</td>
                  <td>
                    <div className="progress-cell">
                      <div className="progress-cell__track">
                        <div className="progress-track">
                          <div className="progress-fill" style={{ width: `${course.completion_rate}%`, background: "var(--success)" }} />
                        </div>
                      </div>
                      <span className="mono muted progress-cell__value">{course.completion_rate}%</span>
                    </div>
                  </td>
                  <td>{course.avg_pal_score || "N/A"}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="5" className="table-empty-cell">
                    <span className="muted">No course data available.</span>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {reportType === "user_performance" && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Student</th>
                <th>Courses Enrolled</th>
                <th>Completed</th>
                <th>PAL Score</th>
                <th>Last Active</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {(learners || []).length > 0 ? (learners || []).map(learner => (
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
                  <td>{learner.total_courses}</td>
                  <td>{learner.courses_completed}</td>
                  <td className="mono" style={{ color: getScoreColor(learner.pal_score) }}>{formatPercent(learner.pal_score)}</td>
                  <td>{learner.last_active || "N/A"}</td>
                  <td><Badge tone={learner.is_active ? "success" : "neutral"}>{learner.is_active ? "Active" : "Inactive"}</Badge></td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="6" className="table-empty-cell">
                    <span className="muted">No user data available.</span>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {reportType === "enrollment_summary" && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Period</th>
                <th>New Enrollments</th>
                <th>Approved</th>
                <th>Denied</th>
                <th>Manual</th>
                <th>Self</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><div className="row-title">This Month</div></td>
                <td>{dashboard?.kpis?.pending_enrollment || 0}</td>
                <td>{dashboard?.kpis?.active_learners || 0}</td>
                <td>0</td>
                <td>0</td>
                <td>0</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

export function PalTrackerTab({ dashboard, labels, palExpanded, setPalExpanded }) {
  const [trendView, setTrendView] = useState("weekly");
  const palCards = dashboard?.pal?.leaderboard ? [...dashboard.pal.leaderboard] : [];
  const topPerformers = [...palCards].sort((a, b) => b.pal_score - a.pal_score).slice(0, 5);
  const atRiskStudents = palCards.filter(s => s.pal_score < 60);
  const visiblePalCards = palExpanded ? palCards : palCards.slice(0, 4);

  return (
    <div className="dashboard-stack">
      <div className="grid-3">
        <div className="summary-chip">
          <div className="summary-chip__label">Avg completion</div>
          <div className="summary-chip__value">{dashboard?.pal?.summary?.avg_completion || 0}%</div>
        </div>
        <div className="summary-chip">
          <div className="summary-chip__label">Avg quiz score</div>
          <div className="summary-chip__value">{dashboard?.pal?.summary?.avg_quiz_score || 0}%</div>
        </div>
        <div className="summary-chip">
          <div className="summary-chip__label">Avg time</div>
          <div className="summary-chip__value">{dashboard?.pal?.summary?.avg_time_hours || 0}h</div>
        </div>
      </div>

      <div className="grid-2-wide">
        <Panel title="Top Performers Leaderboard" subtitle="Top 5 students by PAL score">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Student</th>
                  <th>Courses</th>
                  <th>PAL Score</th>
                  <th>Trend</th>
                </tr>
              </thead>
              <tbody>
                {topPerformers.map((learner, idx) => (
                  <tr key={learner.id}>
                    <td>
                      <div className="leaderboard-rank" style={{ color: getRankColor(idx + 1), fontWeight: 700 }}>
                        #{idx + 1}
                      </div>
                    </td>
                    <td>
                      <div className="leaderboard-row" style={{ padding: 0, borderBottom: 0 }}>
                        <Avatar initials={learner.avatar_initials || getInitials(learner.full_name)} gradient={learner.avatar_gradient} size={26} />
                        <div className="row-title">{learner.full_name}</div>
                      </div>
                    </td>
                    <td>{learner.courses_completed}/{learner.total_courses || 0}</td>
                    <td className="mono" style={{ color: getScoreColor(learner.pal_score), fontWeight: "bold" }}>
                      {formatPercent(learner.pal_score)}
                    </td>
                    <td>
                      <Badge tone={idx < 2 ? "success" : "neutral"}>{idx < 2 ? "↑" : "→"}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Risk Detection" subtitle="Students requiring attention (< 60% PAL)">
          <div className="activity-list">
            {atRiskStudents.length > 0 ? atRiskStudents.map((learner) => (
              <div className="activity-item" key={learner.id}>
                <Avatar initials={getInitials(learner.full_name)} gradient={["var(--error)", "var(--error)"]} size={32} />
                <div style={{ flex: 1 }}>
                  <div className="row-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {learner.full_name}
                    <Badge tone="danger">⚠️ At Risk</Badge>
                  </div>
                  <div className="row-subtitle">Score: <span style={{ color: "var(--danger)", fontWeight: "bold" }}>{formatPercent(learner.pal_score)}</span> · Last active recently</div>
                </div>
                <Button tone="ghost" size="sm" disabled title="Coming soon">Send reminder</Button>
              </div>
            )) : (
              <EmptyState title="No at-risk students" body="All students are currently maintaining a PAL score above 60%." />
            )}
          </div>
        </Panel>
      </div>

      <Panel title="Cohort Trend" subtitle="PAL score progression over time" action={
        <div className="toolbar">
          <label className="chip"><input type="radio" checked={trendView === "weekly"} onChange={() => setTrendView("weekly")} /> Weekly</label>
          <label className="chip"><input type="radio" checked={trendView === "monthly"} onChange={() => setTrendView("monthly")} /> Monthly</label>
        </div>
      }>
        <ChartCanvas
          type="line"
          height={220}
          labels={trendView === "weekly" ? ["W1", "W2", "W3", "W4", "W5"] : ["Jan", "Feb", "Mar", "Apr", "May"]}
          datasets={[{
            label: "Avg PAL Score",
            data: trendView === "weekly" ? [40, 55, 68, 75, 81] : [35, 50, 60, 72, 81],
            borderColor: "var(--primary)",
            backgroundColor: "transparent",
            tension: 0.4,
            pointBackgroundColor: "var(--primary)",
          }]}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              x: { border: { display: false }, grid: { display: false }, ticks: { color: "var(--text-secondary)" } },
              y: { min: 0, max: 100, border: { display: false }, grid: { color: "var(--border-subtle)" }, ticks: { color: "var(--text-muted)" } },
            },
          }}
        />
      </Panel>

      <Panel title={`PAL Score by ${labels.user}`} subtitle="Cohort performance distribution">
        <ChartCanvas
          type="bar"
          height={260}
          labels={(dashboard?.pal?.chart || []).map((entry) => entry.name)}
          datasets={[
            {
              label: "PAL score",
              data: (dashboard?.pal?.chart || []).map((entry) => entry.score),
              backgroundColor: (dashboard?.pal?.chart || []).map((entry) => getScoreColor(entry.score)),
              borderRadius: 8,
            },
          ]}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              x: { border: { display: false }, grid: { display: false }, ticks: { color: "var(--text-secondary)", font: { family: "Geist", size: 10 } } },
              y: { min: 0, max: 100, border: { display: false }, grid: { color: "var(--border-subtle)" }, ticks: { color: "var(--text-muted)", font: { family: "Geist Mono", size: 10 } } },
            },
          }}
        />
      </Panel>

      <div className="grid-2">
        {visiblePalCards.map((learner) => (
          <Panel key={learner.id} title={learner.full_name} subtitle={`${learner.courses_completed}/${learner.total_courses || 0} courses · ${learner.enrollment_type}`}>
            <div className="metric-row" style={{ justifyContent: "space-between", marginBottom: 14 }}>
              <div className="leaderboard-row" style={{ padding: 0, borderBottom: 0 }}>
                <Avatar initials={learner.avatar_initials || getInitials(learner.full_name)} gradient={learner.avatar_gradient} size={30} />
                <div>
                  <div className="row-title">{learner.full_name}</div>
                  <div className="row-subtitle">{learner.courses_completed}/${learner.total_courses || 0} courses · {learner.enrollment_type}</div>
                </div>
              </div>
              <div className="summary-chip__value" style={{ color: getScoreColor(learner.pal_score) }}>{formatPercent(learner.pal_score)}</div>
            </div>
            {[
              ["Completion", learner.pal_completion_pct],
              ["Quiz avg", learner.pal_quiz_avg],
              ["Time spent", learner.pal_time_spent_hours * 2],
            ].map(([label, value]) => (
              <div className="metric-row" key={label} style={{ marginBottom: 10 }}>
                <div className="row-subtitle" style={{ width: 80 }}>{label}</div>
                <div className="progress-track">
                  <div className="progress-fill" style={{ width: `${Math.min(100, value)}%`, background: getScoreColor(value) }} />
                </div>
                <div className="mono" style={{ width: 36, textAlign: "right" }}>{Math.round(value)}</div>
              </div>
            ))}
          </Panel>
        ))}
      </div>

      <div>
        <Button tone="ghost" onClick={() => setPalExpanded((value) => !value)}>
          {palExpanded ? "Hide extra PAL cards" : "View all cards"}
        </Button>
      </div>
    </div>
  );
}

export function TasksTab({ pendingTasks, completedTasks, toggleTask, setTaskModal, onReviewTask }) {
  const [view, setView] = useState("list");

  const assignedTasks = pendingTasks.filter(t => !t.status || t.status === "pending" || t.status === "assigned" || t.status === "revision_requested");
  const inProgressTasks = pendingTasks.filter(t => t.status === "in_progress");
  const submittedTasks = pendingTasks.filter(t => t.status === "submitted");

  const renderTaskList = (tasks, showReviewActions = false) => (
    <div className="task-status-card__body">
      {tasks.length > 0 ? tasks.map((task) => (
        <label className="task-row" key={task.id}>
          <input type="checkbox" checked={false} onChange={() => toggleTask(task)} />
          <div className="task-row__content">
            <div className="row-title">{task.title}</div>
            {showReviewActions ? (
              <div className="split-actions task-row__actions">
                <Button size="sm" tone="success" onClick={() => onReviewTask?.(task, "approve")}>Approve</Button>
                <Button size="sm" tone="ghost" onClick={() => onReviewTask?.(task, "request_revision")}>Request Revision</Button>
              </div>
            ) : null}
            <div className="row-subtitle">{task.assigned_label} · {task.status === "overdue" ? "Overdue!" : `due ${task.due_at || 'soon'}`}</div>
          </div>
        </label>
      )) : (
        <div className="task-status-card__empty">No tasks in this column.</div>
      )}
    </div>
  );

  const renderCompletedList = () => (
    <div className="task-status-card__body">
      {completedTasks.length > 0 ? completedTasks.map((task) => (
        <label className="task-row" key={task.id}>
          <input type="checkbox" checked onChange={() => toggleTask(task)} />
          <div className="task-row__content">
            <div className="row-title">{task.title}</div>
            <div className="row-subtitle">{task.assigned_label} · {task.due_at}</div>
          </div>
        </label>
      )) : (
        <div className="task-status-card__empty">No completed tasks yet.</div>
      )}
    </div>
  );

  const statusColumns = [
    { title: "Assigned", count: assignedTasks.length, content: renderTaskList(assignedTasks) },
    { title: "Submitted", count: submittedTasks.length, content: renderTaskList(submittedTasks, true) },
    { title: "In Progress", count: inProgressTasks.length, content: renderTaskList(inProgressTasks) },
    { title: "Completed", count: completedTasks.length, content: renderCompletedList() },
  ];

  return (
    <Panel
      title="Task Board"
      subtitle="Manage assignments across your category."
      action={
        <div className="split-actions">
          <div className="toolbar">
            <label className="chip"><input type="radio" checked={view === "list"} onChange={() => setView("list")} /> List</label>
            <label className="chip"><input type="radio" checked={view === "kanban"} onChange={() => setView("kanban")} /> Kanban</label>
          </div>
          <Button tone="primary" onClick={() => setTaskModal({ open: true, item: null })}>+ Assign task</Button>
        </div>
      }
    >
      {view === "list" ? (
        <div className="task-board-grid">
          {statusColumns.map((column) => (
            <div className="task-status-card" key={column.title}>
              <div className="task-status-card__header">
                <span className="task-status-card__title">{column.title}</span>
                <span className="task-status-card__count">{column.count}</span>
              </div>
              {column.content}
            </div>
          ))}
        </div>
      ) : (
        <TaskBoardKanban
          allTasks={[...pendingTasks, ...completedTasks]}
          onTaskStatusChange={(taskId, newStatus) => {
            const task = [...pendingTasks, ...completedTasks].find(t => t.id === taskId);
            if (task) toggleTask(task, newStatus);
          }}
        />
      )}
    </Panel>
  );
}

function ArchivedCoursesSettings({ slug }) {
  const { showToast } = useToast();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("newest");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [confirmCourse, setConfirmCourse] = useState(null);
  const [busyCourseId, setBusyCourseId] = useState(null);
  const pageSize = 8;

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total]);

  useEffect(() => {
    setPage(1);
  }, [search, sort]);

  useEffect(() => {
    let cancelled = false;

    async function loadArchivedCourses() {
      if (!slug) return;
      setLoading(true);
      setError("");
      try {
        const payload = await fetchArchivedCourses(slug, {
          search: search.trim() || undefined,
          sort,
          page,
          page_size: pageSize,
        });
        if (!cancelled) {
          setCourses(payload.courses || []);
          setTotal(Number(payload.total || 0));
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(getErrorMessage(requestError, "Unable to load archived courses."));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadArchivedCourses();
    return () => {
      cancelled = true;
    };
  }, [slug, search, sort, page]);

  async function refreshCurrentPage() {
    const payload = await fetchArchivedCourses(slug, {
      search: search.trim() || undefined,
      sort,
      page,
      page_size: pageSize,
    });
    setCourses(payload.courses || []);
    setTotal(Number(payload.total || 0));
  }

  async function handleRestore(course) {
    try {
      setBusyCourseId(course.id);
      await restoreArchivedCourse(slug, course.id);
      showToast("Course restored successfully.", "success");
      await refreshCurrentPage();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to restore course."), "error");
    } finally {
      setBusyCourseId(null);
    }
  }

  async function handlePermanentDelete() {
    if (!confirmCourse) return;
    try {
      setBusyCourseId(confirmCourse.id);
      await permanentlyDeleteArchivedCourse(slug, confirmCourse.id);
      setConfirmCourse(null);
      showToast("Course permanently deleted.", "success");
      await refreshCurrentPage();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to permanently delete course."), "error");
    } finally {
      setBusyCourseId(null);
    }
  }

  return (
    <div className="profile-settings__form">
      <div className="archived-courses-toolbar">
        <label className="field archived-courses-toolbar__search">
          <span className="field__label">Search archived courses</span>
          <input
            className="field__input"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by course name"
          />
        </label>
        <label className="field archived-courses-toolbar__sort">
          <span className="field__label">Sort</span>
          <select className="field__input" value={sort} onChange={(event) => setSort(event.target.value)}>
            <option value="newest">Newest Archived</option>
            <option value="oldest">Oldest Archived</option>
          </select>
        </label>
      </div>

      {loading ? (
        <div className="archived-courses-list" aria-label="Loading archived courses">
          {Array.from({ length: 3 }).map((_, index) => (
            <div className="archived-course-row archived-course-row--loading" key={index}>
              <div className="archived-course-row__thumb skeleton-line" />
              <div className="archived-course-row__main">
                <div className="skeleton-line skeleton-line--title" />
                <div className="skeleton-line skeleton-line--text" />
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="profile-settings__section">
          <div className="profile-settings__section-title">Unable to load archived courses</div>
          <div className="profile-settings__section-subtitle">{error}</div>
        </div>
      ) : courses.length === 0 ? (
        <EmptyState title="No archived courses found." body="Deleted courses will appear here after they are archived." icon="course" />
      ) : (
        <div className="archived-courses-list">
          {courses.map((course) => (
            <article className="archived-course-row" key={course.id}>
              <div className="archived-course-row__thumb">
                {course.cover_image_url ? (
                  <img src={course.cover_image_url} alt="" />
                ) : (
                  <Icon name="course" size={20} />
                )}
              </div>
              <div className="archived-course-row__main">
                <div className="archived-course-row__title">{course.name}</div>
                <div className="archived-course-row__meta">
                  <span>{titleize(course.category || course.category_slug || "Category")}</span>
                  <span>Deleted {formatDateTime(course.deleted_at)}</span>
                  <span>Deleted by {course.deleted_by || "--"}</span>
                </div>
              </div>
              <Badge tone="warning">Archived</Badge>
              <div className="archived-course-row__actions">
                <Button tone="ghost" disabled={busyCourseId === course.id} onClick={() => handleRestore(course)}>
                  Restore
                </Button>
                <Button tone="danger" disabled={busyCourseId === course.id} onClick={() => setConfirmCourse(course)}>
                  Delete Permanently
                </Button>
              </div>
            </article>
          ))}
        </div>
      )}

      {!loading && !error && total > pageSize ? (
        <div className="archived-courses-pagination">
          <Button tone="ghost" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>
            Previous
          </Button>
          <span className="profile-settings__helper">Page {page} of {totalPages}</span>
          <Button tone="ghost" disabled={page >= totalPages} onClick={() => setPage((value) => Math.min(totalPages, value + 1))}>
            Next
          </Button>
        </div>
      ) : null}

      <Modal
        open={Boolean(confirmCourse)}
        title="Delete Course Permanently?"
        onClose={() => setConfirmCourse(null)}
        footer={
          <>
            <Button tone="ghost" onClick={() => setConfirmCourse(null)}>Cancel</Button>
            <Button tone="danger" disabled={busyCourseId === confirmCourse?.id} onClick={handlePermanentDelete}>
              Delete Permanently
            </Button>
          </>
        }
      >
        <p className="profile-settings__modal-copy">
          This action cannot be undone.<br />
          The course and all associated data will be permanently deleted.
        </p>
      </Modal>
    </div>
  );
}

export function ProfileSettingsTab({ session, activeTab, setActiveTab, slug, onClose }) {
  const tabs = [
    { id: "account", label: "Account Settings", icon: "settings" },
    { id: "notifications", label: "Notifications", icon: "bell" },
    { id: "personalization", label: "Personalization", icon: "dashboard" },
    ...(slug ? [{ id: "archived_courses", label: "Archived Courses", icon: "course" }] : []),
  ];
  const activeSettingsTab = tabs.find((tab) => tab.id === activeTab) || tabs[0];
  const selectedTab = activeSettingsTab.id;

  return (
    <div className="profile-settings-modal" role="dialog" aria-modal="true" aria-labelledby="profile-settings-title">
      <div className="profile-settings-modal__backdrop" />
      <div className="profile-settings-modal__card">
        <div className="profile-settings-modal__header">
          <h2 id="profile-settings-title" className="profile-settings-modal__title">Settings</h2>
          <button type="button" className="profile-settings-modal__close" onClick={onClose} aria-label="Close settings">
            <Icon name="x" size={22} />
          </button>
        </div>

        <div className="profile-settings">
          <aside className="profile-settings__nav" aria-label="Profile settings">
            <div className="profile-settings__nav-items">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  className={`profile-settings__nav-item ${selectedTab === tab.id ? "is-active" : ""}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  <span className="profile-settings__nav-item-left">
                    <Icon name={tab.icon} size={20} />
                    <span>{tab.label}</span>
                  </span>
                </button>
              ))}
            </div>
          </aside>

          <section className="profile-settings__panel">
            <div className="profile-settings__header">
              <h3 className="profile-settings__title">{activeSettingsTab.label}</h3>
              <p className="profile-settings__subtitle">Manage your profile preferences and account settings.</p>
            </div>

            <div className="profile-settings__body">
          {selectedTab === "account" && (
            <AccountSettingsPanel />
          )}

          {selectedTab === "notifications" && (
            <div className="profile-settings__form">
              {[
                { title: "Enrollment Requests", desc: "Get notified when a user requests enrollment to a course." },
                { title: "Assignment Alerts", desc: "Get notified about new submission reviews and pending grade actions." },
                { title: "Task Deadlines", desc: "Receive reminders for upcoming or overdue tasks." },
                { title: "PAL Alerts", desc: "Weekly digests and immediate alerts for at-risk students." }
              ].map((item, idx) => (
                <div className="profile-settings__preference-row" key={idx}>
                  <div>
                    <div className="profile-settings__section-title">{item.title}</div>
                    <div className="profile-settings__section-subtitle">{item.desc}</div>
                  </div>
                  <label className="chip"><input type="checkbox" defaultChecked /> Enabled</label>
                </div>
              ))}
              <div className="profile-settings__actions">
                <Button tone="primary" icon="save">Save Changes</Button>
              </div>
            </div>
          )}

          {selectedTab === "personalization" && (
            <div className="profile-settings__form" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "400px" }}>
              <EmptyState 
                icon="dashboard" 
                title="Personalization" 
                body="Coming Soon - Personalization will be available in an upcoming release." 
              />
            </div>
          )}



          {selectedTab === "archived_courses" && (
            <ArchivedCoursesSettings slug={slug} />
          )}

            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
