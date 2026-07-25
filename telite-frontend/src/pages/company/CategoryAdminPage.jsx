import React, { Component, useDeferredValue, useEffect, useMemo, useState, useCallback } from "react";
import { useNavigate, useParams, useLocation, useSearchParams } from "react-router-dom";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import {
  approveEnrollmentRequest,
  approveAssignmentSubmission,
  approveVerification,
  bulkUploadVerifications,
  createCourse,
  createTask,
  deleteCourse,
  deleteUser,
  downloadAssignmentSubmissionFile,
  getErrorMessage,
  fetchAssignmentVerifications,
  fetchCategoryGradingAnalytics,
  fetchCategoryQuizStatistics,
  manualEnroll,
  rejectEnrollmentRequest,
  rejectAssignmentSubmission,
  rejectVerification,
  reviewTask,
  updateCourse,
  updateTask,
  uploadCourseCover,
  deleteCourseCover,
} from "../../services/client";
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
import { ChartCanvas } from "../../components/common/charts";
import {
  formatMonthDate,
  formatDateTime,
  formatPercent,
  formatShortDate,
  getCompletionColor,
  getInitials,
  getScoreColor,
  titleize,
} from "../../utils/formatters";
import {
  getCourseEnrollmentDisabledReason,
  toggleEnrollmentCourseSelection,
} from "../../utils/enrollmentCourses";
import { useKpiPulse } from "../../hooks/useKpiPulse";
import { ActivityFeedTab, SettingsTab, ReportsTab, PalTrackerTab, TasksTab, ProfileSettingsTab } from "../../components/dashboard/CategoryAdminTabs";
import { useDashboardStore } from "../../store/dashboardStore";
import OverviewTab from "../../components/category-admin/OverviewTab";
import CoursesTab from "../../components/category-admin/CoursesTab";
import LearnersTab from "../../components/category-admin/LearnersTab";
import EnrollmentTab from "../../components/category-admin/EnrollmentTab";
import AssignmentVerificationTab from "../../components/category-admin/AssignmentVerificationTab";
import QuizAttemptsTab from "../../components/category-admin/QuizAttemptsTab";
import GradingTab from "../../components/category-admin/GradingTab";

