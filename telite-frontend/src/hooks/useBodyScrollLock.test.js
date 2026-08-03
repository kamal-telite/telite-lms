import test from "node:test";
import assert from "node:assert/strict";
import { lockScroll, unlockScroll } from "./useBodyScrollLock.js";

test("lockScroll and unlockScroll preserve and restore scroll state", () => {
  const body = { style: {} };
  const html = { style: {} };
  const windowStub = {
    innerWidth: 1200,
    scrollX: 120,
    scrollY: 340,
    scrollTo: () => {},
  };

  global.window = windowStub;
  global.document = {
    body,
    documentElement: html,
  };

  lockScroll();
  assert.equal(body.style.overflow, "hidden");
  assert.equal(html.style.overflow, "hidden");
  assert.equal(body.style.position, "fixed");
  assert.equal(body.style.top, "-340px");

  unlockScroll();
  assert.equal(body.style.overflow, "");
  assert.equal(html.style.overflow, "");
  assert.equal(body.style.position, "");
});
