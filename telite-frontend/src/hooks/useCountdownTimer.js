import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook for managing a synchronized countdown timer
 *
 * @param {Object} params - Timer parameters
 * @param {number} params.minimumTimeSeconds - Minimum time requirement in seconds
 * @param {number} params.timeSpentSeconds - Time already spent in seconds
 * @param {boolean} params.isActive - Whether the timer should be running
 * @param {boolean} params.isCompleted - Whether the requirement is already met
 * @param {string|number|null} params.resetKey - Changes when switching section/module (resets local expiry)
 *
 * @returns {Object} Timer state and utilities
 */
export function useCountdownTimer({
  minimumTimeSeconds = 0,
  timeSpentSeconds = 0,
  isActive = true,
  isCompleted = false,
  resetKey = null,
}) {
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const intervalRef = useRef(null);
  const lastUpdateTimeRef = useRef(null);
  const isInitializedRef = useRef(false);
  const [initializedKey, setInitializedKey] = useState(null);
  const expiredKeyRef = useRef(null);
  const prevResetKeyRef = useRef(resetKey);

  const serverRequirementMet =
    isCompleted ||
    (minimumTimeSeconds > 0 && timeSpentSeconds >= minimumTimeSeconds);

  const calculateRemaining = useCallback(() => {
    if (!minimumTimeSeconds || minimumTimeSeconds <= 0) return 0;
    if (serverRequirementMet) return 0;
    return Math.max(0, minimumTimeSeconds - timeSpentSeconds);
  }, [minimumTimeSeconds, timeSpentSeconds, serverRequirementMet]);

  const formatMMSS = useCallback((seconds) => {
    const total = Math.max(0, Number(seconds) || 0);
    const minutes = Math.floor(total / 60);
    const secs = Math.floor(total % 60);
    return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }, []);

  useEffect(() => {
    const resetKeyChanged = prevResetKeyRef.current !== resetKey;
    prevResetKeyRef.current = resetKey;

    if (resetKeyChanged) {
      expiredKeyRef.current = null;
    }

    // Only expire immediately if the section is already marked as completed
    // Don't expire just because time requirement is met - let the timer count down naturally
    if (isCompleted) {
      expiredKeyRef.current = resetKey;
      setRemainingSeconds(0);
      lastUpdateTimeRef.current = Date.now();
      isInitializedRef.current = true;
      setInitializedKey(resetKey);
      return;
    }

    if (expiredKeyRef.current === resetKey) {
      setRemainingSeconds(0);
      lastUpdateTimeRef.current = Date.now();
      setInitializedKey(resetKey);
      return;
    }

    const newRemaining = calculateRemaining();

    if (resetKeyChanged || !isInitializedRef.current) {
      setRemainingSeconds(newRemaining);
    } else {
      setRemainingSeconds((prev) => {
        if (prev <= 0) return 0;
        return Math.min(prev, newRemaining);
      });
    }

    lastUpdateTimeRef.current = Date.now();
    isInitializedRef.current = true;
    setInitializedKey(resetKey);
  }, [resetKey, calculateRemaining, isCompleted]);

  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (
      !isActive ||
      serverRequirementMet ||
      expiredKeyRef.current === resetKey ||
      !minimumTimeSeconds ||
      minimumTimeSeconds <= 0
    ) {
      return;
    }

    if (!isInitializedRef.current) {
      return;
    }

    intervalRef.current = setInterval(() => {
      const now = Date.now();
      const elapsed = (now - lastUpdateTimeRef.current) / 1000;
      lastUpdateTimeRef.current = now;

      if (document.visibilityState === 'visible' && document.hasFocus()) {
        setRemainingSeconds((prev) => {
          const newRemaining = Math.max(0, prev - elapsed);
          if (newRemaining <= 0) {
            expiredKeyRef.current = resetKey;
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
            return 0;
          }
          return newRemaining;
        });
      }
    }, 1000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isActive, serverRequirementMet, minimumTimeSeconds, resetKey]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        lastUpdateTimeRef.current = Date.now();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  const hasRequirement = minimumTimeSeconds > 0;
  const isCurrentTimerInitialized = initializedKey === resetKey;
  const isExpiredLocally = expiredKeyRef.current === resetKey;
  const isTimeMet =
    !hasRequirement ||
    serverRequirementMet ||
    isExpiredLocally ||
    (isCurrentTimerInitialized && remainingSeconds <= 0);
  const isExpired =
    hasRequirement && (
      serverRequirementMet ||
      isExpiredLocally ||
      (isCurrentTimerInitialized && remainingSeconds <= 0)
    );
  const displayRemainingSeconds = isCurrentTimerInitialized
    ? remainingSeconds
    : calculateRemaining();
  const formattedTime = formatMMSS(displayRemainingSeconds);

  return {
    remainingSeconds: displayRemainingSeconds,
    formattedTime,
    isTimeMet,
    isExpired,
  };
}
