import test from "node:test";
import assert from "node:assert/strict";

import { shouldAttemptRefresh } from "./client.js";

test("does not auto-refresh a bootstrap /auth/me request after login", () => {
  const request = {
    url: "/auth/me",
    _skipRefresh: true,
  };

  assert.equal(shouldAttemptRefresh(request, { response: { status: 401 } }), false);
});

test("still auto-refreshes protected requests that are not part of bootstrap", () => {
  const request = {
    url: "/dashboard/learner",
  };

  assert.equal(shouldAttemptRefresh(request, { response: { status: 401 } }), true);
});
