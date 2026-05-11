import React, { Component, useDeferredValue, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useLocation, useSearchParams } from "react-router-dom";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import {
  approveEnrollmentRequest,
  approveVerification,
  bulkUploadVerifications,
  createCourse,
  createTask,
  deleteCourse,
  deleteUser,
  fetchAdminDashboard,
  fetchVerifications,
  getErrorMessage,
  manualEnroll,
  rejectEnrollmentRequest,
  rejectVerification,
  updateCourse,
  updateTask,
} from "../../services/client";
import { ChartCanvas } from "../../components/common/charts";
import { DashboardShell, TabBar, ProfileDropdown } from "../../layouts/DashboardLayout";
import {
  Avatar,
  Badge,
  Button,
  EmptyState,
  ErrorState,
  IconButton,
  LoadingState,
  Modal,
  Panel,
  StatCard,
  useToast,
} from "../../components/common/ui";
import {
  formatMonthDate,
  formatPercent,
  formatShortDate,
  getCompletionColor,
  getInitials,
  getScoreColor,
  getStatusTone,
  titleize,
} from "../../utils/formatters";
import { useKpiPulse } from "../../hooks/useKpiPulse";
import { ActivityFeedTab, SettingsTab, ReportsTab, PalTrackerTab, TasksTab, ProfileSettingsTab } from "../../components/dashboard/CategoryAdminTabs";
import { useDashboardStore } from "../../store/dashboardStore";

const COURSE_INITIAL = {
  name: "",
  slug: "",
  description: "",
  tier: "Basic",
  status: "active",
  module_count: 4,
  lessons_count: 8,
  hours: 12,
  modules: "",
};

const LEARNER_INITIAL = {
  full_name: "",
  email: "",
  enrollment_type: "manual",
  course_ids: [],
  note: "",
};

const TASK_INITIAL = {
  title: "",
  description: "",
  assigned_to_user_id: "all",
  due_at: "",
  notes: "",
};

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "courses", label: "Course management" },
  { id: "learners", label: "Learners" },
  { id: "enrollment", label: "Enrollment" },
  { id: "verifications", label: "Account Verifications" },
  { id: "pal", label: "PAL tracker" },
  { id: "tasks", label: "Tasks" },
  { id: "reports", label: "Reports" },
];

