import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  fetchMyAnnouncements,
  markAnnouncementRead,
  startTask,
  submitTaskWork,
} from "../../services/client";
import { api, getErrorMessage } from "../../services/client";
import { DashboardShell, ProfileDropdown } from "../../layouts/DashboardLayout";
import {
  Badge,
  Button,
  ErrorState,
  LoadingState,
  useToast,
} from "../../components/common/ui";
import { formatPercent, getInitials, titleize } from "../../utils/formatters";
import { useLearnerStore } from "../../store/learnerStore";
import { LearnerPlayer } from "../../components/player/LearnerPlayer";

// Extracted Components
import { NotificationDrawer } from "../../components/learner/NotificationDrawer";
import { DashboardSection } from "../../components/learner/sections/DashboardSection";
import { CoursesSection } from "../../components/learner/sections/CoursesSection";
import { PalProgressSection } from "../../components/learner/sections/PalProgressSection";
import { GradingSection } from "../../components/learner/sections/GradingSection";
import { TasksSection } from "../../components/learner/sections/TasksSection";
import { LeaderboardSection } from "../../components/learner/sections/LeaderboardSection";
import { CertificatesSection } from "../../components/learner/sections/CertificatesSection";
import { AnnouncementsSection } from "../../components/learner/sections/AnnouncementsSection";
import { ProfileSection } from "../../components/learner/sections/ProfileSection";
import { SettingsSection } from "../../components/learner/sections/SettingsSection";

