/**
 * Session management for Telite LMS.
 *
 * PHASE 2 SECURITY HARDENING:
 * - JWT tokens are now stored in HttpOnly Secure cookies (set by backend).
 * - This file no longer reads/writes tokens from localStorage.
 * - Only non-sensitive user profile data (role, name, org_id) is kept in
 *   sessionStorage so the UI can render without an extra /auth/me round-trip.
 * - CSRF token is read from the telite_csrf_token cookie (not HttpOnly) and
 *   sent as X-CSRF-Token on every mutating request via the Axios interceptor.
 * - Multi-account support: accounts array in sessionStorage keyed by user_id.
 */

const USER_KEY = "telite_user";
const ACCOUNTS_KEY = "telite_accounts"; // multi-account switcher

// ── CSRF helpers ──────────────────────────────────────────────────────────────

/**
 * Read the CSRF token from the telite_csrf_token cookie.
 * The backend sets this as a non-HttpOnly cookie so JS can read it.
 */
export function getCsrfToken() {
  if (typeof document === "undefined") return "";
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith("telite_csrf_token="));
  return match ? decodeURIComponent(match.split("=")[1]) : "";
}

// ── Session helpers ───────────────────────────────────────────────────────────

function readStorage(key) {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key, value) {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(key, value);
  } catch {
    // sessionStorage full or unavailable — degrade gracefully
  }
}

function removeStorage(key) {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    // ignore
  }
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Get the current session.
 * Returns null if no user profile is stored (i.e. not logged in).
 *
 * NOTE: Tokens are in HttpOnly cookies — we never read them here.
 */
export function getSession() {
  const rawUser = readStorage(USER_KEY);
  if (!rawUser) return null;

  try {
    const user = JSON.parse(rawUser);
    return { user };
  } catch {
    return null;
  }
}

/**
 * Persist the user profile to sessionStorage after a successful login.
 * Tokens are handled by the backend via Set-Cookie headers.
 */
export function persistSession(session) {
  if (!session?.user) return;
  writeStorage(USER_KEY, JSON.stringify(session.user));

  // Also update the multi-account list
  _upsertAccount(session.user);
}

/**
 * Clear the current session from sessionStorage.
 * The backend clears the HttpOnly cookies via the /auth/logout endpoint.
 */
export function clearSession() {
  removeStorage(USER_KEY);
}

/**
 * Build a session object from the /auth/login or /auth/refresh response.
 * Tokens are NOT stored here — they arrive as HttpOnly cookies.
 */
export function buildSessionFromAuth(payload) {
  return {
    authenticated: true,
    user: {
      user_id: payload.user_id,
      role: payload.role,
      name: payload.name,
      email: payload.email,
      category_scope: payload.category_scope ?? null,
      org_id: payload.org_id ?? null,
      is_platform_admin: payload.is_platform_admin ?? false,
      permissions: payload.permissions ?? [],
    },
  };
}

/**
 * Merge an updated auth payload into an existing session.
 */
export function mergeAuthPayload(session, payload) {
  return {
    authenticated: true,
    user: {
      ...session?.user,
      user_id: payload.user_id || session?.user?.user_id,
      role: payload.role || session?.user?.role,
      name: payload.name || session?.user?.name,
      email: payload.email || session?.user?.email,
      category_scope: payload.category_scope ?? session?.user?.category_scope ?? null,
      org_id: payload.org_id ?? session?.user?.org_id ?? null,
      is_platform_admin: payload.is_platform_admin ?? session?.user?.is_platform_admin ?? false,
      permissions: payload.permissions ?? session?.user?.permissions ?? [],
    },
  };
}

/**
 * Merge updated user fields into an existing session.
 */
export function mergeSessionUser(session, user) {
  return {
    ...session,
    user: { ...session?.user, ...user },
  };
}

/**
 * Determine the default route for a user based on their role.
 */
export function getDefaultRoute(user) {
  if (!user) return "/login";

  if (user.is_platform_admin || user.role === "platform_admin") {
    return "/platform-admin";
  }
  if (user.role === "super_admin") {
    return "/super-admin";
  }
  if (
    user.role === "category_admin" ||
    user.role === "college_super_admin" ||
    user.role === "company_super_admin"
  ) {
    return `/categories/${user.category_scope || "ats"}/admin`;
  }
  return "/learner";
}

// ── Multi-account switcher ────────────────────────────────────────────────────

/**
 * Get all stored accounts (for the account switcher UI).
 */
export function getAllAccounts() {
  const raw = readStorage(ACCOUNTS_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

/**
 * Switch to a different stored account.
 * Returns the account object if found, null otherwise.
 */
export function switchAccount(userId) {
  const accounts = getAllAccounts();
  const account = accounts.find((a) => a.user_id === userId);
  if (!account) return null;
  writeStorage(USER_KEY, JSON.stringify(account));
  return account;
}

/**
 * Remove an account from the switcher list.
 */
export function removeAccount(userId) {
  const accounts = getAllAccounts().filter((a) => a.user_id !== userId);
  writeStorage(ACCOUNTS_KEY, JSON.stringify(accounts));
}

function _upsertAccount(user) {
  if (!user?.user_id) return;
  const accounts = getAllAccounts().filter((a) => a.user_id !== user.user_id);
  accounts.unshift(user); // most recent first
  // Keep at most 5 accounts
  writeStorage(ACCOUNTS_KEY, JSON.stringify(accounts.slice(0, 5)));
}
