import test from "node:test";
import assert from "node:assert/strict";

import {
  DRAFT_COURSE_ENROLLMENT_MESSAGE,
  getCourseEnrollmentDisabledReason,
  isCourseEnrollable,
  toggleEnrollmentCourseSelection,
} from "./enrollmentCourses.js";

const activeCourse = { id: "course-active", name: "Active Course", status: "active" };
const publishedCourse = { id: "course-published", name: "Published Course", status: "published" };
const draftCourse = { id: "course-draft", name: "Draft Course", status: "draft" };

test("draft courses remain visible but disabled for enrollment", () => {
  assert.equal(isCourseEnrollable(draftCourse), false);
  assert.equal(getCourseEnrollmentDisabledReason(draftCourse), DRAFT_COURSE_ENROLLMENT_MESSAGE);
});

test("active and published courses are selectable for enrollment", () => {
  assert.equal(isCourseEnrollable(activeCourse), true);
  assert.equal(isCourseEnrollable(publishedCourse), true);
  assert.equal(getCourseEnrollmentDisabledReason(activeCourse), "");
  assert.equal(getCourseEnrollmentDisabledReason(publishedCourse), "");
});

test("selection helper refuses draft courses and toggles enrollable courses", () => {
  assert.deepEqual(toggleEnrollmentCourseSelection([], draftCourse), []);
  assert.deepEqual(toggleEnrollmentCourseSelection([], activeCourse), ["course-active"]);
  assert.deepEqual(toggleEnrollmentCourseSelection(["course-active"], activeCourse), []);
});
