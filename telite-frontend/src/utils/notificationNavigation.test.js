import test from "node:test";
import assert from "node:assert/strict";

import {
  getNavigableNotificationRoute,
  isSupportedNotificationRoute,
} from "./notificationNavigation.js";

test("certificate notification payload routes to learner certificates", () => {
  const notification = {
    type: "certificate_awarded",
    metadata_json: {
      route: "/learner/certificates",
      route_name: "learner_certificates",
      course_id: "course-cert-1",
      certificate_id: "certificate-1",
      verification_token: "verify-token",
    },
  };

  assert.equal(getNavigableNotificationRoute(notification), "/learner/certificates");
});

test("learning path unlock notification payload routes to learner courses", () => {
  const notification = {
    type: "learning_path_unlocked",
    metadata_json: {
      route: "/learner/courses",
      route_name: "learner_courses",
      path_id: 7101,
      course_id: "lpn-course-2",
    },
  };

  assert.equal(getNavigableNotificationRoute(notification), "/learner/courses");
});

test("learning path assignment and completion payloads route to learner paths", () => {
  const assignedNotification = {
    type: "learning_path_assigned",
    metadata_json: {
      route: "/learner/paths",
      route_name: "learner_paths",
      path_id: 7101,
    },
  };
  const completedNotification = {
    type: "learning_path_completed",
    metadata_json: {
      route: "/learner/paths",
      route_name: "learner_paths",
      path_id: 7101,
    },
  };

  assert.equal(getNavigableNotificationRoute(assignedNotification), "/learner/paths");
  assert.equal(getNavigableNotificationRoute(completedNotification), "/learner/paths");
});

test("notification navigation rejects unsupported API and legacy course routes", () => {
  assert.equal(isSupportedNotificationRoute("/api/certificates/course-cert-1"), false);
  assert.equal(isSupportedNotificationRoute("/courses/course-cert-1"), false);
  assert.equal(isSupportedNotificationRoute("/authoring/courses/course-cert-1"), false);
});

test("notification navigation accepts mounted route families", () => {
  assert.equal(isSupportedNotificationRoute("/learner/certificates"), true);
  assert.equal(isSupportedNotificationRoute("/categories/native/builder/course-1"), true);
  assert.equal(isSupportedNotificationRoute("/platform-admin/admins"), true);
  assert.equal(isSupportedNotificationRoute("/super-admin"), true);
});
