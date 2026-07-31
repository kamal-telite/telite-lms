import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * FocusManager handles accessibility and keyboard scrolling routing 
 * after page transitions.
 * 
 * Priority:
 * 1. Active modal/dialog
 * 2. Element with data-autofocus
 * 3. Main content landmark (<main>)
 * 4. Document body (Browser default)
 */
export function FocusManager() {
  const location = useLocation();

  useEffect(() => {
    // Wait for the DOM to render the new route
    const timeoutId = setTimeout(() => {
      
      // 1. Check for an active modal or dialog
      const activeModal = document.querySelector('dialog[open], [role="dialog"]');
      if (activeModal) {
        // If it's already focused, leave it alone.
        if (!activeModal.contains(document.activeElement)) {
          // Attempt to focus the modal container or its first focusable child
          activeModal.focus();
        }
        return;
      }

      // 2. First meaningful interactive element specifically marked
      const autofocusEl = document.querySelector('[data-autofocus="true"]');
      if (autofocusEl) {
        autofocusEl.focus();
        return;
      }

      // 3. Main content landmark (<main> typically used by PageScroll)
      const mainEl = document.querySelector('main');
      if (mainEl) {
        // Ensure it can receive programmatic focus for keyboard scrolling
        if (!mainEl.hasAttribute('tabindex')) {
          mainEl.setAttribute('tabindex', '-1');
        }
        // focus() on a tabindex="-1" element enables arrow/space scrolling
        // without showing a default outline ring (unless overridden).
        mainEl.focus({ preventScroll: true });
        return;
      }

      // 4. Browser default / Body fallback
      if (document.activeElement && document.activeElement !== document.body) {
        document.activeElement.blur();
      }

    }, 50); // 50ms buffer for React render

    return () => clearTimeout(timeoutId);
  }, [location.pathname]); // Trigger only on path changes

  return null;
}
