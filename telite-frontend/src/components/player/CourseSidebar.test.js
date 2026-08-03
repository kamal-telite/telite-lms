import test from "node:test";
import assert from "node:assert/strict";
import { shouldShowSectionCountdown } from "./courseSidebarCountdown.js";

test("sidebar countdown remains hidden when the section is unlocked or already satisfied", () => {
  assert.equal(
    shouldShowSectionCountdown({
      isSectionLocked: false,
      isSectionCompleted: false,
      minimumTimeSeconds: 120,
      timeSpentSeconds: 30,
    }),
    false,
  );

  assert.equal(
    shouldShowSectionCountdown({
      isSectionLocked: true,
      isSectionCompleted: false,
      minimumTimeSeconds: 120,
      timeSpentSeconds: 120,
    }),
    false,
  );
});

test("sidebar countdown shows only while the backend still reports the section as locked and waiting", () => {
  assert.equal(
    shouldShowSectionCountdown({
      isSectionLocked: true,
      isSectionCompleted: false,
      minimumTimeSeconds: 120,
      timeSpentSeconds: 30,
    }),
    true,
  );
});
