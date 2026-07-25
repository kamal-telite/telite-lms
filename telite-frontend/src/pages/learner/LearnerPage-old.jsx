import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  fetchMyAnnouncements,
  launchCourse,
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
import { getInitials, titleize } from "../../utils/formatters";
import { useLearnerStore } from "../../store/learnerStore";
import { LearnerPlayer } from "../../components/player/LearnerPlayer";

// Extracted Components
import { PalRing } from "../../components/learner/PalRing";
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
  const [submittingTaskId, setSubmittingTaskId] = useState(null);
  const [startingTaskId, setStartingTaskId] = useState(null);
  const [submissionDrafts, setSubmissionDrafts] = useState({});
  const [launchingCourseId, setLaunchingCourseId] = useState(null);
  const [activeCourseId, setActiveCourseId] = useState(null);
  const [certifyingCourseId, setCertifyingCourseId] = useState(null);

  // Tabs for sub-pages
  const [courseFilter, setCourseFilter] = useState("all");
  const [taskFilter, setTaskFilter] = useState("all");
  const [showNotifications, setShowNotifications] = useState(false);
  const [animateProgress, setAnimateProgress] = useState(false);
  const [announcementState, setAnnouncementState] = useState({ items: [], loading: false, error: "" });

  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [profileForm, setProfileForm] = useState({ full_name: "", email: "", organization_id: "1" });
  const [gradingAnalytics, setGradingAnalytics] = useState(null);
  const [gradingLoading, setGradingLoading] = useState(false);
  const [certificates, setCertificates] = useState([]);
  const [certificatesLoading, setCertificatesLoading] = useState(false);

  useEffect(() => {
  }, [certificates]);


  // Calculate activeNav from current path
  const currentPath = location.pathname.replace(/\/$/, "");
  const pathParts = currentPath.split("/");
  const currentTab = pathParts[pathParts.length - 1];

  let activeNav = "section-dashboard";
  if (currentTab !== "learner") {
    activeNav = `section-${currentTab}`;
  }

  useEffect(() => {
    if (data?.profile) {
      setProfileForm({
        full_name: data.profile.full_name || "",
        email: data.profile.email || "",
        organization_id: data.profile.organization_id || data.profile.org_id || "1"
      });
    }
  }, [data]);

  useEffect(() => {
    load();
  }, [load]);

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

  useEffect(() => {
    if (activeNav === "section-certificates") {
      fetchCertificates();
    }
  }, [activeNav]);

  useEffect(() => {
    let ignore = false;
    async function loadAnnouncements() {
      setAnnouncementState((current) => ({ ...current, loading: true, error: "" }));
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
          setAnnouncementState({ items: [], loading: false, error: "Unable to load announcements." });
        }
      }
    }
    loadAnnouncements();
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (!loading && data) {
      setAnimateProgress(false);
      const id = window.requestAnimationFrame(() => setAnimateProgress(true));
      return () => window.cancelAnimationFrame(id);
    }
    return undefined;
  }, [loading, data]);

  function changeSection(item) {
    if (item.id === "launch-current") {
      handleLaunch(data?.hero?.current_course?.id);
      return;
    }
    
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

  async function handleCertificate(courseId) {
    if (!courseId) return;
    const courseIdStr = String(courseId);
    setCertifyingCourseId(courseIdStr);
    try {
      const response = await api.post(`/api/certificates/${courseIdStr}/issue`);
      const cert = response.data?.certificate;
      showToast("Certificate ready.", "success");
      if (cert?.verification_token) {
        window.open(`/public/verify/${cert.verification_token}`, "_blank");
      }
      // Refresh certificates after issuing
      await fetchCertificates();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to issue certificate."), "error");
    } finally {
      setCertifyingCourseId(null);
    }
  }

  async function fetchCertificates() {
    setCertificatesLoading(true);
    try {
      const response = await api.get("/api/certificates");
      
      const newCerts = Array.isArray(response.data.certificates) ? response.data.certificates : [];
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
            ? { ...item, is_read: true, read_at: item.read_at || new Date().toISOString() }
            : item
        ),
      }));
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to mark announcement as read."), "error");
    }
  }

  if (loading) {
    return <LoadingState title="Loading learning portal..." body="Preparing your courses, PAL progress, and tasks." />;
  }

  if (error || !data) {
    return <ErrorState body={error || "Your learner dashboard did not return any data."} action={<Button tone="primary" onClick={load}>Retry</Button>} />;
  }

  const hero = data.hero || {};
  const stats = data.stats || {};
  const courses = Array.isArray(data.courses) ? data.courses : [];
  const tasks = Array.isArray(data.tasks) ? data.tasks : [];
  const notifications = Array.isArray(data.notifications) ? data.notifications : [];
  const leaderboard = Array.isArray(data.recommendation?.leaderboard) ? data.recommendation.leaderboard : [];
  const rankLabel = hero.rank == null ? "-" : `#${hero.rank}`;
  const cohortRankLabel = stats.cohort_rank == null ? "-" : `#${stats.cohort_rank}`;
  const avgQuizScore = Number.isFinite(Number(stats.avg_quiz_score)) ? Math.round(Number(stats.avg_quiz_score)) : 0;

  const navGroups = [
    {
      label: "Learning",
      items: [
        { id: "section-dashboard", label: "Dashboard", icon: "dashboard" },
        { id: "section-courses", label: "My Courses", icon: "course" },
        { id: "section-pal", label: "PAL Progress", icon: "leaderboard" },
        { id: "section-grading", label: "Grades", icon: "analytics" },
        { id: "section-tasks", label: "Tasks", icon: "task", badge: String(tasks.filter(t => t.status === "pending" || t.status === "overdue").length || 0), badgeTone: "warn" },
        { id: "section-announcements", label: "Announcements", icon: "bell", badge: String(announcementState.items.filter((item) => !item.is_read).length || 0), badgeTone: "brand" },
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
      ]
    }
  ];

  return (
    <DashboardShell
      theme="learner"
      brandMark={{ label: "TS", background: "linear-gradient(135deg, #7C3AED, #2563EB)" }}
      brandTitle="Telite LMS"
      brandSubtitle="learner view"
      navGroups={navGroups}
      activeNav={activeNav}
      onNavClick={changeSection}
      profile={{
        initials: data.profile.avatar_initials || getInitials(data.profile.full_name),
        gradient: data.profile.avatar_gradient || ["#7C3AED", "#2563EB"],
        name: data.profile.full_name,
        roleLabel: "learner",
      }}
      title={navGroups.flatMap(g => g.items).find(i => i.id === activeNav)?.label || titleize(currentTab === "learner" ? "Dashboard" : currentTab)}
      subtitle={`${data.profile.category_scope?.toUpperCase()} category · Telite Systems`}
      topbarActions={
        <>
          <Badge tone="accent">PAL {formatPercent(hero.pal_score)}</Badge>
          <Button
            tone="primary"
            icon="external"
            onClick={() => handleLaunch(hero.current_course?.id)}
            disabled={launchingCourseId === hero.current_course?.id}
          >
            {launchingCourseId === hero.current_course?.id ? "Launching..." : "Resume Course"}
          </Button>
          <button className="icon-btn" title="Notifications" onClick={() => setShowNotifications(true)}>
            <span role="img" aria-label="bell">🔔</span>
          </button>
          <ProfileDropdown profile={{
            initials: getInitials(session?.user?.name || "Learner"),
            gradient: ["#0ea5e9", "#6366f1"],
            name: session?.user?.name || "Learner",
            roleLabel: "learner",
          }} onLogout={onLogout} onNavigate={(path) => navigate(`/learner/${path}`)} />
        </>
      }
      scrollRef={scrollRef}
    >
      <NotificationDrawer open={showNotifications} onClose={() => setShowNotifications(false)} notifications={notifications} />
      
      {activeCourseId && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 9999, background: "#fff" }}>
          <LearnerPlayer courseId={activeCourseId} onExit={() => { setActiveCourseId(null); load(); }} onCertificateIssued={fetchCertificates} />
        </div>
      )}

      <div className="dashboard-stack">
        
        {/* DASHBOARD PAGE */}
        {activeNav === "section-dashboard" && (
          <section id="section-dashboard">
            <div className="hero-banner">
              <div className="leaderboard-row" style={{ padding: 0, borderBottom: 0, justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div className="eyebrow" style={{ margin: 0, color: "rgba(255,255,255,0.8)" }}>Learner workspace</div>
                  <h2>{hero.headline}</h2>
                  <p>{hero.subtext}</p>
                </div>
                <div className="summary-chip" style={{ background: "rgba(255,255,255,0.14)", borderColor: "rgba(255,255,255,0.24)" }}>
                  <div className="summary-chip__label" style={{ color: "rgba(255,255,255,0.75)" }}>PAL score</div>
                  <div className="summary-chip__value" style={{ color: "#fff" }}>{formatPercent(hero.pal_score)}</div>
                </div>
              </div>
              <div className="hero-banner__metrics">
                <div className="hero-metric">
                  <span>Rank</span>
                  <strong>{rankLabel}</strong>
                </div>
                <div className="hero-metric">
                  <span>Streak</span>
                  <strong>{hero.streak_days || 0}d</strong>
                </div>
                <div className="hero-metric">
                  <span>Hours logged</span>
                  <strong>{Math.round(hero.pal_time_spent_hours || hero.time_spent_hours || 0)}h</strong>
                </div>
              </div>
              <div className="hero-actions" style={{ marginTop: 18 }}>
                <Button tone="primary" icon="external" onClick={() => handleLaunch(hero.current_course?.id)}>
                  Resume Course
                </Button>
                <Button tone="ghost" onClick={() => changeSection({ id: "section-pal" })}>
                  View PAL Report
                </Button>
              </div>
            </div>

            <div className="grid-4">
              <StatCard accent="#059669" label="Courses Completed" value={stats.courses_completed ?? 0} meta="Completed and archived" />
              <StatCard accent="#D97706" label="Today's Learning Time" value={formatLearningTime(hero.today_time_seconds || 0)} meta="Active time only" />
              <StatCard accent="#2563EB" label="Total Time Spent" value={`${Math.round(hero.time_spent_hours || 0)}h`} meta={hero.last_session ? "Last session recorded" : "No sessions yet"} />
              <StatCard accent="#7C3AED" label="Assignment Status" value={hero.assignment_status ? titleize(String(hero.assignment_status).replace("_", " ")) : "None"} meta={`Rank ${cohortRankLabel}`} />
            </div>

            <Panel title="Recent Courses" subtitle="Resume where you left off" action={<button className="panel-link" onClick={() => changeSection({ id: 'section-courses' })}>View all →</button>}>
              <div className="grid-3">
                {courses.slice(0,3).map((course) => {
                  const courseId = String(course.id || course.course_id);
                  return (
                    <article className={`course-card has-cover ${hero.current_course?.id === courseId ? "is-active" : ""}`} key={courseId}>
                      <div className="course-card__cover">
                        <img
                          src={course.cover_image_url || `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="225" viewBox="0 0 400 225"><rect width="100%" height="100%" fill="%23f1f5f9"/><g transform="translate(200, 112.5)" text-anchor="middle" fill="%2364748b"><rect x="-60" y="-30" width="120" height="60" rx="6" fill="%23cbd5e1"/><text font-family="system-ui, sans-serif" font-weight="bold" font-size="28" y="10" fill="%23475569">${course.name ? encodeURIComponent(course.name.substring(0, 2).toUpperCase()) : "CO"}</text></g></svg>`}
                          loading="lazy"
                          alt={course.name}
                        />
                      </div>
                      <div className="course-card__content">
                        <div>
                          <div className="course-card__header">
                            <h3 className="course-card__title">{course.name}</h3>
                            <Badge tone={course.status === "completed" ? "success" : "neutral"}>
                              {titleize(course.status)}
                            </Badge>
                          </div>
                          <p className="course-card__category-tier">
                            {titleize(course.category_slug?.replace("-", " ") || "General")} • {course.tier || "Basic"}
                          </p>
                          <div className="course-card__progress-section">
                            <div className="course-card__progress-bar">
                              <div className="bar-score">
                                <div className="progress-track">
                                  <div
                                    className="progress-fill"
                                    style={{
                                      width: animateProgress ? `${course.completion_pct}%` : "0%",
                                      background: getCompletionColor(course.completion_pct),
                                    }}
                                  />
                                </div>
                              </div>
                            </div>
                            <span className="course-card__progress-text">{formatPercent(course.completion_pct)}</span>
                          </div>
                        </div>
                        <Button 
                          className="course-card__action"
                          tone={course.status === "completed" ? "ghost" : "primary"} 
                          onClick={() => handleLaunch(courseId)} 
                          disabled={launchingCourseId === courseId}
                        >
                          {launchingCourseId === courseId ? "Loading..." : course.status === "completed" ? "Review" : "Continue Learning"}
                        </Button>
                      </div>
                    </article>
                  );
                })}
              </div>
            </Panel>
          </section>
        )}

        {/* MY COURSES PAGE */}
        {activeNav === "section-courses" && (
          <section id="section-courses">
            <Panel title="All Courses" subtitle="Your complete learning path">
              <div className="toolbar" style={{ marginBottom: 16 }}>
                {["all", "in_progress", "completed", "not_started"].map(f => (
                  <label className="chip" key={f}>
                    <input type="radio" checked={courseFilter === f} onChange={() => setCourseFilter(f)} /> {titleize(f.replace("_", " "))}
                  </label>
                ))}
              </div>
              <div className="grid-3">
                {courses.filter(c => courseFilter === "all" ? true : c.status === courseFilter).map((course) => {
                  const courseId = String(course.id || course.course_id);
                  return (
                    <article className="course-card has-cover" key={courseId}>
                      <div className="course-card__cover">
                        <img
                          src={course.cover_image_url || `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="225" viewBox="0 0 400 225"><rect width="100%" height="100%" fill="%23f1f5f9"/><g transform="translate(200, 112.5)" text-anchor="middle" fill="%2364748b"><rect x="-60" y="-30" width="120" height="60" rx="6" fill="%23cbd5e1"/><text font-family="system-ui, sans-serif" font-weight="bold" font-size="28" y="10" fill="%23475569">${course.name ? encodeURIComponent(course.name.substring(0, 2).toUpperCase()) : "CO"}</text></g></svg>`}
                          loading="lazy"
                          alt={course.name}
                        />
                      </div>
                      <div className="course-card__content">
                        <div>
                          <div className="course-card__header">
                            <h3 className="course-card__title">{course.name}</h3>
                            <Badge tone={course.status === "completed" ? "success" : "neutral"}>
                              {titleize(course.status)}
                            </Badge>
                          </div>
                          <p className="course-card__category-tier">
                            {titleize(course.category_slug?.replace("-", " ") || "General")} • {course.tier || "Basic"}
                          </p>
                          <div className="course-card__progress-section">
                            <div className="course-card__progress-bar">
                              <div className="bar-score">
                                <div className="progress-track">
                                  <div
                                    className="progress-fill"
                                    style={{
                                      width: animateProgress ? `${course.completion_pct}%` : "0%",
                                      background: getCompletionColor(course.completion_pct),
                                    }}
                                  />
                                </div>
                              </div>
                            </div>
                            <span className="course-card__progress-text">{formatPercent(course.completion_pct)}</span>
                          </div>
                        </div>
                        <Button 
                          className="course-card__action"
                          tone={course.status === "completed" ? "ghost" : "primary"} 
                          onClick={() => handleLaunch(courseId)} 
                          disabled={launchingCourseId === courseId}
                        >
                          {launchingCourseId === courseId ? "Loading..." : course.status === "completed" ? "Review" : "Continue Learning"}
                        </Button>
                      </div>
                    </article>
                  );
                })}
              </div>
            </Panel>
          </section>
        )}

        {/* PAL PROGRESS PAGE */}
        {activeNav === "section-pal" && (
          <section id="section-pal">
            {(() => {
              const palBreakdown = data.pal_breakdown || {};
              const trend = palBreakdown.progress_trend || [];
              const timeline = palBreakdown.completion_timeline || [];
              return (
                <>
            <div className="hero-banner" style={{ background: "linear-gradient(135deg, #f59e0b, #d97706)", padding: "40px 20px" }}>
              <div style={{ textAlign: "center", color: "#fff", display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" }}>
                <PalRing score={Math.round(Number(hero.pal_score) || 0)} />
                <div>
                  <h2 style={{ fontSize: "1.5rem", margin: 0 }}>PAL Score Analysis</h2>
                  <p style={{ margin: "4px 0 0", opacity: 0.9 }}>Your holistic performance rating across all modules.</p>
                </div>
              </div>
            </div>
            <Panel title="PAL Dimensions" subtitle="How your score is calculated">
               <div className="pal-list">
                 {[
                   { label: "Course Completion", value: palBreakdown.completion || 0, weight: 0.3 },
                   { label: "Quiz Average", value: palBreakdown.pal_quiz_avg || 0, weight: 0.3 },
                   { label: "Assignment Average", value: palBreakdown.assignment_average || 0, weight: 0.2 },
                   { label: "Task Completion", value: palBreakdown.task_completion || 0, weight: 0.2 },
                 ].map((dim) => (
                   <div className="pal-item" key={dim.label}>
                     <div className="pal-item__info">
                       <span className="pal-item__label">{dim.label}</span>
                       <span className="pal-item__weight">Weight: {dim.weight * 100}%</span>
                     </div>
                     <div className="pal-item__track">
                       <div className="pal-item__fill" style={{ width: `${dim.value}%`, background: getScoreColor(dim.value) }} />
                     </div>
                     <div className="pal-item__value mono" style={{ color: getScoreColor(dim.value) }}>
                       {formatPercent(dim.value)}
                     </div>
                   </div>
                 ))}
               </div>
            </Panel>
            <div className="grid-4" style={{ marginTop: 18 }}>
              <StatCard accent="#2563EB" label="Current Rank" value={palBreakdown.current_rank ? `#${palBreakdown.current_rank}` : "-"} meta="Category leaderboard" />
              <StatCard accent="#059669" label="Leaderboard Position" value={palBreakdown.leaderboard_position ? `#${palBreakdown.leaderboard_position}` : "-"} meta="Dynamic PAL score" />
              <StatCard accent="#7C3AED" label="Highest Strength" value={(palBreakdown.strengths || [])[0] || "Building"} meta={`${(palBreakdown.strengths || []).length} strong areas`} />
              <StatCard accent="#D97706" label="Focus Area" value={(palBreakdown.weak_areas || [])[0] || "Balanced"} meta={`${(palBreakdown.weak_areas || []).length} weak areas`} />
            </div>
            <div className="grid-2" style={{ marginTop: 18 }}>
              <Panel title="Progress Trend" subtitle="Recent learning activity">
                {trend.length ? (
                  <ChartCanvas
                    type="bar"
                    height={180}
                    labels={trend.map((item) => item.label)}
                    datasets={[{ label: "Activity", data: trend.map((item) => item.value), backgroundColor: "#2563EB", borderRadius: 8 }]}
                  />
                ) : (
                  <EmptyState title="No trend yet" body="Learning activity will appear here automatically." />
                )}
              </Panel>
              <Panel title="Completion Timeline" subtitle="Latest modules, quizzes, and submissions">
                {timeline.length ? (
                  <div className="activity-list">
                    {timeline.slice(0, 5).map((item, index) => (
                      <div className="activity-item" key={`${item.type}-${item.created_at}-${index}`}>
                        <div className="activity-item__main">
                          <div className="activity-item__title">{titleize(String(item.type || "").replaceAll("_", " "))}</div>
                          <div className="activity-item__meta">{item.created_at ? formatDateTime(item.created_at) : "Recently"}</div>
                        </div>
                        {item.payload?.score !== undefined ? <Badge tone="info">{Math.round(item.payload.score)}%</Badge> : null}
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState title="No completions yet" body="Completed activities will appear here automatically." />
                )}
              </Panel>
            </div>
                </>
              );
            })()}
          </section>
        )}

        {/* GRADING PAGE */}
        {activeNav === "section-grading" && (
          <section id="section-grading">
            {gradingLoading ? (
              <LoadingState title="Loading your grades..." body="Fetching your grade data from the system." />
            ) : gradingAnalytics ? (
              gradingAnalytics.has_grades ? (
                <>
                  <div className="grid-4">
                    <StatCard accent="#7C3AED" label="Overall Grade" value={gradingAnalytics.overall_grade || `${gradingAnalytics.final_grade}%`} meta={`${gradingAnalytics.final_grade}% overall`} />
                    <StatCard accent="#2563EB" label="Completed Assessments" value={gradingAnalytics.completed_assessments || 0} meta={`${gradingAnalytics.pending_evaluations || 0} pending`} />
                    <StatCard accent="#059669" label="Quiz Average" value={`${gradingAnalytics.quiz_average}%`} meta="Assessment performance" />
                    <StatCard accent="#F59E0B" label="Assignment Average" value={`${gradingAnalytics.assignment_average}%`} meta="Task performance" />
                  </div>
                  <div className="grid-4" style={{ marginTop: 18 }}>
                    <StatCard accent="#2563EB" label="Overall Percentage" value={`${gradingAnalytics.current_percentage}%`} meta="Live gradebook average" />
                    <StatCard accent="#059669" label="Highest Score" value={`${gradingAnalytics.highest_score || 0}%`} meta="Best assessment" />
                    <StatCard accent="#DC2626" label="Lowest Score" value={`${gradingAnalytics.lowest_score || 0}%`} meta="Lowest graded item" />
                    <StatCard accent="#7C3AED" label="Status" value={gradingAnalytics.pass_fail_status} meta="Current standing" />
                  </div>

                  <Panel title="Assessment Grades" subtitle="Quizzes, assignments, feedback, and evaluation status" style={{ marginTop: 18 }}>
                    {(gradingAnalytics.assessments || []).length ? (
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Course</th>
                              <th>Assessment</th>
                              <th>Type</th>
                              <th style={{ textAlign: "right" }}>Marks</th>
                              <th style={{ textAlign: "right" }}>Percentage</th>
                              <th>Grade</th>
                              <th>Status</th>
                              <th>Submitted</th>
                              <th>Evaluated</th>
                              <th>Evaluator</th>
                              <th>Feedback</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(gradingAnalytics.assessments || []).map((item) => (
                              <tr key={item.id}>
                                <td>{item.course_name}</td>
                                <td>
                                  <div className="row-title">{item.assessment_name || item.quiz_name || item.assignment_name}</div>
                                  {item.attempt_number ? <div className="row-subtitle">Attempt {item.attempt_number}{item.attempts_remaining !== null && item.attempts_remaining !== undefined ? ` · ${item.attempts_remaining} left` : ""}</div> : null}
                                </td>
                                <td>{item.assessment_type}</td>
                                <td className="mono" style={{ textAlign: "right" }}>{item.marks_obtained ?? "-"} / {item.maximum_marks ?? "-"}</td>
                                <td className="mono" style={{ textAlign: "right", color: item.percentage !== null && item.percentage !== undefined ? getScoreColor(item.percentage) : undefined, fontWeight: 700 }}>
                                  {item.percentage !== null && item.percentage !== undefined ? `${item.percentage}%` : "-"}
                                </td>
                                <td>{item.grade || "-"}</td>
                                <td><Badge tone={item.status === "graded" || item.status === "approved" ? "success" : item.status === "rejected" ? "danger" : "warn"}>{titleize(String(item.status || "pending").replace("_", " "))}</Badge></td>
                                <td className="mono">{item.submission_date ? formatDateTime(item.submission_date) : "-"}</td>
                                <td className="mono">{item.evaluation_date ? formatDateTime(item.evaluation_date) : "-"}</td>
                                <td>{item.evaluator_name || "-"}</td>
                                <td>{item.feedback || "-"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <EmptyState title="No assessment grades yet" body="Quiz and assignment grades will appear here after evaluation." />
                    )}
                  </Panel>

                  <Panel title="Course Grades" subtitle="Course completion and assessment averages" style={{ marginTop: 18 }}>
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Course</th>
                            <th style={{ textAlign: "right" }}>Completion</th>
                            <th style={{ textAlign: "right" }}>Quiz Avg</th>
                            <th style={{ textAlign: "right" }}>Assignment Avg</th>
                            <th style={{ textAlign: "right" }}>Course Grade</th>
                            <th>Certificate</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {gradingAnalytics.grade_summary.map((grade, idx) => (
                            <tr key={idx}>
                              <td>{grade.course_name}</td>
                              <td className="mono" style={{ textAlign: "right" }}>{formatPercent(grade.completion_percentage || 0)}</td>
                              <td className="mono" style={{ textAlign: "right" }}>{formatPercent(grade.average_quiz_score || 0)}</td>
                              <td className="mono" style={{ textAlign: "right" }}>{formatPercent(grade.average_assignment_score || 0)}</td>
                              <td className="mono" style={{ textAlign: "right", color: getScoreColor(grade.percentage), fontWeight: 700 }}>
                                {grade.percentage}% {grade.display_grade ? `(${grade.display_grade})` : ""}
                              </td>
                              <td>
                                <Badge tone={grade.certificate_eligibility ? "success" : "neutral"}>
                                  {grade.certificate_eligibility ? "Eligible" : "Not yet"}
                                </Badge>
                              </td>
                              <td>
                                <Badge tone={grade.passed ? "success" : "danger"}>
                                  {grade.passed ? "Pass" : "Fail"}
                                </Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Panel>

                  <Panel title="Grade Progress" subtitle="Your performance across courses" style={{ marginTop: 18 }}>
                    <ChartCanvas
                      type="bar"
                      height={200}
                      labels={gradingAnalytics.grade_progress.map(g => g.course_name)}
                      datasets={[
                        {
                          label: "Grade",
                          data: gradingAnalytics.grade_progress.map(g => g.percentage),
                          backgroundColor: gradingAnalytics.grade_progress.map(g => getScoreColor(g.percentage)),
                          borderRadius: 8,
                        },
                      ]}
                      options={{
                        plugins: { legend: { display: false } },
                        scales: { y: { beginAtZero: true, max: 100 } },
                      }}
                    />
                  </Panel>
                </>
              ) : (
                <EmptyState title={gradingAnalytics.message || "No grades available"} body="Your grades will appear here once your assessments have been evaluated." />
              )
            ) : (
              <EmptyState title="No grading data available" body="Grading analytics will appear once courses have been graded." />
            )}
          </section>
        )}

        {/* TASKS PAGE */}
        {activeNav === "section-tasks" && (
          <section id="section-tasks">
            <Panel title="Task Management" subtitle="Your assigned projects and assessments">
              <div className="toolbar" style={{ marginBottom: 16 }}>
                {["all", "assigned", "in_progress", "submitted", "approved", "revision_requested"].map(f => (
                  <label className="chip" key={f}>
                    <input type="radio" checked={taskFilter === f} onChange={() => setTaskFilter(f)} /> {titleize(f)}
                  </label>
                ))}
              </div>
              <div className="grid-2">
                {tasks.filter(t => taskFilter === "all" ? true : t.status === taskFilter).map((task) => {
                  const draft = submissionDrafts[task.id] || {};
                  const canStart = task.status === "assigned" || task.status === "revision_requested";
                  const canSubmit = task.status === "in_progress" || task.status === "revision_requested";
                  const tone = task.status === "approved" ? "success" : task.status === "submitted" ? "brand" : task.status === "revision_requested" ? "danger" : "warn";
                  return (
                    <div className="soft-card" key={task.id}>
                      <div className="split-actions" style={{ alignItems: "flex-start" }}>
                        <div>
                          <div className="row-title">{task.title}</div>
                          <div className="row-subtitle">Assigned by: {task.assigned_by_name || "Category Admin"}</div>
                          <div className="row-subtitle">Due: {formatDateTime(task.due_at)}</div>
                        </div>
                        <Badge tone={tone}>{titleize(task.status)}</Badge>
                      </div>
                      <p className="muted" style={{ marginTop: 12 }}>{task.instructions || "No additional instructions."}</p>
                      {canSubmit ? (
                        <div className="form-stack" style={{ marginTop: 12 }}>
                          <textarea
                            className="field__input"
                            rows={3}
                            placeholder="Submission notes"
                            value={draft.submission_notes || ""}
                            onChange={(event) => setSubmissionDrafts((current) => ({ ...current, [task.id]: { ...draft, submission_notes: event.target.value } }))}
                          />
                          <input
                            className="field__input"
                            placeholder="Github URL or external link"
                            value={draft.external_url || ""}
                            onChange={(event) => setSubmissionDrafts((current) => ({ ...current, [task.id]: { ...draft, external_url: event.target.value } }))}
                          />
                        </div>
                      ) : null}
                      <div className="split-actions" style={{ marginTop: 14 }}>
                        {canStart ? (
                          <Button size="small" tone="primary" onClick={() => handleStartTask(task.id)} disabled={startingTaskId === task.id}>
                            {startingTaskId === task.id ? "Starting..." : "Start Task"}
                          </Button>
                        ) : null}
                        {canSubmit ? (
                          <Button size="small" tone="primary" onClick={() => handleSubmitTask(task.id)} disabled={submittingTaskId === task.id}>
                            {submittingTaskId === task.id ? "Submitting..." : "Submit Task"}
                          </Button>
                        ) : null}
                        {task.status === "submitted" ? <span className="muted">Awaiting review</span> : null}
                        {task.status === "approved" ? <span className="muted">Approved</span> : null}
                      </div>
                    </div>
                  );
                })}
                {tasks.filter(t => taskFilter === "all" ? true : t.status === taskFilter).length === 0 && (
                  <EmptyState title="No tasks assigned yet." body="Tasks assigned by your Category Admin will appear here." />
                )}
              </div>
            </Panel>
          </section>
        )}

        {/* LEADERBOARD PAGE */}
        {activeNav === "section-leaderboard" && (
          <section id="section-leaderboard">
            <Panel title="Cohort Leaderboard" subtitle={`You are currently ${rankLabel} in your cohort`}>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th style={{ width: 60, textAlign: "center" }}>Rank</th>
                      <th>Learner</th>
                      <th style={{ textAlign: "right" }}>PAL Score</th>
                      <th style={{ textAlign: "right" }}>Streak</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaderboard.map((row, idx) => {
                      const rowId = String(row.id || idx);
                      return (
                        <tr key={rowId} className={rowId === String(data.profile.id) ? "is-highlighted" : ""}>
                          <td style={{ textAlign: "center", fontWeight: 700, color: getRankColor(row.rank) }}>
                            #{row.rank}
                          </td>
                          <td>
                            <div className="leaderboard-row" style={{ padding: 0, borderBottom: 0 }}>
                              <Avatar initials={getInitials(row.full_name)} size={24} />
                              <span>{row.full_name}</span>
                            </div>
                          </td>
                          <td className="mono" style={{ textAlign: "right", color: getScoreColor(row.pal_score), fontWeight: 700 }}>
                            {formatPercent(row.pal_score)}
                          </td>
                          <td className="mono" style={{ textAlign: "right", color: "var(--text-secondary)" }}>
                            {row.streak_days}d
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Panel>
          </section>
        )}

        {/* CERTIFICATES PAGE */}
        {activeNav === "section-certificates" && (
          <section id="section-certificates">
            <Panel title="Certificates" subtitle="Earned credentials">
              {certificatesLoading ? (
                <LoadingState title="Loading certificates..." body="Fetching your earned certificates." />
              ) : certificates.length > 0 ? (
                <div className="grid-3">
                  {certificates.map(cert => {
                    const courseId = String(cert.course_id);
                    const certNumber = cert.certificate_hash ? cert.certificate_hash.substring(0, 8).toUpperCase() : "N/A";
                    const issueDate = cert.issued_at ? new Date(cert.issued_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) : "N/A";
                    return (
                      <div className="soft-card" key={cert.id} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                        <div style={{ background: "var(--brand-gradient, linear-gradient(135deg, #0ea5e9, #6366f1))", height: 100, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: "bold", fontSize: "24px" }}>
                          🎓
                        </div>
                        <div>
                          <div className="row-title">{cert.course_name || "Course"}</div>
                          <div className="row-subtitle">{data.profile.full_name || "Learner"}</div>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "var(--text-muted)" }}>
                          <span>ID: {certNumber}</span>
                          <span>{issueDate}</span>
                        </div>
                        <div style={{ display: "flex", gap: 8, marginTop: "auto" }}>
                          <Button tone="primary" size="small" onClick={() => window.open(`/api/certificates/${courseId}/download?inline=true`, "_blank")} style={{ flex: 1 }}>
                            View
                          </Button>
                          <Button tone="ghost" size="small" onClick={() => window.open(`/api/certificates/${courseId}/download`, "_blank")} style={{ flex: 1 }}>
                            Download
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <EmptyState title="No certificates yet" body="Complete your first course to earn a certificate." />
              )}
            </Panel>
          </section>
        )}

        {/* ANNOUNCEMENTS PAGE */}
        {activeNav === "section-announcements" && (
          <section id="section-announcements">
            <Panel title="Announcements" subtitle="Updates from your organization">
              {announcementState.loading ? (
                <LoadingState title="Loading announcements..." body="Checking the latest messages." />
              ) : announcementState.error ? (
                <ErrorState body={announcementState.error} action={<Button tone="primary" onClick={() => window.location.reload()}>Retry</Button>} />
              ) : announcementState.items.length === 0 ? (
                <EmptyState title="No announcements yet" body="Organization announcements will appear here." />
              ) : (
                <div className="dashboard-stack">
                  {announcementState.items.map((announcement) => (
                    <article className="soft-card" key={announcement.id}>
                      <div className="split-actions" style={{ alignItems: "flex-start" }}>
                        <div>
                          <div className="row-title">{announcement.title}</div>
                          <div className="row-subtitle">
                            {announcement.published_at ? formatMonthDate(announcement.published_at) : "Published"}
                          </div>
                        </div>
                        <Badge tone={announcement.is_read ? "neutral" : "brand"}>
                          {announcement.is_read ? "Read" : "Unread"}
                        </Badge>
                      </div>
                      <p className="muted" style={{ marginTop: 12 }}>{announcement.body}</p>
                      {!announcement.is_read ? (
                        <div style={{ marginTop: 14 }}>
                          <Button size="small" tone="primary" onClick={() => handleReadAnnouncement(announcement.id)}>
                            Mark read
                          </Button>
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              )}
            </Panel>
          </section>
        )}

        {/* PROFILE PAGE */}
        {activeNav === "section-profile" && (
          <section id="section-profile">
            <Panel 
              title="Profile Information" 
              subtitle="Your learner details"
              action={
                isEditingProfile ? (
                  <div className="split-actions">
                    <Button tone="ghost" onClick={() => setIsEditingProfile(false)}>Cancel</Button>
                    <Button tone="primary" onClick={() => {
                      showToast("Profile updated successfully.", "success");
                      setIsEditingProfile(false);
                    }}>Save Changes</Button>
                  </div>
                ) : (
                  <Button tone="ghost" icon="edit" onClick={() => setIsEditingProfile(true)}>Edit Profile</Button>
                )
              }
            >
              <div className="grid-2">
                <div className="soft-card">
                  <div className="row-subtitle">Full Name</div>
                  {isEditingProfile ? (
                    <input className="field__input" style={{ marginTop: 8 }} value={profileForm.full_name} onChange={(e) => setProfileForm({ ...profileForm, full_name: e.target.value })} />
                  ) : (
                    <div className="row-title">{data.profile.full_name}</div>
                  )}
                </div>
                <div className="soft-card">
                  <div className="row-subtitle">Email Address</div>
                  {isEditingProfile ? (
                    <input className="field__input" style={{ marginTop: 8 }} type="email" value={profileForm.email} onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })} />
                  ) : (
                    <div className="row-title">{data.profile.email}</div>
                  )}
                </div>
                <div className="soft-card">
                  <div className="row-subtitle">Organization</div>
                  {isEditingProfile ? (
                    <select className="field__select" style={{ marginTop: 8 }} value={profileForm.organization_id} onChange={(e) => setProfileForm({ ...profileForm, organization_id: e.target.value })}>
                      <option value="1">Telite Systems (HQ)</option>
                      <option value="2">Acme Corp</option>
                      <option value="3">Globex Inc</option>
                    </select>
                  ) : (
                    <div className="row-title">{data.profile.category_scope || "Telite Systems"}</div>
                  )}
                </div>
                <div className="soft-card">
                  <div className="row-subtitle">Enrollment Type</div>
                  <div className="row-title" style={{ marginTop: isEditingProfile ? 8 : 0 }}>
                    <Badge tone={data.profile.enrollment_type === "self" ? "accent" : "brand"}>{data.profile.enrollment_type}</Badge>
                  </div>
                </div>
              </div>
            </Panel>
          </section>
        )}

        {/* SETTINGS PAGE */}
        {activeNav === "section-settings" && (
          <section id="section-settings">
            <Panel title="Account Settings" subtitle="Personalize your workspace">
              <EmptyState title="Settings coming soon" body="Theme toggles, notifications, and privacy options will be available here." />
            </Panel>
          </section>
        )}

      </div>
    </DashboardShell>
  );
}
