import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useLocation, useSearchParams } from "react-router-dom";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import {
  approveBatchEnrollments,
  approveEnrollmentRequest,
  approveVerification,
  bulkUploadVerifications,
  createAdmin,
  createCategory,
  createTask,
  deleteCategory,
  deleteUser,
  fetchSettings,
  fetchSuperAdminDashboard,
  fetchOrganizations,
  fetchUsers,
  fetchVerifications,
  getErrorMessage,
  rejectEnrollmentRequest,
  rejectVerification,
  updateAdmin,
  updateCategory,
  updateTask,
  deleteTask,
} from "../../services/client";
import { ChartCanvas } from "../../components/common/charts";
import { DashboardShell, SectionTitle, ProfileDropdown } from "../../layouts/DashboardLayout";
import { ProfileSettingsTab } from "../../components/dashboard/CategoryAdminTabs";
import { TaskBoardKanban } from "../../components/dashboard/TaskBoard";
import { useSuperAdminStore } from "../../store/dashboardStore";
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
  formatDateTime,
  formatMonthDate,
  formatPercent,
  formatShortDate,
  getCompletionColor,
  getInitials,
  getRankColor,
  getRoleLabel,
  getScoreColor,
  getStatusTone,
  titleize,
} from "../../utils/formatters";
import { useKpiPulse } from "../../hooks/useKpiPulse";

const CATEGORY_INITIAL = {
  name: "",
  slug: "",
  description: "",
  admin_user_id: "",
  planned_courses: 0,
  status: "active",
  accent_color: "#7C3AED",
  org_type: "college",
  organization_id: "",
};

const ADMIN_INITIAL = {
  full_name: "",
  email: "",
  role: "category_admin",
  category_scope: "ats",
  password: "",
  username: "",
};

const TASK_INITIAL = {
  title: "",
  description: "",
  assignee: "all_new_learners",
  category_slug: "all",
  due_at: "",
  status: "pending",
  notes: "",
};

const ALL_SCOPE_OPTIONS = [
  { value: "all_new_learners", label: "All new learners" },
  { value: "all_categories", label: "All categories" },
  { value: "all_admins", label: "All admins" },
];

