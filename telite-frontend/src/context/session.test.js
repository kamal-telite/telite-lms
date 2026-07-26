import test from "node:test";
import assert from "node:assert/strict";

import { getDefaultRoute, mergeAuthPayload, mergeSessionUser } from "./session.js";

test("mergeAuthPayload preserves a non-learner role over a stale learner role", () => {
  const existingSession = {
    authenticated: true,
    user: {
      user_id: "user-1",
      role: "category_admin",
      category_scope: "ats",
      is_platform_admin: false,
    },
  };

  const merged = mergeAuthPayload(existingSession, {
    user: {
      user_id: "user-1",
      role: "learner",
    },
  });

  assert.equal(merged.user.role, "category_admin");
  assert.equal(getDefaultRoute(merged.user), "/categories/ats/admin");
});

test("mergeSessionUser does not let a learner role replace an existing admin role", () => {
  const existingSession = {
    authenticated: true,
    user: {
      user_id: "user-1",
      role: "category_admin",
      category_scope: "ats",
      is_platform_admin: false,
    },
  };

  const merged = mergeSessionUser(existingSession, {
    role: "learner",
    name: "Category Admin",
  });

  assert.equal(merged.user.role, "category_admin");
  assert.equal(getDefaultRoute(merged.user), "/categories/ats/admin");
});

test("getDefaultRoute does not fall back to learner for unknown roles", () => {
  assert.equal(getDefaultRoute({ role: "", category_scope: "ats" }), "/login");
  assert.equal(getDefaultRoute({ role: "unknown_role", category_scope: "ats" }), "/login");
});
