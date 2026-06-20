import React, { createContext, useContext, useCallback, useEffect, useMemo, useState } from "react";
import { updateThemePreference } from "../services/client";

const ThemeContext = createContext({
  mode: "system",
  theme: "dark",
  resolvedTheme: "dark",
  toggleTheme: () => {},
  setTheme: () => {},
});

const THEME_STORAGE_KEY = "telite_theme";
const THEME_MODES = new Set(["light", "dark", "system"]);

function normalizeMode(value) {
  return THEME_MODES.has(value) ? value : null;
}

function getStoredMode() {
  if (typeof window === "undefined") return null;
  try {
    return normalizeMode(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return null;
  }
}

function getSystemTheme() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return "dark";
  }
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function resolveTheme(mode, systemTheme) {
  return mode === "system" ? systemTheme : mode;
}

export function ThemeProvider({ children, session, onSessionChange }) {
  const [systemTheme, setSystemTheme] = useState(getSystemTheme);
  const [mode, setModeState] = useState(() => getStoredMode() || "system");

  const resolvedTheme = resolveTheme(mode, systemTheme);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return undefined;
    }

    const mediaQuery = window.matchMedia("(prefers-color-scheme: light)");
    const handleChange = () => setSystemTheme(getSystemTheme());
    mediaQuery.addEventListener?.("change", handleChange);
    mediaQuery.addListener?.(handleChange);
    return () => {
      mediaQuery.removeEventListener?.("change", handleChange);
      mediaQuery.removeListener?.(handleChange);
    };
  }, []);

  useEffect(() => {
    const dbMode = normalizeMode(session?.user?.theme_preference);
    if (dbMode && dbMode !== mode) {
      setModeState(dbMode);
      try {
        window.localStorage.setItem(THEME_STORAGE_KEY, dbMode);
      } catch {
        // localStorage unavailable; DB remains source of truth.
      }
    }
  }, [session?.user?.theme_preference, mode]);

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute("data-theme", resolvedTheme);
    root.style.colorScheme = resolvedTheme;
  }, [resolvedTheme]);

  const setTheme = useCallback((nextMode) => {
    const normalized = normalizeMode(nextMode) || "system";
    setModeState(normalized);

    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, normalized);
    } catch {
      // Preference will still live in component state for this session.
    }

    if (session?.user) {
      const nextSession = {
        ...session,
        user: {
          ...session.user,
          theme_preference: normalized,
        },
      };
      onSessionChange?.(nextSession);
      updateThemePreference(normalized).catch((error) => {
        console.warn("[Theme] Failed to persist theme preference:", error);
      });
    }
  }, [onSessionChange, session]);

  const toggleTheme = useCallback(() => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  }, [resolvedTheme, setTheme]);

  const value = useMemo(() => ({
    mode,
    theme: resolvedTheme,
    resolvedTheme,
    systemTheme,
    setTheme,
    toggleTheme,
  }), [mode, resolvedTheme, setTheme, systemTheme, toggleTheme]);

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
