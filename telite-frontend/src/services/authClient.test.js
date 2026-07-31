import test from "node:test";
import assert from "node:assert/strict";
import { shouldAttemptRefresh } from "./client.js";

test("does not auto-refresh profile update requests on 409 conflict", () => {
  const request = {
    url: "/auth/me",
  };
  assert.equal(shouldAttemptRefresh(request, { response: { status: 409 } }), false);
});
