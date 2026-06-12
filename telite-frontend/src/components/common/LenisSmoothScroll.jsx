import { useEffect } from "react";
import { useLocation } from "react-router-dom";

const MARKETING_PATHS = new Set(["/", "/login", "/signup", "/accept-invite", "/set-password", "/reset-password"]);

function isMarketingRoute(pathname) {
  return MARKETING_PATHS.has(pathname);
}

/**
 * Lenis smooth scroll runs only on public/marketing routes.
 * Dashboard and authoring UIs use native scrolling for lower input latency.
 */
export default function LenisSmoothScroll() {
  const { pathname } = useLocation();

  useEffect(() => {
    if (!isMarketingRoute(pathname)) {
      return undefined;
    }

    let lenis = null;
    let rafId = null;
    let cancelled = false;

    (async () => {
      const { default: Lenis } = await import("lenis");
      if (cancelled) return;

      lenis = new Lenis({
        duration: 1.2,
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        smoothWheel: true,
        smoothTouch: false,
      });

      const raf = (time) => {
        lenis.raf(time);
        rafId = requestAnimationFrame(raf);
      };
      rafId = requestAnimationFrame(raf);
    })();

    return () => {
      cancelled = true;
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
      }
      lenis?.destroy();
    };
  }, [pathname]);

  return null;
}