const COURSE_INITIAL = {
  name: "",
  slug: "",
  description: "",
  tier: "Basic",
  status: "draft",
  module_count: 4,
  lessons_count: 8,
  hours: 12,
  modules: [],
  cover_image_url: "",
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

function formatDuration(seconds) {
  const total = Math.max(0, Number(seconds) || 0);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  if (hours) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "courses", label: "Course management" },
  { id: "learners", label: "Learners" },
  { id: "enrollment", label: "Enrollment" },
  { id: "assignment_verification", label: "Assignment Verification" },
  { id: "quiz_attempts", label: "Quiz Attempts" },

  { id: "pal", label: "PAL tracker" },
  { id: "grading", label: "Grading Analytics" },
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
  const [gradingAnalytics, setGradingAnalytics] = useState(null);
  const [gradingLoading, setGradingLoading] = useState(false);
  const [gradingFilters, setGradingFilters] = useState({ course: "", learner: "", type: "", status: "", grade: "", from: "", to: "", search: "" });
  const [assignmentQueue, setAssignmentQueue] = useState({ stats: {}, submissions: [] });
  const [assignmentLoading, setAssignmentLoading] = useState(false);
  const [assignmentFilters, setAssignmentFilters] = useState({ status: "", course_id: "", search: "" });
  const [reviewDrafts, setReviewDrafts] = useState({});
  const [quizStatistics, setQuizStatistics] = useState({ rows: [] });
  const [quizStatsLoading, setQuizStatsLoading] = useState(false);

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

  const learners = useMemo(() => dashboard?.learners?.rows || [], [dashboard]);
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

  const filteredGradingLearners = useMemo(() => {
    const rows = gradingAnalytics?.learner_grades || [];
    const search = gradingFilters.search.trim().toLowerCase();
    return rows.filter((row) => {
      if (gradingFilters.course && row.course_id !== gradingFilters.course) return false;
      if (gradingFilters.learner && row.learner_id !== gradingFilters.learner) return false;
      if (gradingFilters.grade && row.overall_grade !== gradingFilters.grade) return false;
      if (search && !`${row.learner_name} ${row.course}`.toLowerCase().includes(search)) return false;
      return true;
    });
  }, [gradingAnalytics, gradingFilters]);

  const filteredAssessmentDetails = useMemo(() => {
    const rows = gradingAnalytics?.assessment_details || [];
    const search = gradingFilters.search.trim().toLowerCase();
    const from = gradingFilters.from ? new Date(gradingFilters.from) : null;
    const to = gradingFilters.to ? new Date(`${gradingFilters.to}T23:59:59`) : null;
    return rows.filter((row) => {
      if (gradingFilters.course && row.course_id && row.course_id !== gradingFilters.course) return false;
      if (gradingFilters.learner && row.learner_id !== gradingFilters.learner) return false;
      if (gradingFilters.type && row.assessment_type !== gradingFilters.type) return false;
      if (gradingFilters.status && row.status !== gradingFilters.status) return false;
      if (gradingFilters.grade && row.grade !== gradingFilters.grade) return false;
      if (search && !`${row.learner_name} ${row.course}`.toLowerCase().includes(search)) return false;
      const stamp = row.submission_date ? new Date(row.submission_date) : null;
      if (from && stamp && stamp < from) return false;
      if (to && stamp && stamp > to) return false;
      return true;
    });
  }, [gradingAnalytics, gradingFilters]);

  useEffect(() => {
    fetchDashboardData(slug);
  }, [slug, fetchDashboardData]);

  const derivedActiveTab = searchParams.get("tab") || "overview";
  const derivedSegment = location.pathname.replace(/\/$/, "").split("/").pop();
  const resolvedTab = derivedSegment === "activity" ? "activity" : derivedSegment === "settings" ? "settings" : derivedSegment === "profile" ? "profile" : derivedActiveTab;

  useEffect(() => {
    async function fetchGradingAnalytics() {
      if (resolvedTab === "grading") {
        setGradingLoading(true);
        try {
          setGradingAnalytics(await fetchCategoryGradingAnalytics(slug));
        } catch (err) {
          console.error("Failed to fetch grading analytics:", err);
          showToast(getErrorMessage(err, "Unable to load grading analytics."), "error");
        } finally {
          setGradingLoading(false);
        }
      }
    }
    fetchGradingAnalytics();
  }, [resolvedTab, showToast, slug]);

  useEffect(() => {
    if (resolvedTab !== "grading") return undefined;
    const timer = window.setInterval(async () => {
      try {
        setGradingAnalytics(await fetchCategoryGradingAnalytics(slug));
      } catch (err) {
        console.error("Failed to refresh grading analytics:", err);
      }
    }, 30000);
    return () => window.clearInterval(timer);
  }, [resolvedTab, slug]);

  const loadAssignmentQueue = useCallback(async () => {
    setAssignmentLoading(true);
    try {
      const data = await fetchAssignmentVerifications(slug, {
        status: assignmentFilters.status || undefined,
        course_id: assignmentFilters.course_id || undefined,
        search: assignmentFilters.search || undefined,
      });
      setAssignmentQueue(data);
    } catch (err) {
      showToast(getErrorMessage(err, "Unable to load assignment verifications."), "error");
    } finally {
      setAssignmentLoading(false);
    }
  }, [assignmentFilters.course_id, assignmentFilters.search, assignmentFilters.status, showToast, slug]);

  useEffect(() => {
    if (resolvedTab === "assignment_verification") {
      loadAssignmentQueue();
    }
  }, [resolvedTab, loadAssignmentQueue]);

  const loadQuizStatistics = useCallback(async () => {
    setQuizStatsLoading(true);
    try {
      setQuizStatistics(await fetchCategoryQuizStatistics(slug));
    } catch (err) {
      showToast(getErrorMessage(err, "Unable to load quiz attempt statistics."), "error");
    } finally {
      setQuizStatsLoading(false);
    }
  }, [showToast, slug]);

  useEffect(() => {
    if (resolvedTab === "quiz_attempts") {
      loadQuizStatistics();
    }
  }, [resolvedTab, loadQuizStatistics]);

  async function handleAssignmentReview(submissionId, action) {
    const feedback = reviewDrafts[submissionId] || "";
    try {
      if (action === "approve") {
        await approveAssignmentSubmission(submissionId, feedback);
        showToast("Assignment approved.", "success");
      } else {
        await rejectAssignmentSubmission(submissionId, feedback);
        showToast("Assignment rejected.", "warning");
      }
      await loadAssignmentQueue();
      if (resolvedTab === "grading") {
        setGradingAnalytics(await fetchCategoryGradingAnalytics(slug));
      }
    } catch (err) {
      showToast(getErrorMessage(err, `Unable to ${action} assignment.`), "error");
    }
  }

  async function handleAssignmentDownload(event, submission, file) {
    event.preventDefault();
    event.stopPropagation();
    try {
      const assetId = file?.asset_id || file?.file_path || null;
      const { blob, filename } = await downloadAssignmentSubmissionFile(submission.id, assetId);
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      showToast(getErrorMessage(err, "Unable to download assignment file."), "error");
    }
  }

  const loadVerifications = useCallback(async () => {
    await fetchVerificationsData(slug);
  }, [fetchVerificationsData, slug]);

  useEffect(() => {
    if (resolvedTab === "verifications") {
      loadVerifications();
    }
  }, [resolvedTab, loadVerifications]);

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
    const nextStatus = explicitStatus || (["approved", "completed"].includes(task.status) ? "assigned" : "approved");
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

  async function handleReviewTask(task, action) {
    try {
      await reviewTask(task.id, { action, review_notes: "" });
      showToast(action === "approve" ? "Task approved." : "Revision requested.", "success");
      await load();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to review task."), "error");
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
        { id: "question_banks", label: "Question banks", icon: "database" },
        { id: "announcements", label: "Announcements", icon: "bell" },
        { id: "learners", label: "Learners", icon: "users", badge: String(dashboard.kpis.active_learners), badgeTone: "brand" },
        { id: "enrollment", label: "Enrollment", icon: "enrollments", badge: String(dashboard.kpis.pending_enrollment), badgeTone: "warn" },
        { id: "verifications", label: "Verifications", icon: "shield", badge: String(dashboard.kpis.pending_verifications || 0), badgeTone: "warn" },
        { id: "assignment_verification", label: "Assignment verification", icon: "task", badge: String(assignmentQueue?.stats?.pending || 0), badgeTone: "warn" },
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
      items: [
        { id: "settings", label: "Settings", icon: "settings" },

      ],
    },
  ];

  const currentCourse = (dashboard?.courses || []).find((course) => course.id === detailLearner?.current_course_id);
  const pendingTasks = (dashboard?.tasks || []).filter((task) => !["approved", "completed"].includes(task.status));
  const completedTasks = (dashboard?.tasks || []).filter((task) => ["approved", "completed"].includes(task.status));
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
      assignment_verification: "assignment_verification",
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
        variant={dashboard.category?.slug || slug}
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
          if (item.id === "question_banks") {
            navigate(`/categories/${slug}/question-banks`);
            return;
          }
          if (item.id === "announcements") {
            navigate(`/categories/${slug}/announcements`);
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
            assignment_verification: "assignment_verification",
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
                    📥 All Reports (CSV)
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
                    📄 All Reports (PDF)
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
            <OverviewTab 
              dashboard={dashboard}
              labels={labels}
              handleTabChange={handleTabChange}
              handleApprove={handleApprove}
              handleReject={handleReject}
              handleQuickEnroll={handleQuickEnroll}
              manualQuickInput={manualQuickInput}
              setManualQuickInput={setManualQuickInput}
              quickError={quickError}
              setQuickError={setQuickError}
              learners={learners}
              totalLearners={totalLearners}
              setDetailLearner={setDetailLearner}
              setDeleteLearnerId={setDeleteLearnerId}
              deleteLearnerId={deleteLearnerId}
              handleDeleteLearner={handleDeleteLearner}
              toggleTask={toggleTask}
              setTaskModal={setTaskModal}
              navigate={navigate}
              slug={slug}
              kpiPulse={kpiPulse}
            />
          ) : null}

          {activeTab === "courses" ? (
            <CoursesTab 
              dashboard={dashboard}
              courseSearch={courseSearch}
              setCourseSearch={setCourseSearch}
              setCourseModal={setCourseModal}
              expandedCourseId={expandedCourseId}
              setExpandedCourseId={setExpandedCourseId}
              setDeleteCourseId={setDeleteCourseId}
              deleteCourseId={deleteCourseId}
              handleDeleteCourse={handleDeleteCourse}
              navigate={navigate}
              slug={slug}
            />
          ) : null}

          {activeTab === "learners" ? (
            <LearnersTab 
              labels={labels}
              learnerSearch={learnerSearch}
              setLearnerSearch={setLearnerSearch}
              learnerFilter={learnerFilter}
              setLearnerFilter={setLearnerFilter}
              setLearnerModal={setLearnerModal}
              paginatedLearners={paginatedLearners}
              learnerPage={learnerPage}
              pageCount={pageCount}
              setLearnerPage={setLearnerPage}
              setDetailLearner={setDetailLearner}
              setDeleteLearnerId={setDeleteLearnerId}
              deleteLearnerId={deleteLearnerId}
              handleDeleteLearner={handleDeleteLearner}
              dashboard={dashboard}
            />
          ) : null}

          {activeTab === "enrollment" ? (
            <EnrollmentTab 
              dashboard={dashboard}
              labels={labels}
              handleApprove={handleApprove}
              handleReject={handleReject}
              manualForm={manualForm}
              setManualForm={setManualForm}
              manualErrors={manualErrors}
              setManualErrors={setManualErrors}
              manualSuccess={manualSuccess}
              submitManualEnrollment={submitManualEnrollment}
            />
          ) : null}

          {activeTab === "assignment_verification" ? (
            <AssignmentVerificationTab 
              assignmentQueue={assignmentQueue}
              assignmentLoading={assignmentLoading}
              assignmentFilters={assignmentFilters}
              setAssignmentFilters={setAssignmentFilters}
              loadAssignmentQueue={loadAssignmentQueue}
              handleAssignmentReview={handleAssignmentReview}
              handleAssignmentDownload={handleAssignmentDownload}
              reviewDrafts={reviewDrafts}
              setReviewDrafts={setReviewDrafts}
              dashboard={dashboard}
            />
          ) : null}


          {activeTab === "quiz_attempts" ? (
            <QuizAttemptsTab 
              quizStatistics={quizStatistics}
              quizStatsLoading={quizStatsLoading}
              loadQuizStatistics={loadQuizStatistics}
            />
          ) : null}



          {activeTab === "pal" ? (
            <PalTrackerTab dashboard={dashboard} labels={labels} palExpanded={palExpanded} setPalExpanded={setPalExpanded} />
          ) : null}

          {activeTab === "grading" ? (
            <GradingTab 
              gradingAnalytics={gradingAnalytics}
              gradingLoading={gradingLoading}
              gradingFilters={gradingFilters}
              setGradingFilters={setGradingFilters}
              filteredGradingLearners={filteredGradingLearners}
              filteredAssessmentDetails={filteredAssessmentDetails}
            />
          ) : null}
          {activeTab === "tasks" ? (
            <TasksTab pendingTasks={pendingTasks} completedTasks={completedTasks} toggleTask={toggleTask} setTaskModal={setTaskModal} onReviewTask={handleReviewTask} />
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
        onOpenBuilder={(id) => {
          setCourseModal({ open: false, item: null });
          navigate(`/categories/${slug}/builder/${id}`);
        }}
        onSubmit={async (payload, isEdit, coverFile) => {
          try {
            if (isEdit) {
              await updateCourse(slug, courseModal.item.id, payload);
              if (coverFile) {
                await uploadCourseCover(slug, courseModal.item.id, coverFile);
              }
              showToast("Course updated.", "success");
            } else {
              const newCourse = await createCourse(slug, payload);
              if (coverFile && newCourse?.id) {
                await uploadCourseCover(slug, newCourse.id, coverFile);
              }
              showToast("Course created.", "success");
            }
            setCourseModal({ open: false, item: null });
            await load();
          } catch (requestError) {
            if (requestError.response?.status === 409) {
              throw requestError;
            }
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
            <div className="grid-2" style={{ marginTop: 24 }}>
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


function CourseEditorModal({ open, item, onClose, onSubmit, onOpenBuilder }) {
  const isEdit = Boolean(item);
  const [form, setForm] = useState(COURSE_INITIAL);
  const [errors, setErrors] = useState({});
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadError, setUploadError] = useState("");

  useEffect(() => {
    setForm(
      item
        ? {
            name: item.name,
            slug: item.slug,
            description: item.description,
            tier: item.tier,
            status: item.status,
            cover_image_url: item.cover_image_url || "",
          }
        : COURSE_INITIAL
    );
    setSelectedFile(null);
    setUploadError("");
    setErrors({});
  }, [item, open]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: "" }));
  }

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const ext = file.name.split('.').pop().toLowerCase();
    if (!["jpg", "jpeg", "png", "webp"].includes(ext)) {
      setUploadError("Invalid format. Only JPG, JPEG, PNG, and WEBP are supported.");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setUploadError("File is too large. Maximum size is 5 MB.");
      return;
    }

    setUploadError("");
    setSelectedFile(file);
  };

  const handleRemoveImage = async () => {
    setSelectedFile(null);
    setUploadError("");
    if (isEdit && form.cover_image_url) {
      try {
        await deleteCourseCover(item.category_slug || item.slug, item.id);
        updateField("cover_image_url", "");
      } catch (err) {
        setUploadError("Failed to remove cover image.");
      }
    }
  };

  async function handleSubmit(event) {
    event.preventDefault();
    const nextErrors = {};
    if (!form.name.trim()) nextErrors.name = "Course name is required.";
    if (!form.description.trim()) nextErrors.description = "Description is required.";
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      return;
    }
    try {
      await onSubmit(
        {
          name: form.name,
          slug: form.slug || form.name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
          description: form.description,
          tier: form.tier,
          status: form.status,
          module_count: form.module_count,
          lessons_count: form.lessons_count,
          hours: form.hours,
          modules: form.modules,
          cover_image_url: form.cover_image_url,
        },
        isEdit,
        selectedFile
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
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? "Course Settings" : "Create New Course"}
      description={isEdit ? "Manage metadata and structure." : "Initialize a new course shell."}
      width={640}
      footer={
        <>
          <Button tone="ghost" onClick={onClose}>Cancel</Button>
          <Button tone="primary" onClick={handleSubmit}>{isEdit ? "Save Changes" : "Create Course"}</Button>
        </>
      }
    >
      <form onSubmit={handleSubmit}>
        <div className="form-section">
          <h3 className="form-section__title">1. Basic Information</h3>
          <div className="form-stack">
            <label className="field">
              <span className="field__label">Course Name</span>
              <input className={`field__input ${errors.name ? "is-invalid" : ""}`} value={form.name} onChange={(event) => updateField("name", event.target.value)} placeholder="e.g. Introduction to Python" />
              {errors.name ? <span className="field__error">{errors.name}</span> : null}
            </label>
            <label className="field">
              <span className="field__label">Description</span>
              <input className={`field__input ${errors.description ? "is-invalid" : ""}`} value={form.description} onChange={(event) => updateField("description", event.target.value)} placeholder="Short summary of the course..." />
              {errors.description ? <span className="field__error">{errors.description}</span> : null}
            </label>

            <div className="field">
              <span className="field__label">Course Cover Image</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', border: '1px dashed var(--border)', borderRadius: '6px', padding: '12px', background: 'var(--surface-raised)' }}>
                {(form.cover_image_url || selectedFile) && (
                  <div style={{ position: 'relative', width: '200px', height: '112.5px', borderRadius: '4px', overflow: 'hidden', border: '1px solid var(--border)' }}>
                    <img
                      src={selectedFile ? URL.createObjectURL(selectedFile) : form.cover_image_url}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      alt="Cover Preview"
                    />
                  </div>
                )}
                
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <label className="button button--small button--secondary" style={{ cursor: 'pointer', display: 'inline-flex', margin: 0 }}>
                    {form.cover_image_url || selectedFile ? "Replace Image" : "Upload Image"}
                    <input
                      type="file"
                      accept=".jpg,.jpeg,.png,.webp"
                      style={{ display: 'none' }}
                      onChange={handleFileChange}
                    />
                  </label>
                  
                  {(form.cover_image_url || selectedFile) && (
                    <Button tone="ghost" size="small" onClick={handleRemoveImage}>
                      Remove
                    </Button>
                  )}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Recommended: 1280 × 720 (16:9) • Max: 5 MB • Formats: JPG, JPEG, PNG, WEBP
                </div>
                {uploadError && <span className="field__error">{uploadError}</span>}
              </div>
            </div>

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
          </div>
        </div>

        {isEdit && (
          <>
            <div className="form-section">
              <h3 className="form-section__title">2. Course Statistics</h3>
              <div className="grid-4">
                <div style={{ height: "80px" }}>
                  <StatCard label="Modules" value={item?.module_count || 0} />
                </div>
                <div style={{ height: "80px" }}>
                  <StatCard label="Lessons" value={item?.lessons_count || 0} />
                </div>
                <div style={{ height: "80px" }}>
                  <StatCard label="Blocks" value={item?.blocks_count || 0} />
                </div>
                <div style={{ height: "80px" }}>
                  <StatCard label="Enrollments" value={item?.enrolled_count || 0} />
                </div>
              </div>
            </div>

            <div className="form-section">
              <h3 className="form-section__title">3. Builder Access</h3>
              <div className="soft-card soft-card--tinted" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div className="row-title">Course Builder</div>
                  <div className="row-subtitle">Manage modules, lessons, and interactive blocks.</div>
                </div>
                <Button tone="primary" type="button" onClick={() => onOpenBuilder(item.id)}>Open Course Builder</Button>
              </div>
            </div>

            <div className="form-section">
              <h3 className="form-section__title">4. Metadata</h3>
              <div className="grid-3" style={{ fontSize: "13px" }}>
                <div>
                  <div style={{ color: "var(--text-muted)", marginBottom: "4px" }}>Created Date</div>
                  <div className="mono">{item?.created_at ? formatShortDate(item.created_at) : "Just now"}</div>
                </div>
                <div>
                  <div style={{ color: "var(--text-muted)", marginBottom: "4px" }}>Updated Date</div>
                  <div className="mono">{item?.updated_at ? formatShortDate(item.updated_at) : "Just now"}</div>
                </div>
                <div>
                  <div style={{ color: "var(--text-muted)", marginBottom: "4px" }}>Publish Status</div>
                  <div><Badge tone={item?.status === "active" ? "success" : "neutral"}>{titleize(item?.status || "draft")}</Badge></div>
                </div>
              </div>
            </div>
          </>
        )}
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
            {courses.map((course) => {
              const disabledReason = getCourseEnrollmentDisabledReason(course);
              return (
                <label className={`radio-pill ${disabledReason ? "is-disabled" : ""}`} key={course.id} title={disabledReason || undefined}>
                  <input
                    type="checkbox"
                    disabled={Boolean(disabledReason)}
                    checked={form.course_ids.includes(course.id)}
                    onChange={() =>
                      updateField(
                        "course_ids",
                        toggleEnrollmentCourseSelection(form.course_ids, course)
                      )
                    }
                  />
                  <span>{course.name}</span>
                  {disabledReason ? <span className="field__help">{disabledReason}</span> : null}
                </label>
              );
            })}
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

