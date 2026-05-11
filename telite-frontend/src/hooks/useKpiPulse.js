import { useEffect, useRef, useState } from "react";

/**
 * Detects KPI value changes and returns a map of keys that just changed,
 * suitable for triggering a brief CSS pulse animation.
 *
 * Uses JSON serialization to compare by *value* — not by object identity —
 * so a new `{}` default created every render won't trigger false positives.
 */
export function useKpiPulse(values) {
  const previousJsonRef = useRef("");
  const previousValuesRef = useRef({});
  const [pulseMap, setPulseMap] = useState({});

  useEffect(() => {
    const currentJson = JSON.stringify(values || {});

    // Skip if the serialized values haven't changed (identity-safe check)
    if (currentJson === previousJsonRef.current) {
      return undefined;
    }

    const previous = previousValuesRef.current;
    const changed = Object.keys(values || {}).reduce((accumulator, key) => {
      if (previous[key] !== undefined && previous[key] !== values[key]) {
        accumulator[key] = true;
      }
      return accumulator;
    }, {});

    previousJsonRef.current = currentJson;
    previousValuesRef.current = { ...(values || {}) };

    if (Object.keys(changed).length) {
      setPulseMap(changed);
      const timeout = window.setTimeout(() => setPulseMap({}), 320);
      return () => window.clearTimeout(timeout);
    }

    return undefined;
  }, [values]);

  return pulseMap;
}
