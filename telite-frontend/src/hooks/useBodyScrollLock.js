import { useEffect } from "react";

let activeLocks = 0;
let savedScrollPosition = 0;
let previousBodyOverflow = "";
let previousHtmlOverflow = "";
let previousBodyPosition = "";
let previousBodyTop = "";
let previousBodyWidth = "";
let previousHtmlOverscrollBehavior = "";
let previousBodyOverscrollBehavior = "";

function applyScrollLock() {
  if (typeof document === "undefined") return;

  const { body } = document;
  const html = document.documentElement;

  if (activeLocks === 0) {
    previousBodyOverflow = body?.style.overflow || "";
    previousHtmlOverflow = html?.style.overflow || "";
    previousBodyPosition = body?.style.position || "";
    previousBodyTop = body?.style.top || "";
    previousBodyWidth = body?.style.width || "";
    previousHtmlOverscrollBehavior = html?.style.overscrollBehavior || "";
    previousBodyOverscrollBehavior = body?.style.overscrollBehavior || "";
    savedScrollPosition = window.scrollY || window.pageYOffset || 0;
  }

  activeLocks += 1;

  if (body) {
    body.style.overflow = "hidden";
    body.style.position = "fixed";
    body.style.top = `-${savedScrollPosition}px`;
    body.style.left = "0";
    body.style.right = "0";
    body.style.width = "100%";
    body.style.overscrollBehavior = "none";
  }

  if (html) {
    html.style.overflow = "hidden";
    html.style.overscrollBehavior = "none";
  }
}

function removeScrollLock() {
  if (typeof document === "undefined") return;

  if (activeLocks > 0) {
    activeLocks -= 1;
  }

  if (activeLocks > 0) return;

  const { body } = document;
  const html = document.documentElement;

  if (body) {
    body.style.overflow = previousBodyOverflow;
    body.style.position = previousBodyPosition;
    body.style.top = previousBodyTop;
    body.style.left = "";
    body.style.right = "";
    body.style.width = previousBodyWidth;
    body.style.overscrollBehavior = previousBodyOverscrollBehavior;
  }

  if (html) {
    html.style.overflow = previousHtmlOverflow;
    html.style.overscrollBehavior = previousHtmlOverscrollBehavior;
  }

  if (typeof window !== "undefined") {
    window.scrollTo(0, savedScrollPosition);
  }
}

export function lockScroll() {
  applyScrollLock();
}

export function unlockScroll() {
  removeScrollLock();
}

export function useBodyScrollLock(isLocked) {
  useEffect(() => {
    if (!isLocked) {
      unlockScroll();
      return undefined;
    }

    lockScroll();
    return () => unlockScroll();
  }, [isLocked]);
}
