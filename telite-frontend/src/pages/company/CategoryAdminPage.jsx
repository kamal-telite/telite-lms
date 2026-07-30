import React, { useDeferredValue, useEffect, useMemo, useState, useCallback } from "react";
import { useNavigate, useParams, useLocation, useSearchParams } from "react-router-dom";
import {
  approveEnrollmentRequest,
  approveAssignmentSubmission,
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
  reviewTask,
  updateCourse,
  updateTask,
  uploadCourseCover,
} from "../../services/client";
import { DashboardShell, TabBar, ProfileDropdown } from "../../layouts/DashboardLayout";
import {
  Avatar,
  Button,
  ErrorState,
  LoadingState,
  Modal,
  useToast,
} from "../../components/common/ui";
import {
  formatShortDate,
  getInitials,
  getScoreColor,
  titleize,
} from "../../utils/formatters";
import { useKpiPulse } from "../../hooks/useKpiPulse";
import { ActivityFeedTab, SettingsTab, ReportsTab, PalTrackerTab, TasksTab, ProfileSettingsTab } from "../../components/dashboard/CategoryAdminTabs";
import { useDashboardStore } from "../../store/dashboardStore";
import { ErrorBoundary, CourseEditorModal, LearnerEditorModal, TaskAssignModal } from "../../features/admin/category/dashboard-shell/Dialogs";
import { LEARNER_INITIAL, tabs, buildCategoryAdminNavGroups } from "../../features/admin/category/dashboard-shell/constants";
import { exportCategoryCsv, exportCategoryPdf } from "../../features/admin/category/dashboard-shell/exportUtils";
import OverviewTab from "../../components/category-admin/OverviewTab";
import CoursesTab from "../../components/category-admin/CoursesTab";
import LearnersTab from "../../components/category-admin/LearnersTab";
import EnrollmentTab from "../../components/category-admin/EnrollmentTab";
import AssignmentVerificationTab from "../../components/category-admin/AssignmentVerificationTab";
import QuizAttemptsTab from "../../components/category-admin/QuizAttemptsTab";
import GradingTab from "../../components/category-admin/GradingTab";

function CategoryAdminPageContent({ session, onLogout, children }) {
  const navigate = useNavigate();
  const { slug = "ats" } = useParams();
  const { showToast } = useToast();
  const { 
    dashboard, 
    dashboardLoading: loading, 
    dashboardError: error, 
    fetchDashboardData,
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

  const navGroups = buildCategoryAdminNavGroups({
    kpis: dashboard?.kpis || {},
    tasks: dashboard?.tasks || [],
    assignmentQueueStats: assignmentQueue?.stats || {},
  });

  const currentCourse = (dashboard?.courses || []).find((course) => course.id === detailLearner?.current_course_id);
  const pendingTasks = (dashboard?.tasks || []).filter((task) => !["approved", "completed"].includes(task.status));
  const completedTasks = (dashboard?.tasks || []).filter((task) => ["approved", "completed"].includes(task.status));
  const palCards = dashboard?.pal?.leaderboard ? [...dashboard.pal.leaderboard] : [];
  // eslint-disable-next-line no-unused-vars -- retained from the previous PAL-card derivation for parity.
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
    activeTab = searchParams.get("tab") || "general";
  } else if (currentSegment === "announcements") {
    activeNav = "announcements";
    activeTab = "overview";
  } else if (currentSegment === "question-banks") {
    activeNav = "question_banks";
    activeTab = "overview";
  } else {
    const mapped = {
      overview: "dashboard",
      courses: "courses",
      learners: "learners",
      enrollment: "enrollment",
      pal: "pal",
      tasks: "tasks",
      reports: "reports",
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
                      exportCategoryCsv({ activeTab, dashboard, learners, palCards });
                      showToast("CSV exported successfully!", "success");
                    } catch (err) {
                      showToast("Export failed: " + err.message, "error");
                    }
                  }}>
                    ðŸ“¥ All Reports (CSV)
                  </button>
                  <button type="button" onClick={() => {
                    setExportOpen(false);
                    try {
                      exportCategoryPdf({ activeTab, dashboard, learners, palCards });
                      showToast("PDF exported successfully!", "success");
                    } catch (err) {
                      showToast("PDF export failed: " + err.message, "error");
                    }
                  }}>
                    ðŸ“„ All Reports (PDF)
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
                navigate(`/categories/${slug}/admin/profile?tab=general`);
              }
            }} />
          </>
        }
        tabBar={
        !["activity", "settings", "announcements", "question_banks"].includes(activeNav)
          ? <TabBar tabs={tabs} activeTab={activeTab} onChange={handleTabChange} />
          : null
      }
      >
        {children ?? (
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
              slug={slug}
              setActiveTab={(id) => navigate(`/categories/${slug}/admin/profile?tab=${id}`)} 
              onClose={() => navigate(`/categories/${slug}/admin`)}
            />
          ) : null}

          </div>
        )}
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


export default function CategoryAdminPage(props) {
  return (
    <ErrorBoundary>
      <CategoryAdminPageContent {...props} />
    </ErrorBoundary>
  );
}

