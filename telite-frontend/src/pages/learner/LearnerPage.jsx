import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { launchCourse, submitTask } from "../../services/client";
import { DashboardShell, ProfileDropdown } from "../../layouts/DashboardLayout";
import { Avatar, Badge, Button, ErrorState, LoadingState, Panel, StatCard, useToast, EmptyState, IconButton } from "../../components/common/ui";
import { ChartCanvas } from "../../components/common/charts";
import {
  formatDateTime,
  formatMonthDate,
  formatPercent,
  getCompletionColor,
  getInitials,
  getRankColor,
  getScoreColor,
  titleize
} from "../../utils/formatters";
import { useLearnerStore } from "../../store/learnerStore";

function PalRing({ score, size = 120 }) {
  const radius = 50;
  const stroke = 8;
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const next = Math.max(0, Math.min(100, Number(score) || 0));
    const id = window.requestAnimationFrame(() => setAnimatedScore(next));
    return () => window.cancelAnimationFrame(id);
  }, [score]);

  const dashOffset = useMemo(() => {
    return circumference - (animatedScore / 100) * circumference;
  }, [animatedScore, circumference]);

  return (
    <div className="pal-ring" style={{ width: size, height: size }}>
      <svg height={size} width={size} style={{ transform: "rotate(-90deg)" }}>
        <circle
          className="pal-ring__track"
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={size / 2}
          cy={size / 2}
        />
        <circle
          className="pal-ring__fill"
          fill="transparent"
          strokeWidth={stroke}
          strokeDasharray={`${circumference} ${circumference}`}
          style={{ strokeDashoffset: dashOffset }}
          strokeLinecap="round"
          r={normalizedRadius}
          cx={size / 2}
          cy={size / 2}
        />
      </svg>
      <div className="pal-ring__label">
        <div className="pal-ring__value mono">{Math.round(animatedScore)}%</div>
        <div className="pal-ring__caption">PAL</div>
      </div>
    </div>
  );
}

