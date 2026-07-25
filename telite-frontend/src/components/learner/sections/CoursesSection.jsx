import { Panel } from "../../common/ui";
import { CourseCard } from "../CourseCard";
import { titleize } from "../../../utils/formatters";

/**
 * CoursesSection - My Courses view with filtering
 */
export function CoursesSection({
  courses,
  courseFilter,
  onFilterChange,
  onLaunch,
  launchingCourseId,
  animateProgress,
}) {
  return (
    <section id="section-courses">
      <Panel title="All Courses" subtitle="Your complete learning path">
        <div className="toolbar" style={{ marginBottom: 16 }}>
          {["all", "in_progress", "completed", "not_started"].map((f) => (
            <label className="chip" key={f}>
              <input
                type="radio"
                checked={courseFilter === f}
                onChange={() => onFilterChange(f)}
              />
              {titleize(f.replace("_", " "))}
            </label>
          ))}
        </div>
        <div className="grid-3">
          {courses
            .filter((c) =>
              courseFilter === "all" ? true : c.status === courseFilter
            )
            .map((course) => (
              <CourseCard
                key={String(course.id || course.course_id)}
                course={course}
                isLoading={
                  launchingCourseId === String(course.id || course.course_id)
                }
                onLaunch={onLaunch}
                animateProgress={animateProgress}
              />
            ))}
        </div>
      </Panel>
    </section>
  );
}
