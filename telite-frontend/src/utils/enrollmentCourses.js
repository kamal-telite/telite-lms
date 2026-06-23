export const DRAFT_COURSE_ENROLLMENT_MESSAGE =
  "Draft courses cannot accept enrollments until published.";

const ENROLLABLE_COURSE_STATUSES = new Set(["active", "published"]);

export function normalizeCourseStatus(course) {
  return String(course?.status || "").trim().toLowerCase();
}

export function isCourseEnrollable(course) {
  return ENROLLABLE_COURSE_STATUSES.has(normalizeCourseStatus(course));
}

export function getCourseEnrollmentDisabledReason(course) {
  const status = normalizeCourseStatus(course);
  if (!status || isCourseEnrollable(course)) {
    return "";
  }
  if (status === "draft") {
    return DRAFT_COURSE_ENROLLMENT_MESSAGE;
  }
  return "Only active or published courses can accept enrollments.";
}

export function toggleEnrollmentCourseSelection(selectedCourseIds, course) {
  if (!isCourseEnrollable(course)) {
    return selectedCourseIds;
  }
  if (selectedCourseIds.includes(course.id)) {
    return selectedCourseIds.filter((value) => value !== course.id);
  }
  return [...selectedCourseIds, course.id];
}
