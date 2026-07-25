import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useLocation, useSearchParams } from "react-router-dom";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import {
  approveBatchEnrollments,
  approveEnrollmentRequest,
  approveVerification,
  bulkUploadVerifications,
  inviteAdmin,
  createCategory,
  deleteCategory,
  deleteUser,
  addAllowedDomain,
  removeAllowedDomain,
  getErrorMessage,
  rejectEnrollmentRequest,
  rejectVerification,
  updateAdmin,
  updateCategory,
} from "../../services/client";
import { ChartCanvas } from "../../components/common/charts";
import { DashboardShell, SectionTitle, ProfileDropdown } from "../../layouts/DashboardLayout";
import { ProfileSettingsTab } from "../../components/dashboard/CategoryAdminTabs";

import { BrandingSettingsTab } from "../../components/dashboard/BrandingSettingsTab";

import { useSuperAdminStore } from "../../store/dashboardStore";
import OverviewSection from "../../components/super-admin/OverviewSection";
import CategoriesSection from "../../components/super-admin/CategoriesSection";
import PALSection from "../../components/super-admin/PALSection";
import AdminSection from "../../components/super-admin/AdminSection";
import EnrollmentsSection from "../../components/super-admin/EnrollmentsSection";
import VerificationsSection from "../../components/super-admin/VerificationsSection";
import GradingSection from "../../components/super-admin/GradingSection";
import AuditSection from "../../components/super-admin/AuditSection";
import UsersSection from "../../components/super-admin/UsersSection";
import AnalyticsSection from "../../components/super-admin/AnalyticsSection";
import SettingsSection from "../../components/super-admin/SettingsSection";
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
  formatPercent,
  formatShortDate,
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
  category_scope: "",
  password: "",
  username: "",
};



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
  } = useSuperAdminStore();
  const isMoodleSource = false;
  const [exportOpen, setExportOpen] = useState(false);
  const [categoryModal, setCategoryModal] = useState({ open: false, item: null });
  const [adminModal, setAdminModal] = useState({ open: false, item: null });
  const [categoryDeleteId, setCategoryDeleteId] = useState(null);
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
  const [gradingAnalytics, setGradingAnalytics] = useState(null);
  const [gradingLoading, setGradingLoading] = useState(false);

  const kpiPulse = useKpiPulse(dashboard?.kpis || {});

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
          { id: "section-bulk-enrollment", label: "Bulk Enrollment", icon: "upload" },
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
      ],
    },
    {
      label: "Reports",
      items: [
        { id: "section-pal", label: "PAL performance", icon: "leaderboard" },
        { id: "section-grading", label: "Grading Analytics", icon: "analytics" },
        { id: "section-audit", label: "Audit log", icon: "reports" },
      ],
    },
    {
      label: "System",
      items: [
        { id: "section-settings", label: "Settings", icon: "settings" },
        { id: "section-branding", label: "Branding", icon: "brush" }
      ],
    },
  ];

  const categoryAdmins = users.filter((user) => user.role === "category_admin");

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
  }, [load]);

  useEffect(() => {
    async function fetchGradingAnalytics() {
      if (activeNav === "section-grading") {
        setGradingLoading(true);
        try {
          const response = await fetch("/api/dashboard/super-admin/grading-analytics");
          if (response.ok) {
            const data = await response.json();
            setGradingAnalytics(data);
          }
        } catch (err) {
          console.error("Failed to fetch grading analytics:", err);
        } finally {
          setGradingLoading(false);
        }
      }
    }
    fetchGradingAnalytics();
  }, [activeNav]);

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

  async function handleAddDomain() {
    if (!newDomain.trim() || !newDomainLabel.trim()) {
      showToast("Both domain and label are required.", "warning");
      return;
    }
    const domainToAdd = newDomain.startsWith("@") ? newDomain : `@${newDomain}`;
    
    try {
      const added = await addAllowedDomain({ domain: domainToAdd, label: newDomainLabel });
      useSuperAdminStore.setState((prev) => ({
        settings: {
          ...prev.settings,
          allowed_domains: [...(prev.settings?.allowed_domains || []), added]
        }
      }));
      setNewDomain("");
      setNewDomainLabel("");
      showToast("Domain added successfully.", "success");
    } catch (err) {
      showToast(getErrorMessage(err) || "Failed to add domain.", "error");
    }
  }

  async function handleDeleteDomain(domainToRemove) {
    try {
      await removeAllowedDomain(domainToRemove);
      useSuperAdminStore.setState((prev) => ({
        settings: {
          ...prev.settings,
          allowed_domains: (prev.settings?.allowed_domains || []).filter(d => d.domain !== domainToRemove)
        }
      }));
      showToast("Domain removed successfully.", "success");
    } catch (err) {
      showToast(getErrorMessage(err) || "Failed to remove domain.", "error");
    }
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
        subtitle="Telite Systems · All categories"
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
                    📥 All Reports (CSV)
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
                    📄 All Reports (PDF)
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
            <OverviewSection 
              dashboard={dashboard}
              kpiPulse={kpiPulse}
              handleApprove={handleApprove}
              handleReject={handleReject}
            />
          )}

          {activeNav === "section-categories" && (
            <CategoriesSection 
              dashboard={dashboard}
              setCategoryModal={setCategoryModal}
              setCategoryDeleteId={setCategoryDeleteId}
              categoryDeleteId={categoryDeleteId}
              handleDeleteCategory={handleDeleteCategory}
              navigate={navigate}
              showToast={showToast}
            />
          )}

          {activeNav === "section-pal" && (
            <PALSection 
              dashboard={dashboard}
              isMoodleSource={isMoodleSource}
              navigate={navigate}
            />
          )}

          {activeNav === "section-admin" && (
            <AdminSection 
              dashboard={dashboard}
              isMoodleSource={isMoodleSource}
              setAdminModal={setAdminModal}
            />
          )}

          {activeNav === "section-enrollments" && (
            <EnrollmentsSection 
              dashboard={dashboard}
              isMoodleSource={isMoodleSource}
              handleApprove={handleApprove}
              handleReject={handleReject}
              handleApproveAll={handleApproveAll}
              showToast={showToast}
            />
          )}

          {activeNav === "section-verifications" && (
            <VerificationsSection 
              verifications={verifications}
              bulkFile={bulkFile}
              bulkLoading={bulkLoading}
              bulkResult={bulkResult}
              setBulkFile={setBulkFile}
              handleBulkUpload={handleBulkUpload}
              handleVerification={handleVerification}
            />
          )}

          {activeNav === "section-grading" && (
            <GradingSection 
              gradingAnalytics={gradingAnalytics}
              gradingLoading={gradingLoading}
            />
          )}

          {activeNav === "section-audit" && (
            <AuditSection 
              dashboard={dashboard}
              isMoodleSource={isMoodleSource}
              visibleAudit={visibleAudit}
              expandedAudit={expandedAudit}
              setExpandedAudit={setExpandedAudit}
            />
          )}

          {activeNav === "section-users" && (
            <UsersSection 
              users={users}
              isMoodleSource={isMoodleSource}
              userFilter={userFilter}
              setUserFilter={setUserFilter}
              userQuery={userQuery}
              setUserQuery={setUserQuery}
              filteredUsers={filteredUsers}
              setUserDeleteId={setUserDeleteId}
              userDeleteId={userDeleteId}
              handleDeleteUser={handleDeleteUser}
              showToast={showToast}
            />
          )}

          {activeNav === "section-analytics" && (
            <AnalyticsSection 
              dashboard={dashboard}
              isMoodleSource={isMoodleSource}
            />
          )}

          {activeNav === "section-settings" && (
            <SettingsSection 
              settings={settings}
              isMoodleSource={isMoodleSource}
              newDomain={newDomain}
              newDomainLabel={newDomainLabel}
              setNewDomain={setNewDomain}
              setNewDomainLabel={setNewDomainLabel}
              handleAddDomain={handleAddDomain}
              handleDeleteDomain={handleDeleteDomain}
            />
          )}

          {activeNav === "section-branding" && (
            <section id="section-branding">
              <BrandingSettingsTab dashboard={dashboard} organizations={organizations} session={session} />
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
            if (requestError.response?.status === 409) {
              throw requestError;
            }
            showToast(getErrorMessage(requestError, "Unable to save category."), "error");
          }
        }}
      />

      <AdminEditorModal
        open={adminModal.open}
        item={adminModal.item}
        categories={dashboard.categories}
        allowedDomains={dashboard?.settings?.system?.allowed_domains || []}
        onClose={() => setAdminModal({ open: false, item: null })}
        onSubmit={async (payload, isEdit) => {
          try {
            if (isEdit) {
              await updateAdmin(adminModal.item.id, payload);
              showToast("Admin updated.", "success");
            } else {
              await inviteAdmin(payload);
              showToast("Admin invited.", "success");
            }
            setAdminModal({ open: false, item: null });
            await load();
          } catch (requestError) {
            showToast(getErrorMessage(requestError, "Unable to save admin."), "error");
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
    } catch (err) {
      if (err.response?.status === 409 && err.response?.data?.detail) {
        const d = err.response.data.detail;
        if (d.field) {
          setErrors({ [d.field]: d.message });
        } else {
          setErrors({ name: d.message || "A conflict occurred." });
        }
      }
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

function AdminEditorModal({ open, item, categories = [], allowedDomains = [], onClose, onSubmit }) {
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
    
    const emailDomain = form.email.split('@')[1] ? ('@' + form.email.split('@')[1]) : "";
    if (!form.email.trim() || (allowedDomains.length > 0 && !allowedDomains.map(d => d.domain.toLowerCase()).includes(emailDomain.toLowerCase()))) {
      nextErrors.email = allowedDomains.length > 0 ? `Email must use an allowed domain for your organization: ${allowedDomains.map(d => d.domain).join(", ")}` : "Invalid email address.";
    }
    
    if (isEdit && !form.username.trim()) {
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
      title={isEdit ? "Edit Admin" : "Invite Admin"}
      description="Super admins can invite internal admins and assign them to specific categories (e.g. IoT)."
      footer={
        <>
          <Button tone="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button tone="primary" onClick={handleSubmit}>
            {isEdit ? "Save changes" : "Send Invite"}
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
          {isEdit ? (
            <label className="field">
              <span className="field__label">Username</span>
              <input
                className={`field__input ${errors.username ? "is-invalid" : ""}`}
                value={form.username}
                onChange={(event) => updateField("username", event.target.value)}
              />
              {errors.username ? <span className="field__error">{errors.username}</span> : null}
            </label>
          ) : null}
        </div>

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
              <option value="" disabled>
                Choose category...
              </option>
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


