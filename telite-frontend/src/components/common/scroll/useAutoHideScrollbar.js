import { useEffect, useRef } from 'react';
import { useScrollContext } from './ScrollProvider';

export function useAutoHideScrollbar(ref, disabled = false) {
  const { prefersReducedMotion } = useScrollContext();
  const isScrollingRef = useRef(false);
  const hideTimeoutRef = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || disabled) return;

    // If reduced motion is preferred, we don't apply the scrolling attribute at all
    // so it doesn't trigger opacity/color transitions in CSS.
    if (prefersReducedMotion) {
      return;
    }

    let ticking = false;

    const handleScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          if (!isScrollingRef.current) {
            isScrollingRef.current = true;
            el.setAttribute('data-scrolling', 'true');
          }

          if (hideTimeoutRef.current) {
            clearTimeout(hideTimeoutRef.current);
          }

          hideTimeoutRef.current = setTimeout(() => {
            isScrollingRef.current = false;
            if (el) el.removeAttribute('data-scrolling');
          }, 600); // hide after 600ms of no scroll

          ticking = false;
        });
        ticking = true;
      }
    };

    // Use passive listener to ensure scroll performance isn't blocked
    el.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      el.removeEventListener('scroll', handleScroll);
      if (hideTimeoutRef.current) {
        clearTimeout(hideTimeoutRef.current);
      }
    };
  }, [ref, disabled, prefersReducedMotion]);
}
