import React, { useState } from "react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { Avatar, Badge, Button, EmptyState, StatCard, Panel, useToast } from "../common/ui";
import { TaskBoardKanban } from "./TaskBoard";
import { ChartCanvas } from "../common/charts";
import { formatDateTime, titleize, getScoreColor, getInitials, formatPercent } from "../../utils/formatters";

export function ActivityFeedTab({ events = [] }) {
  const [filter, setFilter] = useState("all");

  const MOCK_EVENTS = [
    { id: 1, type: "enrollment", status: "success", title: "Karan Rawat enrolled in 'Frontend Basics'", timestamp: new Date(Date.now() - 3600000) },
    { id: 2, type: "verification", status: "info", title: "Priya Subramanian's account approved", timestamp: new Date(Date.now() - 7200000) },
    { id: 3, type: "task", status: "warning", title: "Task 'Mock interview' assigned to Simran Kaur", timestamp: new Date(Date.now() - 14400000) },
    { id: 4, type: "enrollment", status: "error", title: "Varun Nair's enrollment denied", timestamp: new Date(Date.now() - 86400000) },
    { id: 5, type: "pal", status: "success", title: "Rahul Singh completed 'Frontend Basics quiz'", timestamp: new Date(Date.now() - 172800000) },
  ];

  const displayEvents = events.length ? events.map(e => ({
    id: e.id,
    type: e.icon === 'launch' || e.icon === 'check' ? 'task' : e.icon === 'plus' ? 'enrollment' : 'system',
    status: e.accent === 'emerald' || e.accent === 'teal' ? 'success' : e.accent === 'red' ? 'error' : e.accent === 'warning' ? 'warning' : 'info',
    title: e.message || e.title,
    timestamp: e.created_at ? new Date(e.created_at) : e.timestamp
  })) : MOCK_EVENTS;
  const filteredEvents = displayEvents.filter(e => filter === "all" || e.type === filter);

  return (
    <div className="panel">
      <div className="panel-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 className="panel-title">Activity Feed</h2>
          <p className="panel-subtitle">Real-time chronological event log across the category.</p>
        </div>
      </div>
      <div className="panel-body">
        <div className="toolbar" style={{ marginBottom: 24 }}>
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
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ 
                        width: 8, 
                        height: 8, 
                        borderRadius: "50%", 
                        backgroundColor: evt.status === "success" ? "var(--success)" : 
                                         evt.status === "error" ? "var(--danger)" : 
                                         evt.status === "warning" ? "var(--warning)" : "var(--primary)" 
                      }} />
                      <span>{evt.title}</span>
                    </div>
                  </td>
                  <td><Badge tone="neutral">{titleize(evt.type)}</Badge></td>
                </tr>
              ))}
              {filteredEvents.length === 0 && (
                <tr>
                  <td colSpan="3" style={{ textAlign: "center", padding: "32px 0" }}>
                    <div className="muted">No activity matching the filter.</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export function SettingsTab({ dashboard }) {
  const [moodleStatus, setMoodleStatus] = useState("connected");
  const { showToast } = useToast();

  return (
    <div className="grid-2">
      <div className="panel">
        <div className="panel-header">
          <h2 className="panel-title">Moodle Connection</h2>
          <p className="panel-subtitle">LMS backend integration status.</p>
        </div>
        <div className="panel-body">
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
            <div style={{ padding: "12px", background: "var(--surface-alt)", borderRadius: "8px", flex: 1 }}>
              <div className="row-subtitle">Instance URL</div>
              <div className="row-title mono">https://moodle.telite.io</div>
            </div>
            <Badge tone={moodleStatus === "connected" ? "brand" : "warn"}>
              {moodleStatus === "connected" ? "Connected ✓" : "Not Connected ✗"}
            </Badge>
          </div>
          <Button
            tone="ghost"
            className="btn--block"
            onClick={() => showToast("Re-sync request sent to Super Admin.", "success")}
          >
            Request re-sync from Super Admin
          </Button>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2 className="panel-title">Category Settings</h2>
          <p className="panel-subtitle">Manage category configuration.</p>
        </div>
        <div className="panel-body">
          <label className="field" style={{ marginBottom: 16 }}>
            <span className="field__label">Category Display Name</span>
            <input className="field__input" defaultValue={dashboard?.category?.name || "Category Name"} />
          </label>
          <label className="field" style={{ marginBottom: 16 }}>
            <span className="field__label">Category Description</span>
            <textarea className="field__input" rows={3} defaultValue={dashboard?.category?.description || ""} />
          </label>

          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 16, marginTop: 16 }}>
            <div className="row-title">Enrollment Approval</div>
            <div className="toolbar" style={{ marginTop: 8 }}>
              <label className="chip"><input type="radio" name="enrollment_flow" defaultChecked /> Auto-approve</label>
              <label className="chip"><input type="radio" name="enrollment_flow" /> Manual Review</label>
            </div>
          </div>
        </div>
        <div className="panel-footer" style={{ borderTop: "1px solid var(--border)", padding: 16, textAlign: "right" }}>
          <Button tone="primary">Save Changes</Button>
        </div>
      </div>
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
          `"This Month",${dashboard?.kpis?.pending_verifications || 0},${dashboard?.kpis?.active_learners || 0},0,0,0`;
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
        body = [["This Month", dashboard?.kpis?.pending_verifications || 0, dashboard?.kpis?.active_learners || 0, 0, 0, 0]];
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
    <div className="panel">
      <div className="panel-header">
        <h2 className="panel-title">Reports Center</h2>
        <p className="panel-subtitle">Generate and export analytics data.</p>
      </div>
      <div className="panel-body">
        <div className="toolbar" style={{ marginBottom: 24, paddingBottom: 24, borderBottom: "1px solid var(--border)" }}>
          {["course_completion", "user_performance", "enrollment_summary"].map(rt => (
            <label className="chip" key={rt}>
              <input type="radio" name="report_type" checked={reportType === rt} onChange={() => setReportType(rt)} />
              {titleize(rt.replace("_", " "))}
            </label>
          ))}
          <div style={{ flex: 1 }} />
          <Button tone="ghost" icon="download" onClick={handleExportCSV}>Export CSV</Button>
          <Button tone="ghost" icon="download" onClick={handleExportPDF}>Export PDF</Button>
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
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{ flex: 1, background: "var(--border)", height: 6, borderRadius: 3, overflow: "hidden" }}>
                          <div style={{ width: `${course.completion_rate}%`, background: "var(--success)", height: "100%" }} />
                        </div>
                        <span className="mono muted">{course.completion_rate}%</span>
                      </div>
                    </td>
                    <td>{course.avg_pal_score || "N/A"}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan="5" style={{ textAlign: "center", padding: "24px 0" }}>
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
                    <td colSpan="6" style={{ textAlign: "center", padding: "24px 0" }}>
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
                  <td>{dashboard?.kpis?.pending_verifications || 0}</td>
                  <td>{dashboard?.kpis?.active_learners || 0}</td>
                  <td>0</td>
                  <td>0</td>
                  <td>0</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
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
                      {idx === 0 ? "🥇 1" : idx === 1 ? "🥈 2" : idx === 2 ? "🥉 3" : `${idx + 1}`}
                    </td>
                    <td>
                      <div className="leaderboard-row" style={{ padding: 0, borderBottom: 0 }}>
                        <Avatar initials={learner.avatar_initials || getInitials(learner.full_name)} gradient={learner.avatar_gradient} size={26} />
                        <div className="row-title">{learner.full_name}</div>
                      </div>
                    </td>
                    <td>{learner.courses_completed}/6</td>
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
                <Avatar initials={getInitials(learner.full_name)} gradient={["#ef4444", "#991b1b"]} size={32} />
                <div style={{ flex: 1 }}>
                  <div className="row-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {learner.full_name}
                    <Badge tone="danger">⚠️ At Risk</Badge>
                  </div>
                  <div className="row-subtitle">Score: <span style={{ color: "var(--danger)", fontWeight: "bold" }}>{formatPercent(learner.pal_score)}</span> · Last active recently</div>
                </div>
                <Button tone="ghost" size="sm">Send reminder</Button>
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
              x: { border: { display: false }, grid: { display: false }, ticks: { color: "#475569" } },
              y: { min: 0, max: 100, border: { display: false }, grid: { color: "#F2F4F8" }, ticks: { color: "#94A3B8" } },
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
              x: { border: { display: false }, grid: { display: false }, ticks: { color: "#475569", font: { family: "Geist", size: 10 } } },
              y: { min: 0, max: 100, border: { display: false }, grid: { color: "#F2F4F8" }, ticks: { color: "#94A3B8", font: { family: "Geist Mono", size: 10 } } },
            },
          }}
        />
      </Panel>

      <div className="grid-2">
        {visiblePalCards.map((learner) => (
          <Panel key={learner.id} title={learner.full_name} subtitle={`${learner.courses_completed}/6 courses · ${learner.enrollment_type}`}>
            <div className="metric-row" style={{ justifyContent: "space-between", marginBottom: 14 }}>
              <div className="leaderboard-row" style={{ padding: 0, borderBottom: 0 }}>
                <Avatar initials={learner.avatar_initials || getInitials(learner.full_name)} gradient={learner.avatar_gradient} size={30} />
                <div>
                  <div className="row-title">{learner.full_name}</div>
                  <div className="row-subtitle">{learner.courses_completed}/6 courses · {learner.enrollment_type}</div>
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

export function TasksTab({ pendingTasks, completedTasks, toggleTask, setTaskModal }) {
  const [view, setView] = useState("list");

  // For Kanban, we simulate "In Progress"
  const todoTasks = pendingTasks.filter(t => !t.status || t.status === 'pending');
  const inProgressTasks = pendingTasks.filter(t => t.status === 'in_progress');
  const doneTasks = completedTasks;

  return (
    <div className="panel">
      <div className="panel-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 className="panel-title">Task Board</h2>
          <p className="panel-subtitle">Manage assignments across your category.</p>
        </div>
        <div className="split-actions">
          <div className="toolbar">
            <label className="chip"><input type="radio" checked={view === "list"} onChange={() => setView("list")} /> ☰ List</label>
            <label className="chip"><input type="radio" checked={view === "kanban"} onChange={() => setView("kanban")} /> ⊞ Kanban</label>
          </div>
          <Button tone="primary" onClick={() => setTaskModal({ open: true, item: null })}>+ Assign task</Button>
        </div>
      </div>
      <div className="panel-body">
        {view === "list" ? (
          <div className="grid-2">
            <div className="soft-card">
              <div className="row-title" style={{ marginBottom: 12 }}>Pending tasks</div>
              <div className="activity-list">
                {pendingTasks.map((task) => (
                  <label className="task-row" key={task.id}>
                    <input type="checkbox" checked={false} onChange={() => toggleTask(task)} />
                    <div style={{ flex: 1 }}>
                      <div className="row-title">{task.title}</div>
                      <div className="row-subtitle">{task.assigned_label} · {task.status === "overdue" ? "Overdue!" : `due ${task.due_at || 'soon'}`}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
            <div className="soft-card">
              <div className="row-title" style={{ marginBottom: 12 }}>Completed tasks</div>
              <div className="activity-list">
                {completedTasks.map((task) => (
                  <label className="task-row" key={task.id}>
                    <input type="checkbox" checked onChange={() => toggleTask(task)} />
                    <div style={{ flex: 1 }}>
                      <div className="row-title">{task.title}</div>
                      <div className="row-subtitle">{task.assigned_label} · {task.due_at}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
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
      </div>
    </div>
  );
}

export function ProfileSettingsTab({ session, activeTab, setActiveTab }) {
  const tabs = [
    { id: "general", label: "General", icon: "👤" },
    { id: "notifications", label: "Notifications", icon: "🔔" },
    { id: "personalization", label: "Personalization", icon: "🎨" },
    { id: "security", label: "Security", icon: "🔒" },
    { id: "account", label: "Account", icon: "⚙️" },
  ];

  return (
    <div className="grid-3" style={{ gridTemplateColumns: "240px 1fr" }}>
      <div className="panel">
        <div className="panel-body" style={{ padding: "16px 8px" }}>
          <div className="sidebar-nav__items">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                className={`nav-item ${activeTab === tab.id ? "is-active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
                style={{ padding: "10px 16px", borderRadius: 8, textAlign: "left" }}
              >
                <span className="nav-item__left">
                  <span>{tab.icon}</span>
                  <span style={{ marginLeft: 8 }}>{tab.label}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2 className="panel-title">{tabs.find(t => t.id === activeTab)?.label || "Settings"}</h2>
          <p className="panel-subtitle">Manage your profile preferences and account settings.</p>
        </div>
        
        <div className="panel-body">
          {activeTab === "general" && (
            <div className="dashboard-stack">
              <div style={{ display: "flex", gap: 24, alignItems: "center", marginBottom: 24 }}>
                <Avatar initials={getInitials(session?.user?.name || "User")} gradient={["#2563EB", "#059669"]} size={80} />
                <div>
                  <Button tone="ghost" style={{ marginBottom: 8 }}>Upload new photo</Button>
                  <div className="muted" style={{ fontSize: 12 }}>JPG, GIF or PNG. Max size of 800K</div>
                </div>
              </div>
              <div className="grid-2">
                <label className="field">
                  <span className="field__label">Full Name</span>
                  <input className="field__input" defaultValue={session?.user?.name || "Category Admin"} />
                </label>
                <label className="field">
                  <span className="field__label">Email Address</span>
                  <input className="field__input" defaultValue={session?.user?.email || "admin@telite.io"} disabled />
                </label>
              </div>
              <label className="field">
                <span className="field__label">Role</span>
                <input className="field__input" defaultValue="Category Admin" disabled />
              </label>
              <div className="panel-footer" style={{ marginTop: 24, padding: "16px 0 0", borderTop: "1px solid var(--border)", textAlign: "right" }}>
                <Button tone="primary">Save Changes</Button>
              </div>
            </div>
          )}

          {activeTab === "notifications" && (
            <div className="dashboard-stack">
              {[
                { title: "Enrollment Requests", desc: "Get notified when a user requests enrollment to a course." },
                { title: "Verification Alerts", desc: "Get notified about new account verification requests." },
                { title: "Task Deadlines", desc: "Receive reminders for upcoming or overdue tasks." },
                { title: "PAL Alerts", desc: "Weekly digests and immediate alerts for at-risk students." }
              ].map((item, idx) => (
                <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 0", borderBottom: "1px solid var(--border)" }}>
                  <div>
                    <div className="row-title">{item.title}</div>
                    <div className="row-subtitle">{item.desc}</div>
                  </div>
                  <label className="chip"><input type="checkbox" defaultChecked /> Enabled</label>
                </div>
              ))}
            </div>
          )}

          {activeTab === "personalization" && (
            <div className="dashboard-stack">
              <div className="row-title">Default Tab on Login</div>
              <div className="toolbar">
                <label className="chip"><input type="radio" name="default_tab" defaultChecked /> Overview</label>
                <label className="chip"><input type="radio" name="default_tab" /> Tasks</label>
                <label className="chip"><input type="radio" name="default_tab" /> Activity</label>
              </div>

              <div className="row-title" style={{ marginTop: 24 }}>Dashboard Density</div>
              <div className="toolbar">
                <label className="chip"><input type="radio" name="density" /> Compact</label>
                <label className="chip"><input type="radio" name="density" defaultChecked /> Comfortable</label>
              </div>
            </div>
          )}

          {activeTab === "security" && (
            <div className="dashboard-stack">
              <label className="field">
                <span className="field__label">Current Password</span>
                <input type="password" className="field__input" placeholder="••••••••" />
              </label>
              <div className="grid-2">
                <label className="field">
                  <span className="field__label">New Password</span>
                  <input type="password" className="field__input" />
                </label>
                <label className="field">
                  <span className="field__label">Confirm New Password</span>
                  <input type="password" className="field__input" />
                </label>
              </div>
              <div style={{ marginTop: 16 }}>
                <Button tone="primary">Update Password</Button>
              </div>
            </div>
          )}

          {activeTab === "account" && (
            <div className="dashboard-stack">
              <div className="soft-card" style={{ background: "var(--red-light)", border: "1px solid var(--red-mid)" }}>
                <div className="row-title" style={{ color: "var(--red)" }}>Danger Zone</div>
                <div className="row-subtitle" style={{ marginBottom: 16 }}>Permanently delete your account and all associated data.</div>
                <Button tone="danger">Delete Account</Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
