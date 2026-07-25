import { useState, useCallback } from 'react';

/**
 * Custom hook for modal state management
 * @param {boolean} initialOpen - Initial open state
 * @returns {object} - Modal state and handlers
 */
export function useModal(initialOpen = false) {
  const [isOpen, setIsOpen] = useState(initialOpen);

  const open = useCallback(() => {
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
  }, []);

  const toggle = useCallback(() => {
    setIsOpen(prev => !prev);
  }, []);

  return {
    isOpen,
    open,
    close,
    toggle,
    setIsOpen
  };
}
