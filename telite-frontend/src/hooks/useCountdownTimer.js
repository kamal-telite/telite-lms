import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook for managing a synchronized countdown timer
 * 
 * @param {Object} params - Timer parameters
 * @param {number} params.minimumTimeSeconds - Minimum time requirement in seconds
 * @param {number} params.timeSpentSeconds - Time already spent in seconds
 * @param {boolean} params.isActive - Whether the timer should be running
 * @param {boolean} params.isCompleted - Whether the requirement is already met
 * 
 * @returns {Object} Timer state and utilities
 * @returns {number} remainingSeconds - Remaining time in seconds
 * @returns {string} formattedTime - MM:SS formatted remaining time
 * @returns {boolean} isTimeMet - Whether time requirement is met
 * @returns {boolean} isExpired - Whether timer has reached 00:00
 */
export function useCountdownTimer({ 
  minimumTimeSeconds = 0, 
  timeSpentSeconds = 0, 
  isActive = true,
  isCompleted = false 
}) {
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const intervalRef = useRef(null);
  const lastUpdateTimeRef = useRef(null);
  const isInitializedRef = useRef(false);

  // Calculate initial remaining time
  const calculateRemaining = useCallback(() => {
    if (!minimumTimeSeconds || minimumTimeSeconds <= 0) return 0;
    if (isCompleted) return 0;
    return Math.max(0, minimumTimeSeconds - timeSpentSeconds);
  }, [minimumTimeSeconds, timeSpentSeconds, isCompleted]);

  // Format seconds to MM:SS
  const formatMMSS = useCallback((seconds) => {
    const total = Math.max(0, Number(seconds) || 0);
    const minutes = Math.floor(total / 60);
    const secs = Math.floor(total % 60);
    return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }, []);

  // Initialize or reset timer when parameters change
  useEffect(() => {
    const newRemaining = calculateRemaining();
    setRemainingSeconds(newRemaining);
    lastUpdateTimeRef.current = Date.now();
    isInitializedRef.current = true;
  }, [calculateRemaining]);

  // Countdown interval - only depends on activation state, not remainingSeconds
  useEffect(() => {
    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // Don't start if not active, already completed, or no time requirement
    if (!isActive || isCompleted || !minimumTimeSeconds || minimumTimeSeconds <= 0) {
      return;
    }

    // Don't start if not yet initialized
    if (!isInitializedRef.current) {
      return;
    }

    // Start countdown
    intervalRef.current = setInterval(() => {
      const now = Date.now();
      const elapsed = (now - lastUpdateTimeRef.current) / 1000;
      lastUpdateTimeRef.current = now;

      // Only decrement if tab is visible and focused
      if (document.visibilityState === 'visible' && document.hasFocus()) {
        setRemainingSeconds(prev => {
          const newRemaining = Math.max(0, prev - elapsed);
          if (newRemaining <= 0) {
            // Clear interval when reaching zero
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
            return 0;
          }
          return newRemaining;
        });
      }
    }, 1000); // Update every second

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isActive, isCompleted, minimumTimeSeconds]);

  // Handle visibility change - pause when tab is hidden, resume when visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        lastUpdateTimeRef.current = Date.now();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  const isTimeMet = isCompleted || remainingSeconds <= 0;
  const isExpired = remainingSeconds <= 0 && minimumTimeSeconds > 0;
  const formattedTime = formatMMSS(remainingSeconds);

  return {
    remainingSeconds,
    formattedTime,
    isTimeMet,
    isExpired
  };
}