export default function SuperAdminPage({ session, onLogout }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { showToast } = useToast();
  const scrollRef = useRef(null);
  const {
    dashboard,
    users,
    settings,
    verifications,
    organizations,
    loading,
    error,
    fetchData: load,
    updateTaskState
  } = useSuperAdminStore();
  const [exportOpen, setExportOpen] = useState(false);
  const [categoryModal, setCategoryModal] = useState({ open: false, item: null });
  const [adminModal, setAdminModal] = useState({ open: false, item: null });
  const [taskModal, setTaskModal] = useState({ open: false, item: null });
  const [categoryDeleteId, setCategoryDeleteId] = useState(null);
  const [taskDeleteId, setTaskDeleteId] = useState(null);
  const [userDeleteId, setUserDeleteId] = useState(null);
  const [expandedAudit, setExpandedAudit] = useState(false);
  const [userFilter, setUserFilter] = useState("all");
  const [userQuery, setUserQuery] = useState("");
  const deferredUserQuery = useDeferredValue(userQuery);
  const [bulkFile, setBulkFile] = useState(null);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);
  const [newDomain, setNewDomain] = useState("");
  const [newDomainLabel, setNewDomainLabel] = useState("");

  const kpiPulse = useKpiPulse(dashboard?.kpis || {});
  const isMoodleSource = dashboard?.data_source === "moodle" || settings?.data_source === "moodle";

  // Derive the active tab from the URL
  const currentPath = location.pathname.replace(/\/$/, ""); // Remove trailing slash
  const pathParts = currentPath.split("/");
  const currentTab = pathParts[pathParts.length - 1];
  
  const [searchParams] = useSearchParams();

  // Map the URL tab to the internal activeNav ID
  let activeNav = "section-overview";
  if (currentTab === "profile") {
    activeNav = "section-profile";
  } else if (currentTab !== "super-admin") {
    activeNav = `section-${currentTab}`;
  }
  
  const activeProfileTab = searchParams.get("tab") || "general";

  const navGroups = [
    {
      label: "Overview",
      items: [
        { id: "section-overview", label: "Dashboard", icon: "dashboard" },
        { id: "section-analytics", label: "Analytics", icon: "analytics" },
      ],
    },
    {
      label: "Management",
      items: [
        {
          id: "section-categories",
          label: "Categories",
          icon: "category",
          badge: String(dashboard?.kpis?.total_categories || 0),
          badgeTone: "accent",
        },
        { id: "section-admin", label: "Admin control", icon: "shield" },
        { id: "section-users", label: "All users", icon: "users" },
        {
          id: "section-enrollments",
          label: "Enrollments",
          icon: "enrollments",
          badge: String(dashboard?.kpis?.pending_approvals || 0),
          badgeTone: "warn",
        },
        {
          id: "section-verifications",
          label: "Verifications",
          icon: "shield",
          badge: String(dashboard?.kpis?.pending_verifications || 0),
          badgeTone: "warn",
        },
        { id: "section-tasks", label: "Task assign", icon: "task" },
      ],
    },
    {
      label: "Reports",
      items: [
        { id: "section-pal", label: "PAL performance", icon: "leaderboard" },
        { id: "section-audit", label: "Audit log", icon: "reports" },
      ],
    },
    {
      label: "System",
      items: [{ id: "section-settings", label: "Settings", icon: "settings" }],
    },
  ];

  const categoryAdmins = users.filter((user) => user.role === "category_admin");
  const learnerUsers = users.filter((user) => user.role === "learner");

  const filteredUsers = useMemo(() => {
    return users.filter((user) => {
      if (userFilter === "admins" && !["super_admin", "category_admin"].includes(user.role)) {
        return false;
      }
      if (userFilter === "learners" && user.role !== "learner") {
        return false;
      }
      if (!deferredUserQuery) {
        return true;
      }
      const haystack = `${user.full_name} ${user.email} ${user.username}`.toLowerCase();
      return haystack.includes(deferredUserQuery.toLowerCase());
    });
  }, [deferredUserQuery, userFilter, users]);

  const visibleAudit = expandedAudit ? dashboard?.audit_log || [] : (dashboard?.audit_log || []).slice(0, 5);

  useEffect(() => {
    load();
  }, []);

  function changeSection(item) {
    setExportOpen(false);
    const route = item.id.replace("section-", "");
    if (route === "overview") {
      navigate("/super-admin");
    } else {
      navigate(`/super-admin/${route}`);
    }
  }

  function exportCSV() {
    let dataToExport = [];
    let filename = "export";

    if (activeNav === "section-categories") {
      dataToExport = dashboard.categories;
      filename = "categories_export";
    } else if (activeNav === "section-users") {
      dataToExport = filteredUsers;
      filename = "users_export";
    } else if (activeNav === "section-tasks") {
      dataToExport = dashboard.tasks;
      filename = "tasks_export";
    } else if (activeNav === "section-enrollments") {
      dataToExport = dashboard.enrollments;
      filename = "enrollments_export";
    } else if (activeNav === "section-verifications") {
      dataToExport = verifications;
      filename = "verifications_export";
    } else if (activeNav === "section-pal") {
      dataToExport = dashboard.pal_performance;
      filename = "pal_performance_export";
    } else if (activeNav === "section-audit") {
      dataToExport = dashboard.audit_log;
      filename = "audit_log_export";
    }

    if (!dataToExport || dataToExport.length === 0) {
      showToast("No data to export for this view.", "warning");
      return;
    }

    const headers = Object.keys(dataToExport[0]).join(",");
    const rows = dataToExport.map(row => 
      Object.values(row).map(val => `"${String(val).replace(/"/g, '""')}"`).join(",")
    );
    const csvContent = [headers, ...rows].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Export downloaded successfully.", "success");
    setExportOpen(false);
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
      await rejectEnrollmentRequest(requestId, "Rejected by super admin");
      showToast("Enrollment denied.", "warning");
      await load();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to deny enrollment."), "error");
    }
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
      await load();
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
      await load();
    } catch (err) {
      showToast(getErrorMessage(err, "Bulk upload failed"), "error");
    } finally {
      setBulkLoading(false);
    }
  }

  async function handleApproveAll() {
    if (!dashboard?.enrollment_audit?.visible_pending_ids?.length) return;
    try {
      await approveBatchEnrollments(dashboard.enrollment_audit.visible_pending_ids);
      showToast(`${dashboard.enrollment_audit.visible_pending_ids.length} requests approved.`, "success");
      await load();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Bulk approval failed."), "error");
    }
  }

  function handleAddDomain() {
    if (!newDomain.trim() || !newDomainLabel.trim()) {
      showToast("Both domain and label are required.", "warning");
      return;
    }
    const domainToAdd = newDomain.startsWith("@") ? newDomain : `@${newDomain}`;
    useSuperAdminStore.setState((prev) => ({
      settings: {
        ...prev.settings,
        allowed_domains: [...(prev.settings?.allowed_domains || []), { domain: domainToAdd, label: newDomainLabel }]
      }
    }));
    setNewDomain("");
    setNewDomainLabel("");
    showToast("Domain added.", "success");
  }

  function handleDeleteDomain(domainToRemove) {
    useSuperAdminStore.setState((prev) => ({
      settings: {
        ...prev.settings,
        allowed_domains: (prev.settings?.allowed_domains || []).filter(d => d.domain !== domainToRemove)
      }
    }));
    showToast("Domain removed.", "success");
  }

  async function handleDeleteCategory(categoryId) {
    try {
      await deleteCategory(categoryId);
      setCategoryDeleteId(null);
      showToast("Category archived.", "warning");
      await load();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to archive category."), "error");
    }
  }

  async function handleDeleteTask(taskId) {
    try {
      await deleteTask(taskId);
      setTaskDeleteId(null);
      showToast("Task removed.", "warning");
      await load();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to remove task."), "error");
    }
  }

  async function handleToggleTask(taskId, newStatus) {
    // Optimistic update
    updateTaskState(taskId, newStatus);
    try {
      await updateTask(taskId, { status: newStatus });
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to update task status"), "error");
      await load(); // Revert on failure
    }
  }

  async function handleDeleteUser(userId) {
    try {
      await deleteUser(userId);
      setUserDeleteId(null);
      showToast("User archived.", "warning");
      await load();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to archive user."), "error");
    }
  }

  if (loading) {
    return <LoadingState title="Loading Super Admin dashboard..." body="Pulling categories, learners, enrollments, and audit activity." />;
  }

  if (error || !dashboard) {
    return <ErrorState body={error || "The dashboard did not return any data."} action={<Button tone="primary" onClick={load}>Retry</Button>} />;
  }

  return (
    <>
      <DashboardShell
        theme="super"
        brandMark={{ label: "TS", background: "linear-gradient(135deg, #7C3AED, #2563EB)" }}
        brandTitle="Telite Systems"
        brandSubtitle="super-admin"
        navGroups={navGroups}
        activeNav={activeNav}
        onNavClick={changeSection}
        profile={{
          initials: getInitials(session?.user?.name || "Rajan Mehra"),
          gradient: ["#7C3AED", "#2563EB"],
          name: session?.user?.name || "Rajan Mehra",
          roleLabel: "super-admin",
        }}
        title="Super Admin Dashboard"
        subtitle={isMoodleSource ? "Telite Systems · Moodle-backed view" : "Telite Systems · All categories"}
        topbarBadge={{ tone: "accent", label: "super-admin access" }}
        topbarActions={
          <>
            <div className="menu-wrap">
              <Button tone="ghost" icon="download" onClick={() => setExportOpen((value) => !value)}>
                Export report
              </Button>
              {exportOpen ? (
                <div className="menu-popover">
                  <button
                    type="button"
                    onClick={exportCSV}
                  >
                    Export as CSV
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setExportOpen(false);
                      try {
                        const doc = new jsPDF();
                        doc.text(`Telite Super Admin Export - ${titleize(activeNav.replace('section-', ''))}`, 14, 15);
                        doc.setFontSize(10);
                        doc.text(`Date: ${new Date().toLocaleDateString()}`, 14, 22);

                        let dataToExport = [];
                        let head = [];
                        let body = [];

                        if (activeNav === "section-categories") {
                          head = [["Category", "Slug", "Learners", "Sync Status", "Status"]];
                          body = (dashboard.categories || []).map(c => [
                            c.name, c.slug, c.learners_count, c.sync_status || "not_synced", c.status
                          ]);
                        } else if (activeNav === "section-users") {
                          head = [["Name", "Email", "Role", "Scope"]];
                          body = (filteredUsers || []).map(u => [
                            u.full_name, u.email, u.role, u.category_scope || "N/A"
                          ]);
                        } else if (activeNav === "section-tasks") {
                          head = [["Task", "Assignee", "Scope", "Due", "Status"]];
                          body = (dashboard.tasks || []).map(t => [
                            t.title, t.assigned_label, t.category_slug, t.due_at || "N/A", t.status
                          ]);
                        } else if (activeNav === "section-enrollments") {
                          head = [["Name", "Email", "Type", "Requested"]];
                          body = (dashboard.enrollments || []).map(r => [
                            r.full_name, r.email || "", r.request_type, r.requested_at
                          ]);
                        } else if (activeNav === "section-verifications") {
                          head = [["Name", "Email", "Role", "Requested"]];
                          body = (verifications || []).map(r => [
                            r.full_name, r.email || "", r.role, r.requested_at || "N/A"
                          ]);
                        } else if (activeNav === "section-pal") {
                          head = [["Name", "Completion %", "Quiz Avg", "Time (h)", "PAL Score"]];
                          body = (dashboard.pal_performance || []).map(l => [
                            l.full_name, `${l.pal_completion_pct}%`, `${Math.round(l.pal_quiz_avg)}%`, `${Math.round(l.pal_time_spent_hours)}h`, l.pal_score
                          ]);
                        } else if (activeNav === "section-audit") {
                          head = [["Action", "User", "IP", "Timestamp"]];
                          body = (dashboard.audit_log || []).map(l => [
                            l.action_type, l.user_email, l.ip_address, l.timestamp
                          ]);
                        }

                        if (body.length === 0) {
                          showToast("No data available for export.", "warning");
                          return;
                        }

                        autoTable(doc, {
                          startY: 28,
                          head,
                          body,
                          theme: 'striped',
                          headStyles: { fillColor: [124, 58, 237] }, // Purple super admin brand
                        });
                        
                        doc.save(`telite_superadmin_${activeNav.replace('section-', '')}_export_${new Date().toISOString().slice(0,10)}.pdf`);
                        showToast("PDF exported successfully!", "success");
                      } catch (err) {
                        showToast("PDF export failed: " + err.message, "error");
                      }
                    }}
                  >
                    Export as PDF
                  </button>
                </div>
              ) : null}
            </div>
            <Button tone="primary" icon="plus" onClick={() => setCategoryModal({ open: true, item: null })}>
              New category
            </Button>
            <ProfileDropdown profile={{
              initials: getInitials(session?.user?.name || "Rajan Mehra"),
              gradient: ["#7C3AED", "#2563EB"],
              name: session?.user?.name || "Rajan Mehra",
              email: session?.user?.email || "rajan@telite.io",
              roleLabel: "super-admin",
            }} onNavigate={(tab) => navigate(`/super-admin/profile?tab=${tab}`)} onLogout={onLogout} />
          </>
        }
        scrollRef={scrollRef}
      >
        <div className="dashboard-stack">
          {activeNav === "section-overview" && (
          <section id="section-overview" className="dashboard-stack">
            <div className="grid-4">
              <StatCard
                accent="#7C3AED"
                label="Total Categories"
                value={dashboard.kpis.total_categories}
                meta={
                  isMoodleSource
                    ? `${dashboard.sync_summary?.synced_categories || 0} synced to Moodle`
                    : "Updated this month"
                }
                pulse={kpiPulse.total_categories}
              />
              <StatCard
                accent="#2563EB"
                label="Total Courses"
                value={dashboard.kpis.total_courses}
                meta={isMoodleSource ? "Live Moodle course count" : "Across all categories"}
                pulse={kpiPulse.total_courses}
              />
              <StatCard
                accent="#059669"
                label={isMoodleSource ? "Moodle Users" : "Total Learners"}
                value={dashboard.kpis.total_learners}
                meta={isMoodleSource ? "Active Moodle accounts" : "Enrolled this quarter"}
                pulse={kpiPulse.total_learners}
              />
              <StatCard
                accent="#D97706"
                label="Pending Approvals"
                value={dashboard.kpis.pending_approvals}
                meta={isMoodleSource ? "Not exposed by current Moodle API" : "Requires action"}
                pulse={kpiPulse.pending_approvals}
              />
            </div>

            {!isMoodleSource ? (
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
            ) : null}
          </section>
          )}

          {activeNav === "section-categories" && (
          <section id="section-categories">
            <SectionTitle label="Learning Categories" />
            <div className="grid-3">
              {dashboard.categories.map((category) => (
                <article className="category-card" key={category.id}>
                  <span className="category-card__bar" style={{ background: category.accent_color }} />
                  <div className="category-card__actions">
                    <IconButton
                      label="Edit category"
                      icon="pencil"
                      onClick={() => setCategoryModal({ open: true, item: category })}
                    />
                    <IconButton
                      label="Delete category"
                      icon="trash"
                      onClick={() => setCategoryDeleteId((value) => (value === category.id ? null : category.id))}
                    />
                  </div>
                  <div className="category-card__name">{category.name}</div>
                  <div className="category-card__meta">
                    {category.slug} · {category.total_courses} courses ·{" "}
                    {isMoodleSource
                      ? `sync: ${category.is_synced ? "synced to Moodle" : "not synced to Moodle"}`
                      : `admin: ${category.admin_name}`}
                  </div>
                  <div className="stat-pair">
                    <div className="stat-pair__card">
                      <span>Learners</span>
                      <strong style={{ color: category.accent_color }}>{category.total_learners}</strong>
                    </div>
                    <div className="stat-pair__card">
                      <span>{isMoodleSource ? "Sync status" : "Avg PAL"}</span>
                      <strong style={{ color: category.accent_color }}>
                        {isMoodleSource
                          ? titleize(category.sync_status || "not_synced")
                          : formatPercent(category.avg_pal)}
                      </strong>
                    </div>
                  </div>
                  <div className="category-card__footer">
                    <Badge tone={category.status === "active" ? "success" : "warn"}>
                      {category.status === "active" ? "Active" : titleize(category.status)}
                    </Badge>
                    <button
                      className="panel-link"
                      type="button"
                      onClick={() => {
                        showToast(`Opening ${category.name} dashboard...`, "info");
                        navigate(`/categories/${category.slug}/admin`);
                      }}
                    >
                      View dashboard →
                    </button>
                  </div>
                  {categoryDeleteId === category.id ? (
                    <div className="inline-confirm">
                      <span>Archive this category?</span>
                      <div className="split-actions">
                        <Button tone="danger" onClick={() => handleDeleteCategory(category.id)}>
                          Confirm delete
                        </Button>
                        <Button tone="ghost" onClick={() => setCategoryDeleteId(null)}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          </section>
          )}

          {activeNav === "section-pal" && (
          <section id="section-pal">
            <Panel
              className="panel"
              title={isMoodleSource ? "Moodle category distribution" : "PAL leaderboard - all categories"}
              subtitle={
                isMoodleSource
                  ? "Live category and course data from Moodle"
                  : "Top learners across the organization"
              }
              action={
                isMoodleSource ? (
                  <Badge tone="neutral">live Moodle</Badge>
                ) : (
                  <>
                    <Badge tone="neutral">all-time</Badge>
                    <button className="panel-link" type="button" onClick={() => navigate("/categories/ats/stats")}>
                      Full report
                    </button>
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
          )}

          {activeNav === "section-admin" && (
          <section id="section-admin">
            <Panel
              title="Admin control"
              subtitle={
                isMoodleSource
                  ? "Read-only admin roles mapped from live Moodle accounts"
                  : "Assigned category administrators"
              }
              action={
                !isMoodleSource ? (
                  <button className="panel-link" type="button" onClick={() => setAdminModal({ open: true, item: null })}>
                    + Add admin
                  </button>
                ) : null
              }
            >
              <div id="section-admin">
                {dashboard.admins.length ? (
                  dashboard.admins.map((admin) => (
                    <div className="admin-row" key={admin.id}>
                      <Avatar initials={admin.avatar_initials} gradient={admin.avatar_gradient} size={30} />
                      <div style={{ flex: 1 }}>
                        <div className="row-title">{admin.full_name}</div>
                        <div className="row-subtitle">{admin.email}</div>
                      </div>
                      <Badge tone={admin.role === "super_admin" ? "accent" : "brand"}>
                        {getRoleLabel(admin)}
                      </Badge>
                      {!isMoodleSource ? (
                        <IconButton
                          label="Edit admin"
                          icon="pencil"
                          onClick={() => setAdminModal({ open: true, item: admin })}
                        />
                      ) : null}
                    </div>
                  ))
                ) : (
                  <EmptyState title="No synced admins found" body={dashboard.notes?.admins || "No admin data available."} />
                )}
              </div>
              <div style={{ marginTop: 16 }}>
                {isMoodleSource ? (
                  <div className="field__help">{dashboard.notes?.admins}</div>
                ) : (
                  <Button
                    tone="ghost"
                    className="btn--block"
                    onClick={() => scrollToSection({ id: "section-users" })}
                  >
                    Manage all admins
                  </Button>
                )}
              </div>
            </Panel>
          </section>
          )}

          {activeNav === "section-enrollments" && (
          <section id="section-enrollments">
            <Panel
              title="Enrollment audit log"
              subtitle={isMoodleSource ? "Read-only" : "manual & self-enrol"}
              action={!isMoodleSource ? <button className="panel-link" type="button">View all</button> : null}
            >
              {isMoodleSource ? (
                <EmptyState
                  title="Enrollment queue unavailable"
                  body={dashboard.notes?.enrollment || "No enrollment queue returned from Moodle."}
                />
              ) : (
                <>
                  <div id="section-enrollments" className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>User</th>
                          <th>Category</th>
                          <th>Type</th>
                          <th>Status</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dashboard.enrollment_audit.rows.map((row) => (
                          <tr key={row.request_id}>
                            <td className="row-title">{row.full_name}</td>
                            <td className="muted">{row.category}</td>
                            <td>
                              <Badge tone={row.type === "self" ? "accent" : "brand"}>{row.type}</Badge>
                            </td>
                            <td>
                              <Badge tone={getStatusTone(row.status)}>{row.status}</Badge>
                            </td>
                            <td>
                              {row.status === "Pending" ? (
                                <div className="split-actions">
                                  <Button tone="success" onClick={() => handleApprove(row.request_id)}>
                                    Approve
                                  </Button>
                                  <Button tone="danger" onClick={() => handleReject(row.request_id)}>
                                    Deny
                                  </Button>
                                </div>
                              ) : (
                                <IconButton
                                  label="View request"
                                  icon="eye"
                                  onClick={() => showToast(`Viewing ${row.full_name} enrollment history.`, "info")}
                                />
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="split-actions">
                    <Button
                      tone="ghost"
                      onClick={handleApproveAll}
                      disabled={!dashboard.enrollment_audit.visible_pending_ids.length}
                    >
                      Approve pending ({dashboard.enrollment_audit.visible_pending_ids.length})
                    </Button>
                    <Button tone="ghost" onClick={() => showToast("Enrollment log export initiated...", "info")}>
                      Export CSV
                    </Button>
                  </div>
                </>
              )}
            </Panel>
          </section>
          )}

          {activeNav === "section-verifications" && (
          <section id="section-verifications">
            <Panel
              id="section-verifications"
              title="Signup Verifications"
              subtitle="Approve or reject new user accounts"
              action={
                <div className="split-actions">
                  <input 
                    type="file" 
                    id="bulk-verif-input" 
                    style={{ display: 'none' }} 
                    onChange={(e) => setBulkFile(e.target.files[0])}
                  />
                  {bulkFile && <span className="row-subtitle">{bulkFile.name}</span>}
                  <Button 
                    tone="ghost" 
                    size="small" 
                    onClick={() => document.getElementById('bulk-verif-input').click()}
                  >
                    {bulkFile ? "Change File" : "Select Bulk File"}
                  </Button>
                  <Button 
                    tone="primary" 
                    size="small" 
                    disabled={!bulkFile || bulkLoading}
                    loading={bulkLoading}
                    onClick={handleBulkUpload}
                  >
                    Bulk Upload
                  </Button>
                </div>
              }
            >
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Org / Role</th>
                      <th>Details</th>
                      <th>Status</th>
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
                          <div className="row-title">{v.organization_name}</div>
                          <Badge tone="brand">{titleize(v.signup_role)}</Badge>
                        </td>
                        <td>
                          <div className="row-subtitle">ID: {v.id_number || 'N/A'}</div>
                          <div className="row-subtitle">{v.program} {v.branch ? `(${v.branch})` : ''}</div>
                        </td>
                        <td>
                          <Badge tone={v.domain_type === 'official' ? 'success' : 'warn'}>
                            {v.company_domain}
                          </Badge>
                        </td>
                        <td>
                          <div className="split-actions">
                            <IconButton label="Approve" icon="check" onClick={() => handleVerification(v.id, 'approve')} />
                            <IconButton label="Reject" icon="close" onClick={() => handleVerification(v.id, 'reject')} />
                          </div>
                        </td>
                      </tr>
                    ))}
                    {verifications.length === 0 && (
                      <tr>
                        <td colSpan="5" style={{ textAlign: 'center', padding: '32px 0' }}>
                          <div className="row-subtitle">No pending verifications</div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              {bulkResult && (
                <div className="soft-card" style={{ marginTop: 16 }}>
                  <div className="row-title">Bulk Result: {bulkResult.approved_count} approved, {bulkResult.ignored_count} ignored</div>
                </div>
              )}
            </Panel>
          </section>
          )}

          {activeNav === "section-audit" && (
          <section id="section-audit">
            <Panel
              title="Audit log"
              subtitle="Recent system activity"
              action={
                !isMoodleSource && visibleAudit.length ? (
                  <button className="panel-link" type="button" onClick={() => setExpandedAudit((value) => !value)}>
                    {expandedAudit ? "Collapse" : "Full log"}
                  </button>
                ) : null
              }
            >
              <div className="search-toolbar" style={{ marginBottom: 16 }}>
                <div className="toolbar">
                  <label className="chip">
                    <input type="radio" defaultChecked name="auditFilter" /> All
                  </label>
                  <label className="chip">
                    <input type="radio" name="auditFilter" /> Login
                  </label>
                  <label className="chip">
                    <input type="radio" name="auditFilter" /> Enrollment
                  </label>
                  <label className="chip">
                    <input type="radio" name="auditFilter" /> Verification
                  </label>
                </div>
                <label className="field" style={{ flex: 1, maxWidth: 300 }}>
                  <input className="field__input" type="text" placeholder="Search users or actions..." />
                </label>
              </div>

              {visibleAudit.length ? (
                <div id="section-audit" className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Timestamp</th>
                        <th>User</th>
                        <th>Action</th>
                        <th>Details</th>
                        <th>IP Address</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleAudit.map((entry) => (
                        <tr key={entry.id}>
                          <td className="mono" style={{ whiteSpace: "nowrap" }}>
                            {formatDateTime(entry.created_at)}
                          </td>
                          <td>
                            <div className="row-title">{entry.actor_name}</div>
                          </td>
                          <td>
                            <Badge tone={entry.accent === "amber" ? "warn" : entry.accent === "blue" ? "brand" : "neutral"}>
                              {titleize(entry.accent || "system")}
                            </Badge>
                          </td>
                          <td>
                            <div className="row-subtitle" style={{ color: "var(--text-primary)" }}>{entry.message}</div>
                            <div className="row-subtitle muted">{entry.result}</div>
                          </td>
                          <td className="mono">{entry.ip_address || "192.168.1.1"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="Audit log unavailable" body={dashboard.notes?.audit || "No audit data available."} />
              )}
              {!isMoodleSource && visibleAudit.length ? (
                <div style={{ marginTop: 16 }}>
                  <Button tone="ghost" className="btn--block" onClick={() => setExpandedAudit((value) => !value)}>
                    {expandedAudit ? "Hide extra entries" : "Load more entries"}
                  </Button>
                </div>
              ) : null}
            </Panel>
          </section>
          )}

          {activeNav === "section-users" && (
          <section id="section-users">
            <Panel
              title="All users"
              subtitle={
                isMoodleSource
                  ? `${users.length} live Moodle accounts`
                  : `${users.length} accounts across admins and learners`
              }
              action={
                <div className="toolbar">
                  <label className="chip">
                    <input
                      type="radio"
                      checked={userFilter === "all"}
                      onChange={() => setUserFilter("all")}
                    />
                    All
                  </label>
                  <label className="chip">
                    <input
                      type="radio"
                      checked={userFilter === "admins"}
                      onChange={() => setUserFilter("admins")}
                    />
                    Admins
                  </label>
                  <label className="chip">
                    <input
                      type="radio"
                      checked={userFilter === "learners"}
                      onChange={() => setUserFilter("learners")}
                    />
                    Learners
                  </label>
                </div>
              }
            >
              <div className="search-toolbar" style={{ marginBottom: 16 }}>
                <label className="field" style={{ flex: 1 }}>
                  <span className="field__label">{isMoodleSource ? "Search Moodle users" : "Search users"}</span>
                  <input
                    className="field__input"
                    type="text"
                    value={userQuery}
                    onChange={(event) => setUserQuery(event.target.value)}
                    placeholder="Search by name, email, or username..."
                  />
                </label>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Role</th>
                      <th>Category</th>
                      <th>PAL</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.map((user) => (
                      <tr key={user.id}>
                        <td>
                          <div className="leaderboard-row" style={{ padding: 0, borderBottom: 0 }}>
                            <Avatar
                              initials={user.avatar_initials || getInitials(user.full_name)}
                              gradient={user.avatar_gradient || ["#2563EB", "#7C3AED"]}
                              size={28}
                            />
                            <div>
                              <div className="row-title">{user.full_name}</div>
                              <div className="row-subtitle">{user.email}</div>
                            </div>
                          </div>
                        </td>
                        <td>
                          <Badge
                            tone={
                              user.role === "super_admin"
                                ? "accent"
                                : user.role === "category_admin"
                                  ? "brand"
                                  : "neutral"
                            }
                          >
                            {getRoleLabel(user)}
                          </Badge>
                        </td>
                        <td className="muted">{user.category_scope || "Global"}</td>
                        <td className="mono">{user.role === "learner" ? formatPercent(user.pal_score) : "--"}</td>
                        <td>
                          <Badge tone={user.is_active ? "success" : "neutral"}>
                            {user.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </td>
                        <td>
                          <div className="split-actions">
                            <IconButton
                              label="View user"
                              icon="eye"
                              onClick={() => showToast(`Viewing ${user.full_name}.`, "info")}
                            />
                            {!isMoodleSource ? (
                              <IconButton
                                label="Archive user"
                                icon="trash"
                                onClick={() => setUserDeleteId((value) => (value === user.id ? null : user.id))}
                              />
                            ) : null}
                          </div>
                          {!isMoodleSource && userDeleteId === user.id ? (
                            <div className="inline-confirm">
                              <span>Archive {user.full_name}?</span>
                              <div className="split-actions">
                                <Button tone="danger" onClick={() => handleDeleteUser(user.id)}>
                                  Confirm delete
                                </Button>
                                <Button tone="ghost" onClick={() => setUserDeleteId(null)}>
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!filteredUsers.length ? (
                  <EmptyState title="No users found" body="Try a different role filter or search term." />
                ) : null}
              </div>
            </Panel>
          </section>
          )}

          {activeNav === "section-tasks" && (
          <section id="section-tasks">
            <Panel
              title="Cross-category task assignment"
              subtitle={isMoodleSource ? "Hidden in Moodle-only mode" : "super-admin only"}
              action={
                !isMoodleSource ? (
                  <button className="panel-link" type="button" onClick={() => setTaskModal({ open: true, item: null })}>
                    + New task
                  </button>
                ) : null
              }
            >
              {isMoodleSource ? (
                <EmptyState title="Task data hidden" body={dashboard.notes?.tasks || "Task data is not sourced from Moodle."} />
              ) : (
                <div style={{ marginTop: 24 }}>
                  <TaskBoardKanban 
                    allTasks={dashboard.tasks || []} 
                    onTaskStatusChange={handleToggleTask}
                    onEdit={(task) => setTaskModal({ open: true, item: task })}
                    onDelete={(taskId) => handleDeleteTask(taskId)}
                  />
                </div>
              )}
            </Panel>
          </section>
          )}

          {activeNav === "section-analytics" && (
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
          )}

          {activeNav === "section-settings" && (
          <section id="section-settings">
            <Panel
              title="System settings"
              subtitle={isMoodleSource ? "Live Moodle service configuration" : "Current backend and Moodle configuration"}
            >
              <div className="grid-3">
                <div className="soft-card soft-card--tinted">
                  <div className="row-subtitle">Moodle URL</div>
                  <div className="row-title">{settings?.moodle_url}</div>
                </div>
                <div className="soft-card soft-card--tinted">
                  <div className="row-subtitle">{isMoodleSource ? "Moodle release" : "API version"}</div>
                  <div className="row-title mono">{isMoodleSource ? settings?.moodle_release : settings?.api_version}</div>
                </div>
                <div className="soft-card soft-card--tinted">
                  <div className="row-subtitle">{isMoodleSource ? "Live categories" : "Category slugs"}</div>
                  <div className="row-title">
                    {isMoodleSource ? settings?.moodle_category_count : (settings?.category_slugs || []).join(", ")}
                  </div>
                </div>
              </div>
              <div style={{ marginTop: 24, borderTop: "1px solid var(--border)", paddingTop: 24 }}>
                <div className="row-title" style={{ marginBottom: 4 }}>
                  Allowed company domains
                </div>
                <div className="row-subtitle" style={{ marginBottom: 16 }}>
                  Restrict signups to these verified email domains for corporate roles.
                </div>
                
                <div className="table-wrap" style={{ marginBottom: 16 }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Domain</th>
                        <th>Organization / Label</th>
                        <th style={{ width: 80 }}>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(settings?.allowed_domains || []).map((item) => (
                        <tr key={item.domain}>
                          <td className="mono" style={{ fontWeight: 600 }}>{item.domain}</td>
                          <td>
                            <Badge tone="accent">{item.label}</Badge>
                          </td>
                          <td>
                            <IconButton 
                              icon="trash" 
                              label="Delete domain" 
                              onClick={() => handleDeleteDomain(item.domain)}
                            />
                          </td>
                        </tr>
                      ))}
                      {(!settings?.allowed_domains || settings.allowed_domains.length === 0) && (
                        <tr>
                          <td colSpan="3" style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)' }}>
                            No allowed domains configured
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="toolbar" style={{ alignItems: "flex-end" }}>
                  <label className="field" style={{ flex: 1, maxWidth: 250 }}>
                    <span className="field__label">Label (e.g. Acme Corp)</span>
                    <input 
                      className="field__input" 
                      type="text" 
                      value={newDomainLabel}
                      onChange={(e) => setNewDomainLabel(e.target.value)}
                      placeholder="Company Name"
                    />
                  </label>
                  <label className="field" style={{ flex: 1, maxWidth: 250 }}>
                    <span className="field__label">Domain</span>
                    <input 
                      className="field__input" 
                      type="text" 
                      value={newDomain}
                      onChange={(e) => setNewDomain(e.target.value)}
                      placeholder="@company.com"
                    />
                  </label>
                  <Button tone="primary" onClick={handleAddDomain}>
                    + Add domain
                  </Button>
                </div>
              </div>
              {isMoodleSource && settings?.service_functions?.length ? (
                <div style={{ marginTop: 16 }}>
                  <div className="row-title" style={{ marginBottom: 10 }}>
                    Exposed Moodle functions
                  </div>
                  <div className="toolbar">
                    {settings.service_functions.map((name) => (
                      <Badge key={name} tone="neutral">
                        {name}
                      </Badge>
                    ))}
                  </div>
                </div>
              ) : null}
            </Panel>
          </section>
          )}
          {activeNav === "section-profile" && (
            <section id="section-profile">
              <ProfileSettingsTab
                session={session}
                activeTab={activeProfileTab}
                setActiveTab={(tab) => navigate(`/super-admin/profile?tab=${tab}`)}
              />
            </section>
          )}

        </div>
      </DashboardShell>

      <CategoryEditorModal
        open={categoryModal.open}
        item={categoryModal.item}
        admins={categoryAdmins}
        organizations={organizations}
        onClose={() => setCategoryModal({ open: false, item: null })}
        onSubmit={async (payload, isEdit) => {
          try {
            if (isEdit) {
              await updateCategory(categoryModal.item.id, payload);
              showToast("Category updated.", "success");
            } else {
              const res = await createCategory(payload);
              if (res.moodle_sync?.mock) {
                showToast("Category created locally (Moodle is in mock mode).", "warning");
              } else if (res.moodle_sync?.already_existed) {
                showToast("Category linked to existing Moodle category.", "info");
              } else {
                showToast("Category created and synced to Moodle.", "success");
              }
            }
            setCategoryModal({ open: false, item: null });
            await load();
          } catch (requestError) {
            showToast(getErrorMessage(requestError, "Unable to save category."), "error");
          }
        }}
      />

      <AdminEditorModal
        open={adminModal.open}
        item={adminModal.item}
        categories={dashboard.categories}
        onClose={() => setAdminModal({ open: false, item: null })}
        onSubmit={async (payload, isEdit) => {
          try {
            if (isEdit) {
              await updateAdmin(adminModal.item.id, payload);
              showToast("Admin updated.", "success");
            } else {
              await createAdmin(payload);
              showToast("Admin added.", "success");
            }
            setAdminModal({ open: false, item: null });
            await load();
          } catch (requestError) {
            showToast(getErrorMessage(requestError, "Unable to save admin."), "error");
          }
        }}
      />

      <TaskEditorModal
        open={taskModal.open}
        item={taskModal.item}
        learners={learnerUsers}
        categories={dashboard.categories}
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
      />
    </>
  );
}

function CategoryEditorModal({ open, item, admins, organizations = [], onClose, onSubmit }) {
  const isEdit = Boolean(item);
  const [form, setForm] = useState(CATEGORY_INITIAL);
  const [errors, setErrors] = useState({});
  const [slugTouched, setSlugTouched] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setForm(
      item
        ? {
            name: item.name || "",
            slug: item.slug || "",
            description: item.description || "",
            admin_user_id: item.admin_user_id || "",
            planned_courses: item.planned_courses || 0,
            status: item.status || "active",
            accent_color: item.accent_color || "#7C3AED",
            org_type: item.org_type || "college",
            organization_id: item.organization_id || "",
          }
        : CATEGORY_INITIAL
    );
    setErrors({});
    setSlugTouched(Boolean(item));
    setIsSubmitting(false);
  }, [item, open]);

  function updateField(field, value) {
    setForm((current) => {
      const next = { ...current, [field]: value };
      if (field === "name" && !slugTouched) {
        next.slug = value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
      }
      return next;
    });
    setErrors((current) => ({ ...current, [field]: "" }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (isSubmitting) return;

    const nextErrors = {};
    if (!form.name.trim()) {
      nextErrors.name = "Category name is required.";
    }
    if (!form.slug.trim()) {
      nextErrors.slug = "Slug is required.";
    }
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(
        {
          ...form,
          slug: form.slug.toLowerCase(),
          planned_courses: Number(form.planned_courses) || 0,
          admin_user_id: form.admin_user_id || null,
        },
        isEdit
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? "Edit Category" : "Add Category"}
      description="Create or update a learning category and assign its primary admin."
      footer={
        <>
          <Button tone="ghost" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button tone="primary" onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : isEdit ? "Save changes" : "Create Category"}
          </Button>
        </>
      }
    >
      <form className="form-stack" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field__label">Category name</span>
          <input
            className={`field__input ${errors.name ? "is-invalid" : ""}`}
            value={form.name}
            onChange={(event) => updateField("name", event.target.value)}
            required
          />
          {errors.name ? <span className="field__error">{errors.name}</span> : null}
        </label>
        <div className="field-grid">
          <label className="field">
            <span className="field__label">Slug / code</span>
            <input
              className={`field__input ${errors.slug ? "is-invalid" : ""}`}
              value={form.slug}
              onChange={(event) => {
                setSlugTouched(true);
                updateField("slug", event.target.value);
              }}
              required
            />
            {errors.slug ? <span className="field__error">{errors.slug}</span> : null}
          </label>
          <label className="field">
            <span className="field__label">Planned courses</span>
            <input
              className="field__input"
              type="number"
              min="0"
              value={form.planned_courses}
              onChange={(event) => updateField("planned_courses", event.target.value)}
            />
          </label>
        </div>
        <label className="field">
          <span className="field__label">Linked Organization</span>
          <select
            className="field__select"
            value={form.organization_id}
            onChange={(event) => updateField("organization_id", event.target.value)}
          >
            <option value="">No link (Generic)</option>
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name} ({org.type})
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field__label">Admin</span>
          <select
            className="field__select"
            value={form.admin_user_id}
            onChange={(event) => updateField("admin_user_id", event.target.value)}
          >
            <option value="">Assign later</option>
            {admins.map((admin) => (
              <option key={admin.id} value={admin.id}>
                {admin.full_name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field__label">Description</span>
          <textarea
            className="field__textarea"
            value={form.description}
            onChange={(event) => updateField("description", event.target.value)}
          />
        </label>
        <div className="field-grid">
          <label className="field">
            <span className="field__label">Accent color</span>
            <input
              className="field__input"
              value={form.accent_color}
              onChange={(event) => updateField("accent_color", event.target.value)}
            />
          </label>
          <div className="field">
            <span className="field__label">Status</span>
            <div className="radio-row">
              {["active", "draft"].map((option) => (
                <label className="radio-pill" key={option}>
                  <input
                    type="radio"
                    name="category-status"
                    checked={form.status === option}
                    onChange={() => updateField("status", option)}
                  />
                  {titleize(option)}
                </label>
              ))}
            </div>
          </div>
        </div>
        <div className="field">
          <span className="field__label">Organization Type</span>
          <div className="radio-row">
            {[
              ["college", "College / University"],
              ["company", "Corporate / Company"],
            ].map(([value, label]) => (
              <label className="radio-pill" key={value}>
                <input
                  type="radio"
                  name="org-type"
                  checked={form.org_type === value}
                  onChange={() => updateField("org_type", value)}
                />
                {label}
              </label>
            ))}
          </div>
        </div>
      </form>
    </Modal>
  );
}

function AdminEditorModal({ open, item, categories = [], onClose, onSubmit }) {
  const isEdit = Boolean(item);
  const [form, setForm] = useState(ADMIN_INITIAL);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    setForm(
      item
        ? {
            full_name: item.full_name || "",
            email: item.email || "",
            role: item.role || "category_admin",
            category_scope: item.category_scope || "ats",
            password: "",
            username: item.username || "",
          }
        : ADMIN_INITIAL
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
    if (!form.full_name.trim()) {
      nextErrors.full_name = "Full name is required.";
    }
    if (!form.email.trim() || !form.email.endsWith("@telite.io")) {
      nextErrors.email = "Email must use the @telite.io domain.";
    }
    if (!isEdit && !form.password.trim()) {
      nextErrors.password = "Temporary password is required.";
    }
    if (!form.username.trim()) {
      nextErrors.username = "Username is required.";
    }
    if (form.role === "category_admin" && !form.category_scope) {
      nextErrors.category_scope = "Select a category.";
    }
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      return;
    }

    const payload = {
      ...form,
      category_scope: form.role === "super_admin" ? null : form.category_scope,
      password: form.password || undefined,
    };

    await onSubmit(payload, isEdit);
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? "Edit Admin" : "Add Admin"}
      description="Super admins can create and update internal admin access."
      footer={
        <>
          <Button tone="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button tone="primary" onClick={handleSubmit}>
            {isEdit ? "Save changes" : "Add Admin"}
          </Button>
        </>
      }
    >
      <form className="form-stack" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field__label">Full name</span>
          <input
            className={`field__input ${errors.full_name ? "is-invalid" : ""}`}
            value={form.full_name}
            onChange={(event) => updateField("full_name", event.target.value)}
          />
          {errors.full_name ? <span className="field__error">{errors.full_name}</span> : null}
        </label>
        <div className="field-grid">
          <label className="field">
            <span className="field__label">Email</span>
            <input
              className={`field__input ${errors.email ? "is-invalid" : ""}`}
              value={form.email}
              onChange={(event) => updateField("email", event.target.value)}
              type="email"
            />
            {errors.email ? <span className="field__error">{errors.email}</span> : null}
          </label>
          <label className="field">
            <span className="field__label">Username</span>
            <input
              className={`field__input ${errors.username ? "is-invalid" : ""}`}
              value={form.username}
              onChange={(event) => updateField("username", event.target.value)}
            />
            {errors.username ? <span className="field__error">{errors.username}</span> : null}
          </label>
        </div>
        {!isEdit ? (
          <label className="field">
            <span className="field__label">Temporary password</span>
            <input
              className={`field__input ${errors.password ? "is-invalid" : ""}`}
              value={form.password}
              onChange={(event) => updateField("password", event.target.value)}
              type="password"
            />
            {errors.password ? <span className="field__error">{errors.password}</span> : null}
          </label>
        ) : null}
        <div className="field">
          <span className="field__label">Role</span>
          <div className="radio-row">
            {[
              ["super_admin", "Super Admin"],
              ["category_admin", "Category Admin"],
            ].map(([value, label]) => (
              <label className="radio-pill" key={value}>
                <input
                  type="radio"
                  name="admin-role"
                  checked={form.role === value}
                  onChange={() => updateField("role", value)}
                />
                {label}
              </label>
            ))}
          </div>
        </div>
        {form.role === "category_admin" ? (
          <label className="field">
            <span className="field__label">Category assignment</span>
            <select
              className={`field__select ${errors.category_scope ? "is-invalid" : ""}`}
              value={form.category_scope}
              onChange={(event) => updateField("category_scope", event.target.value)}
            >
              {categories.map((cat) => (
                <option key={cat.slug} value={cat.slug}>
                  {cat.name}
                </option>
              ))}
            </select>
            {errors.category_scope ? <span className="field__error">{errors.category_scope}</span> : null}
          </label>
        ) : null}
      </form>
    </Modal>
  );
}

function TaskEditorModal({ open, item, learners, categories = [], onClose, onSubmit }) {
  const isEdit = Boolean(item);
  const [form, setForm] = useState(TASK_INITIAL);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    const existingAssignee = item?.assigned_to_user_id || item?.assignment_scope || "all_new_learners";
    setForm(
      item
        ? {
            title: item.title || "",
            description: item.description || "",
            assignee: existingAssignee,
            category_slug: item.category_slug || "all",
            due_at: item.due_at || "",
            status: item.status || "pending",
            notes: item.notes || "",
          }
        : TASK_INITIAL
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
    if (!form.title.trim()) {
      nextErrors.title = "Task title is required.";
    }
    if (!form.assignee) {
      nextErrors.assignee = "Select who this task is assigned to.";
    }
    if (!form.due_at) {
      nextErrors.due_at = "Due date is required.";
    }
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      return;
    }

    const selectedLearner = learners.find((learner) => learner.id === form.assignee);
    const selectedScope = ALL_SCOPE_OPTIONS.find((option) => option.value === form.assignee);

    const payload = {
      title: form.title,
      description: form.description,
      assigned_label: selectedLearner?.full_name || selectedScope?.label || "All learners",
      assigned_to_user_id: selectedLearner?.id || null,
      assignment_scope: selectedLearner ? "individual" : form.assignee,
      category_slug: selectedLearner?.category_scope || form.category_slug,
      due_at: form.due_at,
      status: form.status,
      notes: form.notes,
      is_cross_category: true,
    };

    await onSubmit(payload, isEdit);
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? "Edit Task" : "Assign Cross-Category Task"}
      description="Create tasks that span categories, admins, or onboarding cohorts."
      footer={
        <>
          <Button tone="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button tone="primary" onClick={handleSubmit}>
            {isEdit ? "Save changes" : "Assign Task"}
          </Button>
        </>
      }
    >
      <form className="form-stack" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field__label">Task title</span>
          <input
            className={`field__input ${errors.title ? "is-invalid" : ""}`}
            value={form.title}
            onChange={(event) => updateField("title", event.target.value)}
          />
          {errors.title ? <span className="field__error">{errors.title}</span> : null}
        </label>
        <label className="field">
          <span className="field__label">Assign to</span>
          <select
            className={`field__select ${errors.assignee ? "is-invalid" : ""}`}
            value={form.assignee}
            onChange={(event) => updateField("assignee", event.target.value)}
          >
            {ALL_SCOPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
            {learners.map((learner) => (
              <option key={learner.id} value={learner.id}>
                {learner.full_name}
              </option>
            ))}
          </select>
          {errors.assignee ? <span className="field__error">{errors.assignee}</span> : null}
        </label>
        <div className="field-grid">
          <label className="field">
            <span className="field__label">Category scope</span>
            <select
              className="field__select"
              value={form.category_slug}
              onChange={(event) => updateField("category_slug", event.target.value)}
              disabled={Boolean(learners.find((learner) => learner.id === form.assignee))}
            >
              <option value="all">All</option>
              {categories.map((cat) => (
                <option key={cat.slug} value={cat.slug}>
                  {cat.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="field__label">Status</span>
            <select
              className="field__select"
              value={form.status}
              onChange={(event) => updateField("status", event.target.value)}
            >
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="overdue">Overdue</option>
            </select>
          </label>
        </div>
        <label className="field">
          <span className="field__label">Due date</span>
          <input
            className={`field__input ${errors.due_at ? "is-invalid" : ""}`}
            value={form.due_at}
            onChange={(event) => updateField("due_at", event.target.value)}
            type="date"
          />
          {errors.due_at ? <span className="field__error">{errors.due_at}</span> : null}
        </label>
        <label className="field">
          <span className="field__label">Description</span>
          <textarea
            className="field__textarea"
            value={form.description}
            onChange={(event) => updateField("description", event.target.value)}
          />
        </label>
        <label className="field">
          <span className="field__label">Notes</span>
          <textarea
            className="field__textarea"
            value={form.notes}
            onChange={(event) => updateField("notes", event.target.value)}
          />
        </label>
      </form>
    </Modal>
  );
}

function auditAccent(value) {
  if (value === "emerald") {
    return "#059669";
  }
  if (value === "blue") {
    return "#2563EB";
  }
  if (value === "violet") {
    return "#7C3AED";
  }
  if (value === "amber") {
    return "#F59E0B";
  }
  return "#DC2626";
}