function NotificationDrawer({ open, onClose, notifications }) {
  if (!open) return null;
  return (
    <div className="notification-drawer" role="dialog" aria-modal="true" aria-label="Notifications">
      <div className="notification-drawer__header">
        <h3>Notifications</h3>
        <IconButton label="Close notifications" icon="close" size="sm" onClick={onClose} />
      </div>
      <div className="notification-drawer__body">
        {notifications?.length === 0 ? (
          <EmptyState title="You're all caught up" body="No new notifications." />
        ) : (
          notifications?.map(n => (
            <div key={n.id} className="notification-drawer__item">
              <div className="notification-drawer__title">{n.title}</div>
              <div className="notification-drawer__message">{n.message}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
export default function LearnerPage({ session, onLogout }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { showToast } = useToast();
  const scrollRef = useRef(null);
  
  const { data, loading, error, fetchData: load } = useLearnerStore();
  const [submittingTaskId, setSubmittingTaskId] = useState(null);
  const [launchingId, setLaunchingId] = useState(null);

  // Tabs for sub-pages
  const [courseFilter, setCourseFilter] = useState("all");
  const [taskFilter, setTaskFilter] = useState("all");
  const [showNotifications, setShowNotifications] = useState(false);
  const [animateProgress, setAnimateProgress] = useState(false);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!loading && data) {
      setAnimateProgress(false);
      const id = window.requestAnimationFrame(() => setAnimateProgress(true));
      return () => window.cancelAnimationFrame(id);
    }
    return undefined;
  }, [loading, data]);

  const currentPath = location.pathname.replace(/\/$/, "");
  const pathParts = currentPath.split("/");
  const currentTab = pathParts[pathParts.length - 1];

  let activeNav = "section-dashboard";
  if (currentTab !== "learner") {
    activeNav = `section-${currentTab}`;
  }

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
    setLaunchingId(courseId);
    try {
      const payload = await launchCourse(courseId);
      window.open(payload.launch_url, "_blank", "noopener,noreferrer");
      showToast(`Launching ${payload.course_name}...`, "info");
    } catch (requestError) {
      showToast("Unable to launch Moodle course.", "error");
    } finally {
      setLaunchingId(null);
    }
  }

  async function handleSubmitTask(taskId) {
    setSubmittingTaskId(taskId);
    try {
      await submitTask(taskId);
      showToast("Task marked as submitted.", "success");
      await load();
    } catch (requestError) {
      showToast("Unable to submit task.", "error");
    } finally {
      setSubmittingTaskId(null);
    }
  }

  if (loading) {
    return <LoadingState title="Loading learning portal..." body="Preparing your courses, PAL progress, and tasks." />;
  }

  if (error || !data) {
    return <ErrorState body={error || "Your learner dashboard did not return any data."} action={<Button tone="primary" onClick={load}>Retry</Button>} />;
  }

  const navGroups = [
    {
      label: "Learning",
      items: [
        { id: "section-dashboard", label: "Dashboard", icon: "dashboard" },
        { id: "section-courses", label: "My Courses", icon: "course" },
        { id: "section-pal", label: "PAL Progress", icon: "leaderboard" },
        { id: "section-tasks", label: "Tasks", icon: "task", badge: String(data.tasks?.filter(t => t.status === "pending" || t.status === "overdue").length || 0), badgeTone: "warn" },
      ],
    },
    {
      label: "Workspace",
      items: [
        { id: "launch-current", label: "Moodle link", icon: "moodle" },
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
      title={titleize(currentTab === "learner" ? "Dashboard" : currentTab)}
      subtitle={`${data.profile.category_scope?.toUpperCase()} category · Telite Systems`}
      topbarActions={
        <>
          <Badge tone="accent">PAL {formatPercent(data.hero.pal_score)}</Badge>
          <Button
            tone="primary"
            icon="external"
            onClick={() => handleLaunch(data.hero.current_course?.id)}
            disabled={launchingId === data.hero.current_course?.id}
          >
            {launchingId === data.hero.current_course?.id ? "Launching..." : "Resume Course"}
          </Button>
          <IconButton label="Notifications" icon="bell" onClick={() => setShowNotifications(true)} />
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
      <NotificationDrawer open={showNotifications} onClose={() => setShowNotifications(false)} notifications={data.notifications} />
      <div className="dashboard-stack">
        
        {/* DASHBOARD PAGE */}
        {activeNav === "section-dashboard" && (
          <section id="section-dashboard">
            <div className="hero-banner">
              <div className="learner-hero-row">
                <div>
                  <div className="learner-hero-eyebrow">Learner workspace</div>
                  <h2>{data.hero.headline}</h2>
                  <p>{data.hero.subtext}</p>
                </div>
                <div className="summary-chip summary-chip--hero">
                  <div className="summary-chip__label">PAL score</div>
                  <div className="summary-chip__value">{formatPercent(data.hero.pal_score)}</div>
                </div>
              </div>
              <div className="hero-banner__metrics">
                <div className="hero-metric">
                  <span>Rank</span>
                  <strong>#{data.hero.rank}</strong>
                </div>
                <div className="hero-metric">
                  <span>Streak</span>
                  <strong>{data.hero.streak_days}d</strong>
                </div>
                <div className="hero-metric">
                  <span>Hours logged</span>
                  <strong>{Math.round(data.hero.time_spent_hours)}h</strong>
                </div>
              </div>
              <div className="hero-actions hero-actions--spaced">
                <Button tone="primary" icon="external" onClick={() => handleLaunch(data.hero.current_course?.id)}>
                  Resume Course
                </Button>
                <Button tone="ghost" onClick={() => changeSection({ id: "section-pal" })}>
                  View PAL Report
                </Button>
              </div>
            </div>

            <div className="grid-4">
              <StatCard accent="#059669" label="Courses Completed" value={data.stats.courses_completed} meta="Completed and archived" />
              <StatCard accent="#D97706" label="Courses Remaining" value={data.stats.courses_remaining} meta="Keep pushing the modules" />
              <StatCard accent="#2563EB" label="Avg Quiz Score" value={Math.round(data.stats.avg_quiz_score)} suffix="%" meta="Assessment consistency" />
              <StatCard accent="#7C3AED" label="Cohort Rank" value={`#${data.stats.cohort_rank}`} meta="You lead the cohort" />
            </div>

            <Panel title="Recent Courses" subtitle="Resume where you left off" action={<button className="panel-link" onClick={() => changeSection({ id: 'section-courses' })}>View all</button>}>
              <div className="grid-3">
                {data.courses.slice(0,3).map((course) => (
                  <article className={`course-card ${data.hero.current_course?.id === course.id ? "is-active" : ""}`} key={course.id}>
                    <div className="course-card__header">
                      <div className="course-card__title">{course.name}</div>
                      <Badge tone={course.status === "completed" ? "success" : "neutral"}>
                        {titleize(course.status)}
                      </Badge>
                    </div>
                    <div className="bar-score bar-score--spaced">
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
                    <div className="course-card__footer">
                      <div className="mono course-card__progress-label">
                        {formatPercent(course.completion_pct)} done
                      </div>
                      <Button tone={course.status === "completed" ? "ghost" : "primary"} size="small" onClick={() => handleLaunch(course.id)} disabled={launchingId === course.id}>
                        {launchingId === course.id ? "..." : course.status === "completed" ? "Review" : "Resume"}
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            </Panel>
          </section>
        )}

        {/* MY COURSES PAGE */}
        {activeNav === "section-courses" && (
          <section id="section-courses">
            <Panel title="All Courses" subtitle="Your complete learning path">
              <div className="toolbar toolbar--panel-filter">
                {["all", "in_progress", "completed", "not_started"].map(f => (
                  <label className="chip" key={f}>
                    <input type="radio" checked={courseFilter === f} onChange={() => setCourseFilter(f)} /> {titleize(f.replace("_", " "))}
                  </label>
                ))}
              </div>
              <div className="grid-3">
                {data.courses.filter(c => courseFilter === "all" ? true : c.status === courseFilter).map((course) => (
                  <article className="course-card" key={course.id}>
                    <div className="course-card__header">
                      <div className="course-card__title">{course.name}</div>
                      <Badge tone={course.status === "completed" ? "success" : "neutral"}>
                        {titleize(course.status)}
                      </Badge>
                    </div>
                    <div className="bar-score bar-score--spaced">
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
                    <div className="course-card__footer">
                      <div className="mono course-card__progress-label">
                        {formatPercent(course.completion_pct)} done
                      </div>
                      <Button tone={course.status === "completed" ? "ghost" : "primary"} size="small" onClick={() => handleLaunch(course.id)} disabled={launchingId === course.id}>
                        {launchingId === course.id ? "..." : course.status === "completed" ? "Review" : "Resume"}
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            </Panel>
          </section>
        )}

        {/* PAL PROGRESS PAGE */}
        {activeNav === "section-pal" && (
          <section id="section-pal">
            <div className="hero-banner hero-banner--pal">
              <div className="pal-hero-content">
                <PalRing score={Math.round(data.hero.pal_score)} />
                <div>
                  <h2>PAL Score Analysis</h2>
                  <p>Your holistic performance rating across all modules.</p>
                </div>
              </div>
            </div>
            <Panel title="PAL Dimensions" subtitle="How your score is calculated">
               <div className="pal-list">
                 {[
                   { label: "Course Completion", value: data.pal_breakdown.completion, weight: 0.3 },
                   { label: "Quiz Average", value: data.pal_breakdown.quiz_avg, weight: 0.3 },
                   { label: "Task Completion", value: data.pal_breakdown.task_completion, weight: 0.2 },
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
          </section>
        )}

        {/* TASKS PAGE */}
        {activeNav === "section-tasks" && (
          <section id="section-tasks">
            <Panel title="Task Management" subtitle="Your assigned projects and assessments">
              <div className="toolbar toolbar--panel-filter">
                {["all", "pending", "submitted", "completed", "overdue"].map(f => (
                  <label className="chip" key={f}>
                    <input type="radio" checked={taskFilter === f} onChange={() => setTaskFilter(f)} /> {titleize(f)}
                  </label>
                ))}
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Task</th>
                      <th>Due date</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.tasks.filter(t => taskFilter === "all" ? true : t.status === taskFilter).map((task) => (
                      <tr key={task.id}>
                        <td>
                          <div className="row-title">{task.title}</div>
                        </td>
                        <td>
                          <span className={task.status === "overdue" ? "text-danger" : "muted"}>
                            {formatDateTime(task.due_at)}
                          </span>
                        </td>
                        <td>
                          <Badge tone={task.status === "completed" ? "success" : task.status === "overdue" ? "danger" : "warn"}>
                            {titleize(task.status)}
                          </Badge>
                        </td>
                        <td>
                          {task.status === "pending" || task.status === "overdue" ? (
                            <Button size="small" tone="primary" onClick={() => handleSubmitTask(task.id)} disabled={submittingTaskId === task.id}>
                              {submittingTaskId === task.id ? "Submitting..." : "Mark submitted"}
                            </Button>
                          ) : (
                            <span className="muted">Submitted</span>
                          )}
                        </td>
                      </tr>
                    ))}
                    {data.tasks.filter(t => taskFilter === "all" ? true : t.status === taskFilter).length === 0 && (
                      <tr>
                        <td colSpan="4"><EmptyState title="No tasks" body="You have no tasks matching this filter." /></td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </Panel>
          </section>
        )}

        {/* LEADERBOARD PAGE */}
        {activeNav === "section-leaderboard" && (
          <section id="section-leaderboard">
            <Panel title="Cohort Leaderboard" subtitle={`You are currently #${data.hero.rank} in your cohort`}>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th className="table-cell--rank">Rank</th>
                      <th>Learner</th>
                      <th className="table-cell--right">PAL Score</th>
                      <th className="table-cell--right">Streak</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recommendation?.leaderboard?.map((row, idx) => (
                      <tr key={row.id || idx} className={row.id === data.profile.id ? "is-highlighted" : ""}>
                        <td className="table-cell--rank leaderboard-rank-cell" style={{ color: getRankColor(row.rank) }}>
                          #{row.rank}
                        </td>
                        <td>
                          <div className="leaderboard-row leaderboard-row--compact">
                            <Avatar initials={getInitials(row.full_name)} size={24} />
                            <span>{row.full_name}</span>
                          </div>
                        </td>
                        <td className="mono table-cell--right leaderboard-score-cell" style={{ color: getScoreColor(row.pal_score) }}>
                          {formatPercent(row.pal_score)}
                        </td>
                        <td className="mono table-cell--right text-secondary">
                          {row.streak_days}d
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </section>
        )}

        {/* CERTIFICATES PAGE */}
        {activeNav === "section-certificates" && (
          <section id="section-certificates">
            <Panel title="Certificates" subtitle="Unlock certificates upon track completion">
              <EmptyState title="Track incomplete" body="Complete all assigned courses to unlock your certificate." />
            </Panel>
          </section>
        )}

        {/* PROFILE PAGE */}
        {activeNav === "section-profile" && (
          <section id="section-profile">
            <Panel title="Profile Information" subtitle="Your learner details">
              <div className="grid-2">
                <div className="soft-card">
                  <div className="row-subtitle">Full Name</div>
                  <div className="row-title">{data.profile.full_name}</div>
                </div>
                <div className="soft-card">
                  <div className="row-subtitle">Email Address</div>
                  <div className="row-title">{data.profile.email}</div>
                </div>
                <div className="soft-card">
                  <div className="row-subtitle">Cohort Category</div>
                  <div className="row-title">{data.profile.category_scope}</div>
                </div>
                <div className="soft-card">
                  <div className="row-subtitle">Enrollment Type</div>
                  <div className="row-title">{data.profile.enrollment_type}</div>
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
