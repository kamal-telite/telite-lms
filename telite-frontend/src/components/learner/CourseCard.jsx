import { Badge, Button } from "../common/ui";
import { getCompletionColor, formatPercent, titleize } from "../../utils/formatters";

/**
 * CourseCard - Reusable course card component for displaying course information and progress
 * 
 * @param {object} course - Course data object
 * @param {string} course.id - Course ID
 * @param {string} course.course_id - Alternative course ID field
 * @param {string} course.name - Course name
 * @param {string} course.status - Course status (completed, in_progress, not_started)
 * @param {number} course.completion_pct - Completion percentage
 * @param {string} course.category_slug - Category slug
 * @param {string} course.tier - Course tier
 * @param {string} course.cover_image_url - Course cover image URL
 * @param {string} heroCurrentCourseId - ID of current/hero course (for visual highlighting)
 * @param {boolean} isLoading - Whether course is currently loading
 * @param {function} onLaunch - Callback when launch/continue button is clicked
 * @param {boolean} animateProgress - Whether to animate progress bar
 */
export function CourseCard({
  course,
  heroCurrentCourseId,
  isLoading = false,
  onLaunch,
  animateProgress = false,
}) {
  const courseId = String(course.id || course.course_id);
  const isActive = heroCurrentCourseId === courseId;
  const isCompleted = course.status === "completed";
  const isInProgress = course.status === "in_progress";
  const isLocked = course.status === "locked";

  const placeholderSvg = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="225" viewBox="0 0 400 225"><rect width="100%" height="100%" fill="%23f1f5f9"/><g transform="translate(200, 112.5)" text-anchor="middle" fill="%2364748b"><rect x="-60" y="-30" width="120" height="60" rx="6" fill="%23cbd5e1"/><text font-family="system-ui, sans-serif" font-weight="bold" font-size="28" y="10" fill="%23475569">${
    course.name ? encodeURIComponent(course.name.substring(0, 2).toUpperCase()) : "CO"
  }</text></g></svg>`;

  // Premium Status Badge Rendering Details
  let badgeText = titleize(course.status);
  let badgeBg = "rgba(107, 114, 128, 0.1)";
  let badgeColor = "#6B7280";
  let badgeIcon = "⚪";

  if (isCompleted) {
    badgeBg = "rgba(16, 185, 129, 0.15)";
    badgeColor = "#10B981";
    badgeIcon = "✔";
    badgeText = "Completed";
  } else if (isInProgress) {
    badgeBg = "rgba(59, 130, 246, 0.15)";
    badgeColor = "#3B82F6";
    badgeIcon = "🟦";
    badgeText = "In Progress";
  } else if (isLocked) {
    badgeBg = "rgba(220, 38, 38, 0.1)";
    badgeColor = "#DC2626";
    badgeIcon = "🔒";
    badgeText = "Locked";
  } else if (course.status === "not_started") {
    badgeBg = "rgba(156, 163, 175, 0.15)";
    badgeColor = "#9CA3AF";
    badgeIcon = "⚪";
    badgeText = "Not Started";
  }

  return (
    <article
      className={`course-card ${isActive ? "is-active" : ""}`}
      style={{
        display: "flex",
        flexDirection: "column",
        background: "#ffffff",
        border: isActive ? "2px solid var(--primary, #4648d4)" : "1px solid #e5e7eb",
        borderRadius: "12px",
        boxShadow: isActive ? "0 8px 24px rgba(70,72,212,0.15)" : "0 2px 8px rgba(0,0,0,0.06)",
        overflow: "hidden",
        height: "100%",
        minHeight: "280px",
        transition: "transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease",
        cursor: "pointer",
        position: "relative"
      }}
      onMouseEnter={(e) => {
        if (window.innerWidth > 768) {
          e.currentTarget.style.transform = "translateY(-2px)";
          e.currentTarget.style.boxShadow = "0 12px 32px rgba(0,0,0,0.1)";
          e.currentTarget.style.borderColor = isActive ? "var(--primary, #4648d4)" : "#d1d5db";
        }
      }}
      onMouseLeave={(e) => {
        if (window.innerWidth > 768) {
          e.currentTarget.style.transform = "none";
          e.currentTarget.style.boxShadow = isActive ? "0 8px 24px rgba(70,72,212,0.15)" : "0 2px 8px rgba(0,0,0,0.06)";
          e.currentTarget.style.borderColor = isActive ? "var(--primary, #4648d4)" : "#e5e7eb";
        }
      }}
    >
      <div 
        className="course-card__cover"
        style={{
          width: "100%",
          height: "160px",
          overflow: "hidden",
          background: "#f8fafc",
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0
        }}
      >
        <img
          src={course.cover_image_url || placeholderSvg}
          loading="lazy"
          alt={course.name}
          onError={(event) => {
            if (event.currentTarget.src !== placeholderSvg) {
              event.currentTarget.src = placeholderSvg;
            }
          }}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: "center center",
            transition: "transform 0.3s ease"
          }}
        />
      </div>

      <div 
        className="course-card__content"
        style={{
          display: "flex",
          flexDirection: "column",
          flex: 1,
          padding: "16px",
          gap: "10px"
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "6px", flexGrow: 1 }}>
          {/* Category */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span 
              style={{ 
                fontSize: "11px", 
                fontWeight: 500, 
                color: "#6b7280", 
                textTransform: "uppercase",
                letterSpacing: "0.5px",
                lineHeight: "1.2"
              }}
            >
              {titleize(course.category_slug?.replace("-", " ") || "General")}
            </span>
          </div>

          {/* Title */}
          <h3 
            className="course-card__title"
            style={{
              fontSize: "15px",
              fontWeight: 600,
              color: "#111827",
              margin: 0,
              lineHeight: "1.4",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
              textOverflow: "ellipsis",
              height: "42px"
            }}
          >
            {course.name}
          </h3>

          {/* Status Badge */}
          <div style={{ display: "flex", marginTop: "2px" }}>
            <span 
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "3px",
                padding: "3px 8px",
                borderRadius: "6px",
                fontSize: "10px",
                fontWeight: 500,
                background: badgeBg,
                color: badgeColor,
                border: "none"
              }}
            >
              <span style={{ fontSize: "10px" }}>{badgeText}</span>
            </span>
          </div>
        </div>

        {/* Progress Section */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "11px", fontWeight: 500, color: "#6b7280" }}>
              Progress
            </span>
            <span style={{ fontSize: "12px", fontWeight: 600, color: "#111827" }}>
              {formatPercent(course.completion_pct)}
            </span>
          </div>
          <div 
            style={{
              width: "100%",
              height: "4px",
              background: "#e5e7eb",
              borderRadius: "2px",
              overflow: "hidden"
            }}
          >
            <div
              style={{
                height: "100%",
                width: animateProgress ? `${course.completion_pct}%` : "0%",
                background: getCompletionColor(course.completion_pct),
                borderRadius: "inherit",
                transition: "width 0.8s cubic-bezier(0.16, 1, 0.3, 1)"
              }}
            />
          </div>
        </div>

        {/* Primary Action Button */}
        <button
          className="course-card__action"
          onClick={() => onLaunch(courseId)}
          disabled={isLoading}
          style={{
            width: "100%",
            height: "36px",
            borderRadius: "6px",
            fontSize: "13px",
            fontWeight: 500,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            marginTop: "auto",
            background: isCompleted ? "#f3f4f6" : "#3b82f6",
            color: isCompleted ? "#374151" : "#ffffff",
            border: "none",
            cursor: isLoading ? "not-allowed" : "pointer",
            transition: "background-color 0.2s ease, transform 0.1s ease",
            opacity: isLoading ? 0.7 : 1
          }}
          onMouseEnter={(e) => {
            if (!isLoading) {
              e.currentTarget.style.background = isCompleted ? "#e5e7eb" : "#2563eb";
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = isCompleted ? "#f3f4f6" : "#3b82f6";
          }}
        >
          {isLoading ? "Loading..." : isCompleted ? "Review Course" : "Resume Learning"}
        </button>
      </div>
    </article>
  );
}
