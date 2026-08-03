import { Button, Panel, StatCard, EmptyState } from "../../common/ui";
import { CourseCard } from "../CourseCard";
import {
  formatPercent,
  formatLearningTime,
  titleize,
} from "../../../utils/formatters";

const formatLoggedHours = (hero) => {
  const seconds = hero.total_time_seconds !== undefined 
    ? hero.total_time_seconds 
    : (hero.pal_time_spent_hours || hero.time_spent_hours || 0) * 3600;

  if (!seconds || seconds < 60) return "0h";
  const totalMinutes = Math.floor(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  
  if (hours > 0 && minutes > 0) {
    return `${hours}h ${minutes}m`;
  } else if (hours > 0) {
    return `${hours}h`;
  } else {
    return `${minutes}m`;
  }
};

/**
 * DashboardSection - Main dashboard view with hero banner and recent courses
 */
export function DashboardSection({
  hero,
  stats,
  courses,
  animateProgress,
  onLaunch,
  launchingCourseId,
  onNavigateSection,
}) {
  return (
    <section id="section-dashboard">
      <div className="hero-banner">
        <div
          className="leaderboard-row"
          style={{
            padding: 0,
            borderBottom: 0,
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div
              className="eyebrow"
              style={{ margin: 0, color: "rgba(255,255,255,0.8)" }}
            >
              Learner workspace
            </div>
            <h2>{hero.headline}</h2>
            <p>{hero.subtext}</p>
          </div>
          <div
            className="summary-chip"
            style={{
              background: "rgba(255,255,255,0.14)",
              borderColor: "rgba(255,255,255,0.24)",
            }}
          >
            <div
              className="summary-chip__label"
              style={{ color: "rgba(255,255,255,0.75)" }}
            >
              PAL score
            </div>
            <div className="summary-chip__value" style={{ color: "#fff" }}>
              {formatPercent(hero.pal_score)}
            </div>
          </div>
        </div>
        <div className="hero-banner__metrics">
          <div className="hero-metric">
            <span>Rank</span>
            <strong>{hero.rank == null ? "-" : `#${hero.rank}`}</strong>
          </div>
          <div className="hero-metric">
            <span>Streak</span>
            <strong>{hero.streak_days || 0}d</strong>
          </div>
          <div className="hero-metric">
            <span>Hours logged</span>
            <strong>{formatLoggedHours(hero)}</strong>
          </div>
        </div>
        <div className="hero-actions" style={{ marginTop: 18 }}>
          <Button
            tone="primary"
            icon="external"
            onClick={() => onLaunch(hero.current_course?.id)}
          >
            Resume Course
          </Button>
          <Button tone="ghost" onClick={() => onNavigateSection({ id: "section-pal" })}>
            View PAL Report
          </Button>
        </div>
      </div>

      <div className="grid-4">
        <StatCard
          accent="#059669"
          label="Courses Completed"
          value={stats.courses_completed ?? 0}
          meta="Completed and archived"
        />
        <StatCard
          accent="#D97706"
          label="Today's Learning Time"
          value={formatLearningTime(hero.today_time_seconds || 0)}
          meta="Active time only"
        />
        <StatCard
          accent="#2563EB"
          label="Total Time Spent"
          value={`${Math.round(hero.time_spent_hours || 0)}h`}
          meta={hero.last_session ? "Last session recorded" : "No sessions yet"}
        />
        <StatCard
          accent="#7C3AED"
          label="Assignment Status"
          value={
            hero.assignment_status
              ? titleize(String(hero.assignment_status).replace("_", " "))
              : "None"
          }
          meta={`Rank #${stats.cohort_rank == null ? "-" : stats.cohort_rank}`}
        />
      </div>

      <Panel
        title="Recent Courses"
        subtitle="Resume where you left off"
        action={
          <button
            className="panel-link"
            onClick={() => onNavigateSection({ id: "section-courses" })}
          >
            View all →
          </button>
        }
      >
        <div className="grid-3">
          {courses.slice(0, 3).map((course) => (
            <CourseCard
              key={String(course.id || course.course_id)}
              course={course}
              heroCurrentCourseId={hero.current_course?.id}
              isLoading={launchingCourseId === String(course.id || course.course_id)}
              onLaunch={onLaunch}
              animateProgress={animateProgress}
            />
          ))}
        </div>
      </Panel>
    </section>
  );
}