export default function LearnerPage({ session, onLogout }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { showToast } = useToast();
  const scrollRef = useRef(null);

  const { data, loading, error, fetchData: load } = useLearnerStore();
  console.log("[LEARNER_PAGE] LearnerPage rendering - session:", session, "location:", location.pathname);

  // State management
  const [submittingTaskId, setSubmittingTaskId] = useState(null);
  const [startingTaskId, setStartingTaskId] = useState(null);
  const [submissionDrafts, setSubmissionDrafts] = useState({});
  const [launchingCourseId, setLaunchingCourseId] = useState(null);
  const [activeCourseId, setActiveCourseId] = useState(null);

  // Section filters and visibility
  const [courseFilter, setCourseFilter] = useState("all");
  const [taskFilter, setTaskFilter] = useState("all");
  const [showNotifications, setShowNotifications] = useState(false);
  const [animateProgress, setAnimateProgress] = useState(false);

  // Announcements state
  const [announcementState, setAnnouncementState] = useState({
    items: [],
    loading: false,
    error: "",
  });



  // Grading state
  const [gradingAnalytics, setGradingAnalytics] = useState(null);
  const [gradingLoading, setGradingLoading] = useState(false);

  // Certificates state
  const [certificates, setCertificates] = useState([]);
  const [certificatesLoading, setCertificatesLoading] = useState(false);

  // Determine active navigation
  const currentPath = location.pathname.replace(/\/$/, "");
  const pathParts = currentPath.split("/");
  const currentTab = pathParts[pathParts.length - 1];
  let activeNav = "section-dashboard";
  if (currentTab !== "learner") {
    activeNav = `section-${currentTab}`;
  }


  // Load initial data
  useEffect(() => {
    load();
  }, [load]);

  // Fetch grading analytics when grading section is active
  useEffect(() => {
    async function fetchGradingAnalytics() {
      if (activeNav === "section-grading") {
        setGradingLoading(true);
        try {
          const { data } = await api.get("/dashboard/learner/grading-analytics");
          setGradingAnalytics(data);
        } catch (err) {
          console.error("Failed to fetch grading analytics:", err);
        } finally {
          setGradingLoading(false);
        }
      }
    }
    fetchGradingAnalytics();
  }, [activeNav]);

  // Fetch certificates when certificates section is active
  useEffect(() => {
    if (activeNav === "section-certificates") {
      fetchCertificates();
    }
  }, [activeNav]);

  // Load announcements
  useEffect(() => {
    let ignore = false;
    async function loadAnnouncements() {
      setAnnouncementState((current) => ({
        ...current,
        loading: true,
        error: "",
      }));
      try {
        const response = await fetchMyAnnouncements();
        if (!ignore) {
          setAnnouncementState({
            items: Array.isArray(response.items) ? response.items : [],
            loading: false,
            error: "",
          });
        }
      } catch (requestError) {
        if (!ignore) {
          setAnnouncementState({
            items: [],
            loading: false,
            error: "Unable to load announcements.",
          });
        }
      }
    }
    loadAnnouncements();
    return () => {
      ignore = true;
    };
  }, []);

  // Animate progress bars
  useEffect(() => {
    if (!loading && data) {
      setAnimateProgress(false);
      const id = window.requestAnimationFrame(() => setAnimateProgress(true));
      return () => window.cancelAnimationFrame(id);
    }
    return undefined;
  }, [loading, data]);

  // Handlers
  function changeSection(item) {
    if (item.id === "section-dashboard") {
      navigate("/learner");
    } else {
      const tab = item.id.replace("section-", "");
      navigate(`/learner/${tab}`);
    }
  }

  async function handleLaunch(courseId) {
    if (!courseId) {
      showToast("No active course selected yet.", "warning");
      return;
    }
    setLaunchingCourseId(courseId);
    setActiveCourseId(courseId);
    window.setTimeout(() => setLaunchingCourseId(null), 250);
  }

  async function handleStartTask(taskId) {
    setStartingTaskId(taskId);
    try {
      await startTask(taskId);
      showToast("Task started.", "success");
      await load();
    } catch (requestError) {
      showToast("Unable to start task.", "error");
    } finally {
      setStartingTaskId(null);
    }
  }

  async function handleSubmitTask(taskId) {
    setSubmittingTaskId(taskId);
    try {
      await submitTaskWork(taskId, submissionDrafts[taskId] || {});
      showToast("Task submitted.", "success");
      setSubmissionDrafts((current) => ({ ...current, [taskId]: {} }));
      await load();
    } catch (requestError) {
      showToast("Unable to submit task.", "error");
    } finally {
      setSubmittingTaskId(null);
    }
  }

  async function fetchCertificates() {
    setCertificatesLoading(true);
    try {
      const response = await api.get("/api/certificates");
      const newCerts = Array.isArray(response.data.certificates)
        ? response.data.certificates
        : [];
      setCertificates(newCerts);
    } catch (err) {
      console.error("Failed to fetch certificates:", err);
      setCertificates([]);
    } finally {
      setCertificatesLoading(false);
    }
  }

  async function handleReadAnnouncement(announcementId) {
    try {
      await markAnnouncementRead(announcementId);
      setAnnouncementState((current) => ({
        ...current,
        items: current.items.map((item) =>
          item.id === announcementId
            ? {
                ...item,
                is_read: true,
                read_at: item.read_at || new Date().toISOString(),
              }
            : item
        ),
      }));
    } catch (requestError) {
      showToast(
        getErrorMessage(
          requestError,
          "Unable to mark announcement as read."
        ),
        "error"
      );
    }
  }

  function handleDraftChange(taskId, draft) {
    setSubmissionDrafts((current) => ({
      ...current,
      [taskId]: draft,
    }));
  }


  // Loading and error states
  if (loading) {
    return (
      <LoadingState
        title="Loading learning portal..."
        body="Preparing your courses, PAL progress, and tasks."
      />
    );
  }

  if (error || !data) {
    return (
      <ErrorState
        body={
          error || "Your learner dashboard did not return any data."
        }
        action={
          <Button tone="primary" onClick={load}>
            Retry
          </Button>
        }
      />
    );
  }

  // Prepare data
  const hero = data.hero || {};
  const stats = data.stats || {};
  const courses = Array.isArray(data.courses) ? data.courses : [];
  const tasks = Array.isArray(data.tasks) ? data.tasks : [];
  const notifications = Array.isArray(data.notifications)
    ? data.notifications
    : [];
  const leaderboard = Array.isArray(data.leaderboard)
    ? data.leaderboard
    : Array.isArray(data.recommendation?.leaderboard)
      ? data.recommendation.leaderboard
      : [];

  const navGroups = [
    {
      label: "Learning",
      items: [
        { id: "section-dashboard", label: "Dashboard", icon: "dashboard" },
        { id: "section-courses", label: "My Courses", icon: "course" },
        { id: "section-pal", label: "PAL Progress", icon: "leaderboard" },
        { id: "section-grading", label: "Grades", icon: "analytics" },
        {
          id: "section-tasks",
          label: "Tasks",
          icon: "task",
          badge: String(
            tasks.filter(
              (t) => t.status === "pending" || t.status === "overdue"
            ).length || 0
          ),
          badgeTone: "warn",
        },
        {
          id: "section-announcements",
          label: "Announcements",
          icon: "bell",
          badge: String(
            announcementState.items.filter((item) => !item.is_read).length || 0
          ),
          badgeTone: "brand",
        },
      ],
    },
    {
      label: "Workspace",
      items: [
        { id: "section-certificates", label: "Certificates", icon: "certificate" },
        { id: "section-leaderboard", label: "Leaderboard", icon: "leaderboard" },
      ],
    },
    {
      label: "Account",
      items: [
        { id: "section-profile", label: "Profile", icon: "profile" },
        { id: "section-settings", label: "Settings", icon: "settings" },
      ],
    },
  ];

  return (
    <DashboardShell
      theme="learner"
      brandMark={{
        label: "TS",
        background: "linear-gradient(135deg, #7C3AED, #2563EB)",
      }}
      brandTitle="Telite LMS"
      brandSubtitle="learner view"
      navGroups={navGroups}
      activeNav={activeNav}
      onNavClick={changeSection}
      profile={{
        initials:
          data.profile.avatar_initials ||
          getInitials(data.profile.full_name),
        gradient: data.profile.avatar_gradient || ["#7C3AED", "#2563EB"],
        name: data.profile.full_name,
        roleLabel: "learner",
      }}
      title={
        navGroups.flatMap((g) => g.items).find((i) => i.id === activeNav)
          ?.label ||
        titleize(currentTab === "learner" ? "Dashboard" : currentTab)
      }
      subtitle={undefined}
      topbarActions={
        <>
          <button
            className="icon-btn"
            title="Notifications"
            onClick={() => setShowNotifications(true)}
          >
            <span role="img" aria-label="bell">
              🔔
            </span>
          </button>
          <ProfileDropdown
            profile={{
              initials: getInitials(session?.user?.name || "Learner"),
              gradient: ["#0ea5e9", "#6366f1"],
              name: session?.user?.name || "Learner",
              roleLabel: "learner",
            }}
            onLogout={onLogout}
            onNavigate={(path) => navigate(`/learner/${path}`)}
          />
        </>
      }
      scrollRef={scrollRef}
    >
      <NotificationDrawer
        open={showNotifications}
        onClose={() => setShowNotifications(false)}
        notifications={notifications}
      />

      {activeCourseId && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 9999,
            background: "#fff",
          }}
        >
          <LearnerPlayer
            courseId={activeCourseId}
            onExit={() => {
              setActiveCourseId(null);
              load();
            }}
            onCertificateIssued={fetchCertificates}
          />
        </div>
      )}

      <div className="dashboard-stack">
        {activeNav === "section-dashboard" && (
          <DashboardSection
            hero={hero}
            stats={stats}
            courses={courses}
            animateProgress={animateProgress}
            onLaunch={handleLaunch}
            launchingCourseId={launchingCourseId}
            onNavigateSection={changeSection}
          />
        )}

        {activeNav === "section-courses" && (
          <CoursesSection
            courses={courses}
            courseFilter={courseFilter}
            onFilterChange={setCourseFilter}
            onLaunch={handleLaunch}
            launchingCourseId={launchingCourseId}
            animateProgress={animateProgress}
          />
        )}

        {activeNav === "section-pal" && (
          <PalProgressSection
            hero={hero}
            palBreakdown={data.pal_breakdown || {}}
          />
        )}

        {activeNav === "section-grading" && (
          <GradingSection
            gradingAnalytics={gradingAnalytics}
            gradingLoading={gradingLoading}
          />
        )}

        {activeNav === "section-tasks" && (
          <TasksSection
            tasks={tasks}
            taskFilter={taskFilter}
            onFilterChange={setTaskFilter}
            submissionDrafts={submissionDrafts}
            onDraftChange={handleDraftChange}
            startingTaskId={startingTaskId}
            submittingTaskId={submittingTaskId}
            onStartTask={handleStartTask}
            onSubmitTask={handleSubmitTask}
          />
        )}

        {activeNav === "section-leaderboard" && (
          <LeaderboardSection
            leaderboard={leaderboard}
            currentUserRank={hero.rank}
            currentUserId={data.profile.id}
          />
        )}

        {activeNav === "section-certificates" && (
          <CertificatesSection
            certificates={certificates}
            certificatesLoading={certificatesLoading}
            learnerName={data.profile.full_name}
            courses={courses}
          />
        )}

        {activeNav === "section-announcements" && (
          <AnnouncementsSection
            announcements={announcementState}
            onMarkRead={handleReadAnnouncement}
          />
        )}

        {activeNav === "section-profile" && (
          <ProfileSection profile={data.profile} />
        )}

        {activeNav === "section-settings" && <SettingsSection />}
      </div>
    </DashboardShell>
  );
}