function CategoryAdminPageContent({ session, onLogout }) {
  const navigate = useNavigate();
  const { slug = "ats" } = useParams();
  const { showToast } = useToast();
  const { 
    dashboard, 
    dashboardLoading: loading, 
    dashboardError: error, 
    verifications, 
    verifLoading, 
    fetchDashboardData, 
    fetchVerificationsData,
    updateTaskState
  } = useDashboardStore();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [exportOpen, setExportOpen] = useState(false);
  const [courseModal, setCourseModal] = useState({ open: false, item: null });
  const [learnerModal, setLearnerModal] = useState({ open: false, seed: null });
  const [detailLearner, setDetailLearner] = useState(null);
  const [taskModal, setTaskModal] = useState({ open: false, item: null });
  const [deleteCourseId, setDeleteCourseId] = useState(null);
  const [deleteLearnerId, setDeleteLearnerId] = useState(null);
  const [expandedCourseId, setExpandedCourseId] = useState(null);
  const [palExpanded, setPalExpanded] = useState(false);
  const [manualQuickInput, setManualQuickInput] = useState("");
  const [quickError, setQuickError] = useState("");
  const [learnerSearch, setLearnerSearch] = useState("");
  const [learnerFilter, setLearnerFilter] = useState("all");
  const [learnerPage, setLearnerPage] = useState(1);
  const [courseSearch, setCourseSearch] = useState("");
  const [manualForm, setManualForm] = useState(LEARNER_INITIAL);
  const [manualErrors, setManualErrors] = useState({});
  const [manualSuccess, setManualSuccess] = useState("");
  const [bulkFile, setBulkFile] = useState(null);
  const [bulkResult, setBulkResult] = useState(null);
  const [bulkLoading, setBulkLoading] = useState(false);

  const deferredLearnerSearch = useDeferredValue(learnerSearch);
  const kpiPulse = useKpiPulse(dashboard?.kpis || {});
  const orgType = dashboard?.category?.org_type || 'college';
  const labels = {
    user: orgType === 'company' ? 'Employee' : 'Student',
    id: orgType === 'company' ? 'Employee ID' : 'Enrollment No',
    program: orgType === 'company' ? 'Department' : 'Program',
    branch: orgType === 'company' ? 'Designation' : 'Branch',
    users: orgType === 'company' ? 'Employees' : 'Students',
  };

  const learners = dashboard?.learners?.rows || [];
  const totalLearners = dashboard?.learners?.total || 0;
  const filteredLearners = useMemo(() => {
    return learners.filter((learner) => {
      if (learnerFilter !== "all" && learner.enrollment_type !== learnerFilter) {
        return false;
      }
      if (!deferredLearnerSearch) {
        return true;
      }
      const haystack = `${learner.full_name} ${learner.email}`.toLowerCase();
      return haystack.includes(deferredLearnerSearch.toLowerCase());
    });
  }, [deferredLearnerSearch, learnerFilter, learners]);

  const paginatedLearners = filteredLearners.slice((learnerPage - 1) * 10, learnerPage * 10);
  const pageCount = Math.max(1, Math.ceil(filteredLearners.length / 10));

  useEffect(() => {
    setLearnerPage(1);
  }, [deferredLearnerSearch, learnerFilter]);

  useEffect(() => {
    fetchDashboardData(slug);
  }, [slug]);

  // Derived active tab from URL (needed before early returns for the useEffect below)
  const derivedActiveTab = searchParams.get("tab") || "overview";
  const derivedSegment = location.pathname.replace(/\/$/, "").split("/").pop();
  const resolvedTab = derivedSegment === "activity" ? "activity" : derivedSegment === "settings" ? "settings" : derivedSegment === "profile" ? "profile" : derivedActiveTab;

  // Auto-load verifications when tab switches
  useEffect(() => {
    if (resolvedTab === "verifications") {
      loadVerifications();
    }
  }, [resolvedTab]);



  async function loadVerifications() {
    await fetchVerificationsData(slug);
  }

  async function handleVerification(id, action, reason = "") {
    try {
      if (action === "approve") {
        await approveVerification(id);
        showToast("Account approved", "success");
      } else {
        await rejectVerification(id, reason);
        showToast("Account rejected", "warning");
      }
      await loadVerifications();
    } catch (err) {
      showToast(getErrorMessage(err, `Failed to ${action} account`), "error");
    }
  }

  async function handleBulkUpload(e) {
    e.preventDefault();
    if (!bulkFile) return;

    setBulkLoading(true);
    setBulkResult(null);
    try {
      const result = await bulkUploadVerifications(bulkFile);
      setBulkResult(result);
      showToast("Bulk verification completed", "success");
      await loadVerifications();
    } catch (err) {
      showToast(getErrorMessage(err, "Bulk upload failed"), "error");
    } finally {
      setBulkLoading(false);
    }
  }

  async function load() {
    await fetchDashboardData(slug);
  }

  async function handleApprove(requestId) {
    try {
      await approveEnrollmentRequest(requestId);
      showToast("Enrollment approved.", "success");
      await load();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to approve enrollment."), "error");
    }
  }

  async function handleReject(requestId) {
    try {
      await rejectEnrollmentRequest(requestId, "Rejected by category admin");
      showToast("Enrollment denied.", "warning");
      await load();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to deny enrollment."), "error");
    }
  }

  async function handleDeleteCourse(courseId) {
    try {
      await deleteCourse(slug, courseId);
      setDeleteCourseId(null);
      showToast("Course archived.", "warning");
      await load();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to archive course."), "error");
    }
  }

  async function handleDeleteLearner(userId) {
    try {
      await deleteUser(userId);
      setDeleteLearnerId(null);
      showToast("Learner removed.", "warning");
      await load();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to remove learner."), "error");
    }
  }

  async function toggleTask(task, explicitStatus) {
    const nextStatus = explicitStatus || (task.status === "completed" ? "pending" : "completed");
    updateTaskState(task.id, nextStatus); // Optimistic update
    try {
      await updateTask(task.id, {
        title: task.title,
        description: task.description,
        assigned_label: task.assigned_label,
        assigned_to_user_id: task.assigned_to_user_id,
        assignment_scope: task.assignment_scope,
        category_slug: task.category_slug,
        due_at: task.due_at,
        status: nextStatus,
        notes: task.notes,
        is_cross_category: Boolean(task.is_cross_category),
      });
      showToast("Task status updated.", "success");
      // await load(); // Defer to background or omit since we have optimistic updates. 
    } catch (requestError) {
      updateTaskState(task.id, task.status); // Revert on failure
      showToast(getErrorMessage(requestError, "Unable to update task."), "error");
    }
  }

  async function handleQuickEnroll() {
    if (!manualQuickInput.trim()) {
      setQuickError("Enter a name or email.");
      return;
    }

    const value = manualQuickInput.trim();
    const seed = value.includes("@")
      ? {
          full_name: titleize(value.split("@")[0].replace(/[._-]/g, " ")),
          email: value,
        }
      : {
          full_name: value,
          email: `${value.toLowerCase().replace(/[^a-z0-9]+/g, ".").replace(/(^\.|\.$)/g, "")}@telite.io`,
        };

    setLearnerModal({ open: true, seed });
    setManualQuickInput("");
    setQuickError("");
  }

  async function submitManualEnrollment(payload) {
    try {
      await manualEnroll({
        ...payload,
        category_slug: slug,
      });
      showToast("Learner enrolled successfully.", "success");
      setManualSuccess("Learner enrolled successfully!");
      setManualErrors({});
      setManualForm(LEARNER_INITIAL);
      setLearnerModal({ open: false, seed: null });
      await load();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to enroll learner."), "error");
    }
  }

  if (loading) {
    return <LoadingState title="Loading Admin dashboard..." body="Pulling course, learner, enrollment, PAL, and task data." />;
  }

  if (error || !dashboard) {
    return <ErrorState body={error || "The admin dashboard did not return data."} action={<Button tone="primary" onClick={load}>Retry</Button>} />;
  }

  const navGroups = [
    {
      label: "Overview",
      items: [
        { id: "dashboard", label: "Dashboard", icon: "dashboard" },
        { id: "activity", label: "Activity feed", icon: "reports" },
      ],
    },
    {
      label: "Management",
      items: [
        { id: "courses", label: "Courses", icon: "course", badge: String(dashboard.kpis.total_courses), badgeTone: "brand" },
        { id: "learners", label: "Learners", icon: "users", badge: String(dashboard.kpis.active_learners), badgeTone: "brand" },
        { id: "enrollment", label: "Enrollment", icon: "enrollments", badge: String(dashboard.kpis.pending_enrollment), badgeTone: "warn" },
        { id: "verifications", label: "Verifications", icon: "shield", badge: String(dashboard.kpis.pending_verifications || 0), badgeTone: "warn" },
        { id: "tasks", label: "Tasks", icon: "task", badge: String(dashboard.tasks.length), badgeTone: "neutral" },
      ],
    },
    {
      label: "Analytics",
      items: [
        { id: "pal", label: "PAL tracking", icon: "leaderboard" },
        { id: "reports", label: "Reports", icon: "analytics" },
      ],
    },
    {
      label: "Settings",
      items: [{ id: "settings", label: "Settings", icon: "settings" }],
    },
  ];

  const currentCourse = (dashboard?.courses || []).find((course) => course.id === detailLearner?.current_course_id);
  const pendingTasks = (dashboard?.tasks || []).filter((task) => task.status !== "completed");
  const completedTasks = (dashboard?.tasks || []).filter((task) => task.status === "completed");
  const palCards = dashboard?.pal?.leaderboard ? [...dashboard.pal.leaderboard] : [];
  const visiblePalCards = palExpanded ? palCards : palCards.slice(0, 4);

  // Router-based state determination
  const currentPath = location.pathname.replace(/\/$/, "");
  const pathParts = currentPath.split("/");
  const currentSegment = pathParts[pathParts.length - 1];

  let activeNav = "dashboard";
  let activeTab = searchParams.get("tab") || "overview";

  if (currentSegment === "activity") {
    activeNav = "activity";
    activeTab = "activity";
  } else if (currentSegment === "settings") {
    activeNav = "settings";
    activeTab = "settings";
  } else if (currentSegment === "profile") {
    activeNav = "settings";
    activeTab = searchParams.get("tab") || "profile";
  } else {
    const mapped = {
      overview: "dashboard",
      courses: "courses",
      learners: "learners",
      enrollment: "enrollment",
      pal: "pal",
      tasks: "tasks",
      reports: "reports",
      verifications: "verifications",
    };
    activeNav = mapped[activeTab] || "dashboard";
  }


  const handleTabChange = (tabId) => {
    if (tabId === "overview") {
      navigate(`/categories/${slug}/admin`);
    } else {
      navigate(`/categories/${slug}/admin?tab=${tabId}`);
    }
  };

  return (
    <>
      <DashboardShell
        theme={dashboard.category?.slug || slug}
        brandMark={{ label: (dashboard.category?.name || "LMS").substring(0, 3).toUpperCase(), background: dashboard.category?.accent_color || "#2563EB" }}
        brandTitle="Telite LMS"
        brandSubtitle={`${dashboard.category?.name || slug} · admin panel`}
        navGroups={navGroups}
        activeNav={activeNav}
        onNavClick={(item) => {
          if (item.id === "activity") {
            navigate(`/categories/${slug}/admin/activity`);
            return;
          }
          if (item.id === "reports") {
            navigate(`/categories/${slug}/admin?tab=reports`);
            return;
          }
          if (item.id === "settings") {
            navigate(`/categories/${slug}/admin/settings`);
            return;
          }
          const mapped = {
            dashboard: "overview",
            courses: "courses",
            learners: "learners",
            enrollment: "enrollment",
            pal: "pal",
            tasks: "tasks",
            verifications: "verifications",
          };
          const targetTab = mapped[item.id] || "overview";
          if (targetTab === "overview") {
             navigate(`/categories/${slug}/admin`);
          } else {
             navigate(`/categories/${slug}/admin?tab=${targetTab}`);
          }
        }}
        profile={{
          initials: getInitials(session?.user?.name || "Admin User"),
          gradient: ["#2563EB", "#7C3AED"],
          name: session?.user?.name || "Admin User",
          roleLabel: `${dashboard.category?.slug || slug}-admin`,
        }}
        title={`${dashboard.category?.name || "Category"} Admin Dashboard`}
        subtitle={`${dashboard.category?.name || "Category"} Learning Category · Telite Systems`}
        topbarActions={
          <>
            <div className="menu-wrap">
              <Button tone="ghost" icon="download" onClick={() => setExportOpen((value) => !value)}>
                Export
              </Button>
              {exportOpen ? (
                <div className="menu-popover">
                  <button type="button" onClick={() => {
                    setExportOpen(false);
                    try {
                      let csvContent = "";
                      if (activeTab === "overview" || activeTab === "courses") {
                        csvContent = "Course,Tier,Enrolled,Completion,Status\n" +
                          (dashboard?.courses || []).map(c => `"${c.name}",${c.tier},${c.enrolled_count},${c.completion_pct}%,${c.status}`).join("\n");
                      } else if (activeTab === "learners") {
                        csvContent = "Name,Email,Courses,PAL Score,Enrollment Type\n" +
                          (learners || []).map(l => `"${l.full_name}","${l.email}",${l.courses_completed}/${l.total_courses},${l.pal_score}%,${l.enrollment_type}`).join("\n");
                      } else if (activeTab === "enrollment") {
                        csvContent = "Name,Email,Request Type,Requested At,Domain Verified\n" +
                          (dashboard?.enrollment_requests || []).map(r => `"${r.full_name}","${r.email || ""}",${r.request_type},${r.requested_at},${r.domain_verified}`).join("\n");
                      } else if (activeTab === "pal") {
                        csvContent = "Name,Completion %,Quiz Avg,Time (h),PAL Score\n" +
                          (palCards || []).map(l => `"${l.full_name}",${l.pal_completion_pct},${Math.round(l.pal_quiz_avg)},${Math.round(l.pal_time_spent_hours)},${l.pal_score}`).join("\n");
                      } else {
                        csvContent = "Category Summary Export\nTab," + activeTab + "\nExported," + new Date().toISOString();
                      }
                      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
                      const url = URL.createObjectURL(blob);
                      const link = document.createElement("a");
                      link.href = url;
                      link.download = `telite_${activeTab}_export_${new Date().toISOString().slice(0,10)}.csv`;
                      link.click();
                      URL.revokeObjectURL(url);
                      showToast("CSV exported successfully!", "success");
                    } catch (err) {
                      showToast("Export failed: " + err.message, "error");
                    }
                  }}>
                    📥 Export as CSV
                  </button>
                  <button type="button" onClick={() => {
                    setExportOpen(false);
                    try {
                      const doc = new jsPDF();
                      doc.text(`Telite LMS Export - ${titleize(activeTab)}`, 14, 15);
                      doc.setFontSize(10);
                      doc.text(`Date: ${new Date().toLocaleDateString()}`, 14, 22);

                      let head = [];
                      let body = [];

                      if (activeTab === "overview" || activeTab === "courses") {
                        head = [["Course", "Tier", "Enrolled", "Completion", "Status"]];
                        body = (dashboard?.courses || []).map(c => [
                          c.name, c.tier, c.enrolled_count, `${c.completion_pct}%`, c.status
                        ]);
                      } else if (activeTab === "learners") {
                        head = [["Name", "Email", "Courses", "PAL Score", "Enrollment Type"]];
                        body = (learners || []).map(l => [
                          l.full_name, l.email, `${l.courses_completed}/${l.total_courses}`, `${l.pal_score}%`, l.enrollment_type
                        ]);
                      } else if (activeTab === "enrollment") {
                        head = [["Name", "Email", "Type", "Requested", "Domain Verified"]];
                        body = (dashboard?.enrollment_requests || []).map(r => [
                          r.full_name, r.email || "", r.request_type, r.requested_at, r.domain_verified ? "Yes" : "No"
                        ]);
                      } else if (activeTab === "pal") {
                        head = [["Name", "Completion %", "Quiz Avg", "Time (h)", "PAL Score"]];
                        body = (palCards || []).map(l => [
                          l.full_name, `${l.pal_completion_pct}%`, `${Math.round(l.pal_quiz_avg)}%`, `${Math.round(l.pal_time_spent_hours)}h`, l.pal_score
                        ]);
                      } else {
                        head = [["Tab", "Exported At"]];
                        body = [[activeTab, new Date().toISOString()]];
                      }

                      autoTable(doc, {
                        startY: 28,
                        head,
                        body,
                        theme: 'striped',
                        headStyles: { fillColor: [37, 99, 235] },
                      });
                      
                      doc.save(`telite_${activeTab}_export_${new Date().toISOString().slice(0,10)}.pdf`);
                      showToast("PDF exported successfully!", "success");
                    } catch (err) {
                      showToast("PDF export failed: " + err.message, "error");
                    }
                  }}>
                    📄 Export as PDF
                  </button>
                </div>
              ) : null}
            </div>
            <Button tone="primary" icon="plus" onClick={() => setLearnerModal({ open: true, seed: null })}>
              Add learner
            </Button>
            <ProfileDropdown profile={{
              initials: getInitials(session?.user?.name || "Category Admin"),
              gradient: ["#2563EB", "#059669"],
              name: session?.user?.name || "Category Admin",
              roleLabel: "category-admin",
            }} onLogout={onLogout} onNavigate={(path) => {
              if (path === "profile" || path === "settings") {
                navigate(`/categories/${slug}/admin/profile?tab=${path}`);
              }
            }} />
          </>
        }
        tabBar={activeNav !== "activity" && activeNav !== "settings" ? <TabBar tabs={tabs} activeTab={activeTab} onChange={handleTabChange} /> : null}
      >
        <div className="dashboard-stack">
          {activeTab === "overview" ? (
            <>
              <div className="grid-4">
                <StatCard accent="#2563EB" label="Total Courses" value={dashboard?.kpis?.total_courses || 0} meta="↑ 2 this quarter" pulse={kpiPulse?.total_courses || 0} />
                <StatCard
                  label={`Active ${labels.users}`}
                  value={dashboard?.kpis?.active_learners || 0}
                  delta={kpiPulse?.active_learners || 0}
                  icon="users"
                />
                <StatCard
                  label="Pending Verifications"
                  value={dashboard?.kpis?.pending_verifications || 0}
                  delta={kpiPulse?.pending_verifications || 0}
                  icon="shield"
                  tone="warn"
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
                  title="Courses"
                  subtitle="6 total"
                  action={<button className="panel-link" type="button" onClick={() => setCourseModal({ open: true, item: null })}>+ New course</button>}
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
                        {(dashboard?.courses || []).map((course) => (
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
                              <Badge tone={course.status === "active" ? "success" : "warn"}>{titleize(course.status)}</Badge>
                            </td>
                            <td>
                              <div className="split-actions">
                                <IconButton label="Edit course" icon="pencil" onClick={() => setCourseModal({ open: true, item: course })} />
                                <IconButton label="Delete course" icon="trash" onClick={() => setDeleteCourseId((value) => (value === course.id ? null : course.id))} />
                              </div>
                              {deleteCourseId === course.id ? (
                                <div className="inline-confirm">
                                  <span>Archive this course?</span>
                                  <div className="split-actions">
                                    <Button tone="danger" onClick={() => handleDeleteCourse(course.id)}>Confirm delete</Button>
                                    <Button tone="ghost" onClick={() => setDeleteCourseId(null)}>Cancel</Button>
                                  </div>
                                </div>
                              ) : null}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Panel>

                <Panel title="Pending enrollment" subtitle="Needs review">
                  <div className="activity-list">
                    {(dashboard?.pending_enrollment || []).map((request) => (
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
                          <Button tone="success" onClick={() => handleApprove(request.id)}>Approve</Button>
                          <Button tone="danger" onClick={() => handleReject(request.id)}>Deny</Button>
                        </div>
                      </div>
                    ))}
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
          ) : null}

          {activeTab === "courses" ? (
            <Panel
              title="Course management"
              subtitle={`All ${dashboard.category?.name || "category"} courses with structure preview`}
              action={
                <div className="split-actions">
                  <input
                    className="field__input"
                    placeholder="Search courses..."
                    value={courseSearch}
                    onChange={(event) => setCourseSearch(event.target.value)}
                  />
                  <Button tone="primary" onClick={() => setCourseModal({ open: true, item: null })}>+ New course</Button>
                </div>
              }
            >
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Course</th>
                      <th>Tier</th>
                      <th>Modules</th>
                      <th>Enrolled</th>
                      <th>Completion</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(dashboard?.courses || [])
                      .filter((course) => course.name.toLowerCase().includes(courseSearch.toLowerCase()))
                      .map((course) => (
                        <FragmentCourseRow
                          key={course.id}
                          course={course}
                          expanded={expandedCourseId === course.id}
                          onToggle={() => setExpandedCourseId((value) => (value === course.id ? null : course.id))}
                          onEdit={() => setCourseModal({ open: true, item: course })}
                          onDelete={() => setDeleteCourseId((value) => (value === course.id ? null : course.id))}
                          deleteOpen={deleteCourseId === course.id}
                          onConfirmDelete={() => handleDeleteCourse(course.id)}
                          onCancelDelete={() => setDeleteCourseId(null)}
                        />
                      ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          ) : null}

          {activeTab === "learners" ? (
            <div className="tab-stack">
              <Panel
                title={`Manage ${labels.users}`}
                subtitle={`Overview of ${labels.users.toLowerCase()} enrolled in ${dashboard.category?.name}`}
                action={
                  <div className="toolbar">
                    <input
                      className="field__input"
                      placeholder={`Search by name or email...`}
                      value={learnerSearch}
                      onChange={(event) => setLearnerSearch(event.target.value)}
                    />
                    <select className="field__select" value={learnerFilter} onChange={(event) => setLearnerFilter(event.target.value)}>
                      <option value="all">All</option>
                      <option value="manual">Manual</option>
                      <option value="self">Self-enrolled</option>
                    </select>
                    <Button tone="primary" onClick={() => setLearnerModal({ open: true, seed: null })}>+ Add {labels.user}</Button>
                  </div>
                }
              >
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>{labels.user}</th>
                      <th>Enrolled date</th>
                      <th>Courses</th>
                      <th>PAL Score</th>
                      <th>Enrollment type</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedLearners.map((learner) => (
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
                        <td className="mono">{formatShortDate(learner.created_at)}</td>
                        <td className="mono">{learner.courses_completed}/{learner.total_courses}</td>
                        <td className="mono" style={{ color: getScoreColor(learner.pal_score) }}>{formatPercent(learner.pal_score)}</td>
                        <td><Badge tone={learner.enrollment_type === "self" ? "accent" : "brand"}>{learner.enrollment_type}</Badge></td>
                        <td><Badge tone={learner.is_active ? "success" : "neutral"}>{learner.is_active ? "Active" : "Inactive"}</Badge></td>
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
              <div className="pagination" style={{ marginTop: 16 }}>
                <Button tone="ghost" disabled={learnerPage === 1} onClick={() => setLearnerPage(1)}>Page 1</Button>
                <Button tone="ghost" disabled={learnerPage === pageCount} onClick={() => setLearnerPage((prev) => Math.min(prev + 1, pageCount))}>Next</Button>
              </div>
            </Panel>
            </div>
          ) : null}

          {activeTab === "enrollment" ? (
            <div className="dashboard-stack">
              <Panel title="Pending requests" subtitle="All pending self-enrollment requests">
                <div className="activity-list">
                  {(dashboard?.pending_enrollment || []).map((request) => (
                    <div className="activity-item" key={request.id}>
                      <Avatar initials={getInitials(request.full_name)} gradient={request.domain_verified ? ["#7C3AED", "#2563EB"] : ["#D97706", "#92400E"]} size={32} />
                      <div style={{ flex: 1 }}>
                        <div className="row-title">{request.full_name}</div>
                        <div className="row-subtitle">{request.request_type} · {request.email}</div>
                      </div>
                      <div className="split-actions">
                        <Button tone="success" onClick={() => handleApprove(request.id)}>Approve</Button>
                        <Button tone="danger" onClick={() => handleReject(request.id)}>Deny</Button>
                      </div>
                    </div>
                  ))}
                </div>
              </Panel>

              <Panel title="Manual Enrollment form" subtitle="Create learner access and enrol them into courses">
                {manualSuccess ? <div className="form-alert" style={{ background: "var(--emerald-light)", border: "1px solid var(--emerald-mid)", color: "var(--emerald)" }}>{manualSuccess}</div> : null}
                <form
                  className="form-stack"
                  onSubmit={async (event) => {
                    event.preventDefault();
                    const errors = {};
                    if (!manualForm.full_name.trim()) errors.full_name = "Name is required.";
                    if (!manualForm.email.trim()) errors.email = "Email is required.";
                    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(manualForm.email)) errors.email = "Enter a valid email address.";
                    if (!manualForm.course_ids.length) errors.course_ids = "Select at least one course.";
                    setManualErrors(errors);
                    if (Object.keys(errors).length) return;
                    await submitManualEnrollment(manualForm);
                  }}
                >
                  <div className="field-grid">
                    <label className="field">
                      <span className="field__label">{labels.user} name</span>
                      <input className={`field__input ${manualErrors.full_name ? "is-invalid" : ""}`} value={manualForm.full_name} onChange={(event) => setManualForm((current) => ({ ...current, full_name: event.target.value }))} />
                      {manualErrors.full_name ? <span className="field__error">{manualErrors.full_name}</span> : null}
                    </label>
                    <label className="field">
                      <span className="field__label">Email address</span>
                      <input className={`field__input ${manualErrors.email ? "is-invalid" : ""}`} value={manualForm.email} onChange={(event) => setManualForm((current) => ({ ...current, email: event.target.value }))} />
                      {manualForm.email && !manualForm.email.endsWith("@telite.io") ? <span className="field__help">Warning: non-company domain, approval may be required.</span> : null}
                      {manualErrors.email ? <span className="field__error">{manualErrors.email}</span> : null}
                    </label>
                  </div>
                  <div className="field">
                    <span className="field__label">Enrollment type</span>
                    <div className="radio-row">
                      {["manual", "self"].map((option) => (
                        <label className="radio-pill" key={option}>
                          <input type="radio" checked={manualForm.enrollment_type === option} onChange={() => setManualForm((current) => ({ ...current, enrollment_type: option }))} />
                          {titleize(option === "self" ? "Self-enrollment" : option)}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="field">
                    <span className="field__label">Courses to enroll in</span>
                    <div className="checkbox-grid">
                      {(dashboard?.courses || []).map((course) => (
                        <label className="radio-pill" key={course.id}>
                          <input
                            type="checkbox"
                            checked={manualForm.course_ids.includes(course.id)}
                            onChange={() =>
                              setManualForm((current) => ({
                                ...current,
                                course_ids: current.course_ids.includes(course.id)
                                  ? current.course_ids.filter((value) => value !== course.id)
                                  : [...current.course_ids, course.id],
                              }))
                            }
                          />
                          {course.name}
                        </label>
                      ))}
                    </div>
                    {manualErrors.course_ids ? <span className="field__error">{manualErrors.course_ids}</span> : null}
                  </div>
                  <label className="field">
                    <span className="field__label">Note / reason</span>
                    <textarea className="field__textarea" value={manualForm.note} onChange={(event) => setManualForm((current) => ({ ...current, note: event.target.value }))} />
                  </label>
                  <Button tone="primary" type="submit" className="btn--block">Enroll {labels.user}</Button>
                </form>
              </Panel>
            </div>
          ) : null}

          {activeTab === "verifications" ? (
            <div className="dashboard-stack">
              <Panel
                title="Bulk Account Verification"
                subtitle="Upload Excel/CSV to approve multiple signups at once"
              >
                <div className="bulk-verify-zone">
                  <div className="bulk-verify-info">
                    <div className="row-title">How it works</div>
                    <p className="row-subtitle">Upload a file with a column named <strong>email</strong> or <strong>id_number</strong>. The system will match these against pending signups for your organization and approve them automatically.</p>
                  </div>
                  
                  <form onSubmit={handleBulkUpload} className="bulk-verify-form">
                    <div className="file-drop-zone">
                      <input 
                        type="file" 
                        id="bulk-file-input"
                        accept=".csv,.xlsx,.xls" 
                        onChange={(e) => setBulkFile(e.target.files[0])}
                      />
                      <label htmlFor="bulk-file-input" className="file-drop-label">
                        <i className="icon icon-upload" style={{ fontSize: 24, marginBottom: 8, display: 'block' }}></i>
                        {bulkFile ? bulkFile.name : "Click or drag Excel/CSV file here to upload"}
                      </label>
                    </div>
                    <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end' }}>
                      <Button 
                        tone="primary" 
                        type="submit" 
                        disabled={!bulkFile || bulkLoading}
                        loading={bulkLoading}
                        icon="shield"
                      >
                        Process Bulk Verification
                      </Button>
                    </div>
                  </form>

                  {bulkResult && (
                    <div className="bulk-result-dashboard" style={{ marginTop: 24 }}>
                      <div className="grid-3">
                        <div className="stat-card">
                          <div className="stat-card__label">Total Processed</div>
                          <div className="stat-card__value">{bulkResult.total_processed}</div>
                        </div>
                        <div className="stat-card" style={{ borderLeft: '4px solid var(--emerald)' }}>
                          <div className="stat-card__label">Approved</div>
                          <div className="stat-card__value" style={{ color: 'var(--emerald)' }}>{bulkResult.approved_count}</div>
                        </div>
                        <div className="stat-card">
                          <div className="stat-card__label">Ignored/Failed</div>
                          <div className="stat-card__value">{bulkResult.ignored_count}</div>
                        </div>
                      </div>
                      {bulkResult.errors?.length > 0 && (
                        <div className="error-log" style={{ marginTop: 16 }}>
                          <div className="row-title">Issues encountered:</div>
                          <ul className="row-subtitle">
                            {bulkResult.errors.map((err, i) => <li key={i}>{err}</li>)}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </Panel>

              <Panel title="Pending Verifications" subtitle="Individual account review">
                {verifLoading ? (
                  <LoadingState title="Loading requests..." />
                ) : verifications.length === 0 ? (
                  <EmptyState title="No pending requests" body="All signups for your organization have been processed." />
                ) : (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>{labels.user}</th>
                          <th>Role/Info</th>
                          <th>{labels.id} / {labels.program}</th>
                          <th>Domain</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {verifications.map((v) => (
                          <tr key={v.id}>
                            <td>
                              <div className="row-title">{v.full_name}</div>
                              <div className="row-subtitle">{v.email}</div>
                            </td>
                            <td>
                              <Badge tone="brand">{titleize(v.signup_role)}</Badge>
                              <div className="row-subtitle">{formatShortDate(v.created_at)}</div>
                            </td>
                            <td>
                              <div className="row-title">{v.id_number || 'N/A'}</div>
                              <div className="row-subtitle">{v.program} {v.branch ? `(${v.branch})` : ''}</div>
                            </td>
                            <td>
                              <Badge tone={v.domain_type === 'official' ? 'success' : 'warn'}>
                                {v.company_domain}
                              </Badge>
                            </td>
                            <td>
                              <div className="split-actions">
                                <Button tone="success" size="small" onClick={() => handleVerification(v.id, 'approve')}>Approve</Button>
                                <Button tone="danger" size="small" onClick={() => handleVerification(v.id, 'reject')}>Reject</Button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Panel>
            </div>
          ) : null}

          {activeTab === "pal" ? (
            <PalTrackerTab dashboard={dashboard} labels={labels} palExpanded={palExpanded} setPalExpanded={setPalExpanded} />
          ) : null}

          {activeTab === "tasks" ? (
            <TasksTab pendingTasks={pendingTasks} completedTasks={completedTasks} toggleTask={toggleTask} setTaskModal={setTaskModal} />
          ) : null}
          {activeTab === "activity" ? (
            <ActivityFeedTab events={dashboard?.activity || []} />
          ) : null}

          {activeTab === "settings" ? (
            <SettingsTab dashboard={dashboard} />
          ) : null}

          {activeTab === "reports" ? (
            <ReportsTab dashboard={dashboard} learners={learners} />
          ) : null}

          {currentSegment === "profile" ? (
            <ProfileSettingsTab 
              session={session} 
              activeTab={activeTab} 
              setActiveTab={(id) => navigate(`/categories/${slug}/admin/profile?tab=${id}`)} 
            />
          ) : null}

        </div>
      </DashboardShell>

      <CourseEditorModal
        open={courseModal.open}
        item={courseModal.item}
        onClose={() => setCourseModal({ open: false, item: null })}
        onSubmit={async (payload, isEdit) => {
          try {
            if (isEdit) {
              await updateCourse(slug, courseModal.item.id, payload);
              showToast("Course updated.", "success");
            } else {
              await createCourse(slug, payload);
              showToast("Course created.", "success");
            }
            setCourseModal({ open: false, item: null });
            await load();
          } catch (requestError) {
            showToast(getErrorMessage(requestError, "Unable to save course."), "error");
          }
        }}
      />

      <LearnerEditorModal
        open={learnerModal.open}
        seed={learnerModal.seed}
        courses={dashboard?.courses || []}
        onClose={() => setLearnerModal({ open: false, seed: null })}
        onSubmit={submitManualEnrollment}
      />

      <TaskAssignModal
        open={taskModal.open}
        item={taskModal.item}
        learners={learners}
        onClose={() => setTaskModal({ open: false, item: null })}
        onSubmit={async (payload, isEdit) => {
          try {
            if (isEdit) {
              await updateTask(taskModal.item.id, payload);
              showToast("Task updated.", "success");
            } else {
              await createTask(payload);
              showToast("Task assigned.", "success");
            }
            setTaskModal({ open: false, item: null });
            await load();
          } catch (requestError) {
            showToast(getErrorMessage(requestError, "Unable to save task."), "error");
          }
        }}
        categorySlug={slug}
      />

      <Modal
        open={Boolean(detailLearner)}
        onClose={() => setDetailLearner(null)}
        title="Learner Detail"
        description="Read-only learner profile and PAL breakdown."
        footer={<Button tone="ghost" onClick={() => setDetailLearner(null)}>Close</Button>}
        width={560}
      >
        {detailLearner ? (
          <div className="dashboard-stack">
            <div className="leaderboard-row" style={{ borderBottom: 0, padding: 0 }}>
              <Avatar initials={detailLearner.avatar_initials || getInitials(detailLearner.full_name)} gradient={detailLearner.avatar_gradient} size={42} />
              <div>
                <div className="row-title">{detailLearner.full_name}</div>
                <div className="row-subtitle">{detailLearner.email}</div>
                <div className="row-subtitle">{detailLearner.enrollment_type} · {formatShortDate(detailLearner.created_at)}</div>
              </div>
            </div>
            <div className="soft-card soft-card--tinted">
              <div className="row-title" style={{ marginBottom: 10 }}>Enrolled courses</div>
              <div className="activity-list">
                {(dashboard?.courses || []).map((course) => {
                  const progress = detailLearner.course_progress.find((item) => item.course_id === course.id);
                  return (
                    <div className="course-status-row" key={course.id}>
                      <div style={{ flex: 1 }}>
                        <div className="row-title">{course.name}</div>
                        <div className="row-subtitle">{progress?.current_lesson || progress?.status || "Not started"}</div>
                      </div>
                      <div className="mono">{progress ? `${progress.progress}%` : "0%"}</div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="soft-card soft-card--tinted">
              <div className="row-title" style={{ marginBottom: 10 }}>PAL metrics</div>
              {[
                ["Completion", detailLearner.pal_completion_pct],
                ["Quiz Avg", detailLearner.pal_quiz_avg],
                ["Time", detailLearner.pal_time_spent_hours * 2],
                ["Tasks", detailLearner.pal_task_completion_pct],
              ].map(([label, value]) => (
                <div className="metric-row" key={label} style={{ marginBottom: 10 }}>
                  <div className="row-subtitle" style={{ width: 80 }}>{label}</div>
                  <div className="progress-track">
                    <div className="progress-fill" style={{ width: `${Math.min(100, value)}%`, background: getScoreColor(value) }} />
                  </div>
                  <div className="mono" style={{ width: 36, textAlign: "right" }}>{Math.round(value)}</div>
                </div>
              ))}
            </div>
            {currentCourse ? (
              <div className="field__help">Current course: {currentCourse.name}</div>
            ) : null}
          </div>
        ) : null}
      </Modal>
    </>
  );
}

function FragmentCourseRow({
  course,
  expanded,
  onToggle,
  onEdit,
  onDelete,
  deleteOpen,
  onConfirmDelete,
  onCancelDelete,
}) {
  return (
    <>
      <tr>
        <td>
          <button type="button" className="panel-link" onClick={onToggle}>
            {course.name}
          </button>
          <div className="row-subtitle">{course.description}</div>
        </td>
        <td><Badge tone={course.tier === "Advanced" ? "accent" : "brand"}>{course.tier}</Badge></td>
        <td className="mono">{course.module_count} modules</td>
        <td className="mono">{course.enrolled_count}</td>
        <td className="mono">{formatPercent(course.completion_rate)}</td>
        <td><Badge tone={course.status === "active" ? "success" : "warn"}>{titleize(course.status)}</Badge></td>
        <td>
          <div className="split-actions">
            <IconButton label="Edit course" icon="pencil" onClick={onEdit} />
            <IconButton label="Delete course" icon="trash" onClick={onDelete} />
          </div>
          {deleteOpen ? (
            <div className="inline-confirm">
              <span>Archive this course?</span>
              <div className="split-actions">
                <Button tone="danger" onClick={onConfirmDelete}>Confirm delete</Button>
                <Button tone="ghost" onClick={onCancelDelete}>Cancel</Button>
              </div>
            </div>
          ) : null}
        </td>
      </tr>
      {expanded ? (
        <tr>
          <td colSpan={7}>
            <div className="soft-card soft-card--tinted">
              <div className="row-title" style={{ marginBottom: 8 }}>Course structure preview</div>
              <div className="activity-list">
                {course.modules.map((module) => (
                  <div className="row-subtitle" key={module}>• {module}</div>
                ))}
              </div>
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}

function CourseEditorModal({ open, item, onClose, onSubmit }) {
  const isEdit = Boolean(item);
  const [form, setForm] = useState(COURSE_INITIAL);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    setForm(
      item
        ? {
            name: item.name,
            slug: item.slug,
            description: item.description,
            tier: item.tier,
            status: item.status,
            module_count: item.module_count,
            lessons_count: item.lessons_count,
            hours: item.hours,
            modules: item.modules.join("\n"),
          }
        : COURSE_INITIAL
    );
    setErrors({});
  }, [item, open]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: "" }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const nextErrors = {};
    if (!form.name.trim()) nextErrors.name = "Course name is required.";
    if (!form.description.trim()) nextErrors.description = "Description is required.";
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      return;
    }
    await onSubmit(
      {
        name: form.name,
        slug: form.slug || form.name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
        description: form.description,
        tier: form.tier,
        status: form.status,
        module_count: Number(form.module_count) || 0,
        lessons_count: Number(form.lessons_count) || 0,
        hours: Number(form.hours) || 0,
        modules: form.modules.split("\n").map((item) => item.trim()).filter(Boolean),
      },
      isEdit
    );
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? "Edit Course" : "Add Course"}
      description="Create or update ATS course information."
      footer={
        <>
          <Button tone="ghost" onClick={onClose}>Cancel</Button>
          <Button tone="primary" onClick={handleSubmit}>{isEdit ? "Save changes" : "Create Course"}</Button>
        </>
      }
    >
      <form className="form-stack" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field__label">Course name</span>
          <input className={`field__input ${errors.name ? "is-invalid" : ""}`} value={form.name} onChange={(event) => updateField("name", event.target.value)} />
          {errors.name ? <span className="field__error">{errors.name}</span> : null}
        </label>
        <label className="field">
          <span className="field__label">Description</span>
          <input className={`field__input ${errors.description ? "is-invalid" : ""}`} value={form.description} onChange={(event) => updateField("description", event.target.value)} />
          {errors.description ? <span className="field__error">{errors.description}</span> : null}
        </label>
        <div className="field-grid">
          <label className="field">
            <span className="field__label">Tier</span>
            <select className="field__select" value={form.tier} onChange={(event) => updateField("tier", event.target.value)}>
              <option value="Basic">Basic</option>
              <option value="Advanced">Advanced</option>
            </select>
          </label>
          <label className="field">
            <span className="field__label">Status</span>
            <select className="field__select" value={form.status} onChange={(event) => updateField("status", event.target.value)}>
              <option value="active">Active</option>
              <option value="draft">Draft</option>
            </select>
          </label>
        </div>
        <div className="field-grid">
          <label className="field">
            <span className="field__label">Module count</span>
            <input className="field__input" type="number" min="0" value={form.module_count} onChange={(event) => updateField("module_count", event.target.value)} />
          </label>
          <label className="field">
            <span className="field__label">Lessons</span>
            <input className="field__input" type="number" min="0" value={form.lessons_count} onChange={(event) => updateField("lessons_count", event.target.value)} />
          </label>
        </div>
        <label className="field">
          <span className="field__label">Modules</span>
          <textarea className="field__textarea" value={form.modules} onChange={(event) => updateField("modules", event.target.value)} />
        </label>
      </form>
    </Modal>
  );
}

function LearnerEditorModal({ open, seed, courses, onClose, onSubmit }) {
  const [form, setForm] = useState(LEARNER_INITIAL);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    setForm({ ...LEARNER_INITIAL, ...seed });
    setErrors({});
  }, [seed, open]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: "" }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const nextErrors = {};
    if (!form.full_name.trim()) nextErrors.full_name = "Full name is required.";
    if (!form.email.trim()) nextErrors.email = "Email is required.";
    if (!form.course_ids.length) nextErrors.course_ids = "Select at least one course.";
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      return;
    }
    await onSubmit(form);
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add Learner"
      description="Create a learner account and assign ATS courses."
      footer={
        <>
          <Button tone="ghost" onClick={onClose}>Cancel</Button>
          <Button tone="primary" onClick={handleSubmit}>Add Learner</Button>
        </>
      }
    >
      <form className="form-stack" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field__label">Full name</span>
          <input className={`field__input ${errors.full_name ? "is-invalid" : ""}`} value={form.full_name} onChange={(event) => updateField("full_name", event.target.value)} />
          {errors.full_name ? <span className="field__error">{errors.full_name}</span> : null}
        </label>
        <label className="field">
          <span className="field__label">Email</span>
          <input className={`field__input ${errors.email ? "is-invalid" : ""}`} value={form.email} onChange={(event) => updateField("email", event.target.value)} />
          {errors.email ? <span className="field__error">{errors.email}</span> : null}
        </label>
        <div className="field">
          <span className="field__label">Enrollment type</span>
          <div className="radio-row">
            {["manual", "self"].map((option) => (
              <label className="radio-pill" key={option}>
                <input type="radio" checked={form.enrollment_type === option} onChange={() => updateField("enrollment_type", option)} />
                {titleize(option)}
              </label>
            ))}
          </div>
        </div>
        <div className="field">
          <span className="field__label">Courses</span>
          <div className="checkbox-grid">
            {courses.map((course) => (
              <label className="radio-pill" key={course.id}>
                <input
                  type="checkbox"
                  checked={form.course_ids.includes(course.id)}
                  onChange={() =>
                    updateField(
                      "course_ids",
                      form.course_ids.includes(course.id)
                        ? form.course_ids.filter((value) => value !== course.id)
                        : [...form.course_ids, course.id]
                    )
                  }
                />
                {course.name}
              </label>
            ))}
          </div>
          {errors.course_ids ? <span className="field__error">{errors.course_ids}</span> : null}
        </div>
        <label className="field">
          <span className="field__label">Note</span>
          <textarea className="field__textarea" value={form.note} onChange={(event) => updateField("note", event.target.value)} />
        </label>
      </form>
    </Modal>
  );
}

function TaskAssignModal({ open, item, learners, onClose, onSubmit, categorySlug }) {
  const isEdit = Boolean(item);
  const [form, setForm] = useState(TASK_INITIAL);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    setForm(
      item
        ? {
            title: item.title,
            description: item.description,
            assigned_to_user_id: item.assigned_to_user_id || "all",
            due_at: item.due_at,
            notes: item.notes || "",
          }
        : TASK_INITIAL
    );
    setErrors({});
  }, [item, open]);

  async function handleSubmit(event) {
    event.preventDefault();
    const nextErrors = {};
    if (!form.title.trim()) nextErrors.title = "Task title is required.";
    if (!form.due_at) nextErrors.due_at = "Due date is required.";
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      return;
    }
    const learner = learners.find((entry) => entry.id === form.assigned_to_user_id);
    await onSubmit(
      {
        title: form.title,
        description: form.description,
        assigned_label: learner?.full_name || "All learners",
        assigned_to_user_id: learner?.id || null,
        assignment_scope: learner ? "individual" : "all_learners",
        category_slug: categorySlug,
        due_at: form.due_at,
        status: item?.status || "pending",
        notes: form.notes,
        is_cross_category: false,
      },
      isEdit
    );
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Assign Task"
      description="Assign a practice task to an individual learner or the full cohort."
      footer={
        <>
          <Button tone="ghost" onClick={onClose}>Cancel</Button>
          <Button tone="primary" onClick={handleSubmit}>{isEdit ? "Save changes" : "Assign Task"}</Button>
        </>
      }
    >
      <form className="form-stack" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field__label">Task title</span>
          <input className={`field__input ${errors.title ? "is-invalid" : ""}`} value={form.title} onChange={(event) => { setForm((current) => ({ ...current, title: event.target.value })); setErrors((current) => ({ ...current, title: "" })); }} />
          {errors.title ? <span className="field__error">{errors.title}</span> : null}
        </label>
        <label className="field">
          <span className="field__label">Assign to</span>
          <select className="field__select" value={form.assigned_to_user_id} onChange={(event) => setForm((current) => ({ ...current, assigned_to_user_id: event.target.value }))}>
            <option value="all">All learners</option>
            {learners.map((learner) => (
              <option key={learner.id} value={learner.id}>{learner.full_name}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field__label">Due date</span>
          <input className={`field__input ${errors.due_at ? "is-invalid" : ""}`} type="date" value={form.due_at} onChange={(event) => { setForm((current) => ({ ...current, due_at: event.target.value })); setErrors((current) => ({ ...current, due_at: "" })); }} />
          {errors.due_at ? <span className="field__error">{errors.due_at}</span> : null}
        </label>
        <label className="field">
          <span className="field__label">Additional notes (optional)</span>
          <textarea className="field__textarea" value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} />
        </label>
      </form>
    </Modal>
  );
}

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true };
  }
  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "2rem", color: "var(--danger)", textAlign: "center" }}>
          <h2>Something went wrong loading this dashboard.</h2>
          <p>Please refresh the page or try again later.</p>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function CategoryAdminPage(props) {
  return (
    <ErrorBoundary>
      <CategoryAdminPageContent {...props} />
    </ErrorBoundary>
  );
}
