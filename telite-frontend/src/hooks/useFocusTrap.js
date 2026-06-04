import React, { useEffect, useRef } from 'react';

/**
 * Custom focus trap for accessibility.
 * Ensures focus remains within the modal/panel while open.
 */
export const useFocusTrap = (isOpen, ref) => {
  useEffect(() => {
    if (!isOpen || !ref.current) return;

    const focusableElements = ref.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleKeyDown = (e) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    ref.current.addEventListener('keydown', handleKeyDown);
    firstElement?.focus();

    return () => ref.current?.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, ref]);
};
