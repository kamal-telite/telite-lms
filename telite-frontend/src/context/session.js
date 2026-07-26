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
const PRESERVED_LOCAL_STORAGE_KEYS = new Set(["telite_theme"]);
const SESSION_LOCAL_STORAGE_KEYS = [
  "lastRoute",
  "lastDashboard",
  "redirectAfterLogin",
  "tenantSlug",
  "activeTenant",
  "selectedCategory",
  "branding",
  "categoryScope",
  "organizationContext",
  "currentTenant",
  "telite_user",
  "telite_accounts",
  "telite_branding",
  "telite_tenant",
  "telite_category",
  "telite_last_route",
  "telite_last_dashboard",
];

const ROLE_ALIASES = {
  "category admin": "category_admin",
  "category-admin": "category_admin",
  categoryadmin: "category_admin",
  cat_admin: "category_admin",
  "super admin": "super_admin",
  "super-admin": "super_admin",
  superadmin: "super_admin",
  "platform admin": "platform_admin",
  "platform-admin": "platform_admin",
  platformadmin: "platform_admin",
};

export function normalizeRole(role) {
  if (role == null || String(role).trim() === "") return "";
  const normalized = String(role).trim().toLowerCase();
  return ROLE_ALIASES[normalized] || normalized;
}

function normalizeUser(user) {
  if (!user) return null;
  const role = normalizeRole(user.role ?? user.user_type ?? user.type);
  return {
    ...user,
    role,
    category_scope:
      user.category_scope ??
      user.categoryScope ??
      user.category_slug ??
      user.categorySlug ??
      null,
    is_platform_admin:
      user.is_platform_admin ??
      user.isPlatformAdmin ??
      role === "platform_admin",
  };
}

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
    const user = normalizeUser(JSON.parse(rawUser));
    return user ? { user } : null;
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
  const user = normalizeUser(session.user);
  writeStorage(USER_KEY, JSON.stringify(user));

  // Also update the multi-account list
  _upsertAccount(user);
}

/**
 * Clear the current session from sessionStorage.
 * The backend clears the HttpOnly cookies via the /auth/logout endpoint.
 */
export function clearSession() {
  removeStorage(USER_KEY);
}

/**
 * Clear all browser-side state that is scoped to an authenticated user/session.
 * Keep non-auth preferences such as theme so logout does not reset personalization.
 */
export function clearClientSessionState() {
  if (typeof window === "undefined") return;

  try {
    window.sessionStorage.clear();
  } catch {
    removeStorage(USER_KEY);
    removeStorage(ACCOUNTS_KEY);
  }

  try {
    SESSION_LOCAL_STORAGE_KEYS.forEach((key) => {
      if (!PRESERVED_LOCAL_STORAGE_KEYS.has(key)) {
        window.localStorage.removeItem(key);
      }
    });

    Object.keys(window.localStorage).forEach((key) => {
      const normalized = key.toLowerCase();
      const isSessionLike =
        normalized.includes("tenant") ||
        normalized.includes("branding") ||
        normalized.includes("category") ||
        normalized.includes("dashboard") ||
        normalized.includes("route") ||
        normalized.includes("auth") ||
        normalized.includes("session");

      if (isSessionLike && !PRESERVED_LOCAL_STORAGE_KEYS.has(key)) {
        window.localStorage.removeItem(key);
      }
    });
  } catch {
    // localStorage unavailable; nothing else to clear.
  }
}

/**
 * Build a session object from the /auth/login or /auth/refresh response.
 * Tokens are NOT stored here — they arrive as HttpOnly cookies.
 */
export function buildSessionFromAuth(payload) {
  const source = payload?.user || payload || {};
  const user = normalizeUser({
    user_id: source.user_id ?? source.id ?? source.sub,
    role: source.role ?? source.user_type ?? source.type,
    name: source.name ?? source.full_name,
    email: source.email,
    category_scope: source.category_scope ?? source.categoryScope ?? source.category_slug,
    org_id: source.org_id ?? source.organization_id,
    is_platform_admin: source.is_platform_admin ?? source.isPlatformAdmin,
    permissions: source.permissions ?? [],
    theme_preference: source.theme_preference ?? "system",
  });

  return {
    authenticated: true,
    user,
  };
}

/**
 * Merge an updated auth payload into an existing session.
 */
export function mergeAuthPayload(session, payload) {
  const source = payload?.user || payload || {};
  const user = normalizeUser({
    ...session?.user,
    user_id: source.user_id ?? source.id ?? source.sub ?? session?.user?.user_id,
    role: source.role ?? source.user_type ?? source.type ?? session?.user?.role,
    name: source.name ?? source.full_name ?? session?.user?.name,
    email: source.email ?? session?.user?.email,
    category_scope:
      source.category_scope ??
      source.categoryScope ??
      source.category_slug ??
      session?.user?.category_scope,
    org_id: source.org_id ?? source.organization_id ?? session?.user?.org_id,
    is_platform_admin:
      source.is_platform_admin ??
      source.isPlatformAdmin ??
      session?.user?.is_platform_admin,
    permissions: source.permissions ?? session?.user?.permissions ?? [],
    theme_preference:
      source.theme_preference ?? session?.user?.theme_preference ?? "system",
  });

  return {
    authenticated: true,
    user,
  };
}

/**
 * Merge updated user fields into an existing session.
 */
export function mergeSessionUser(session, user) {
  return {
    ...session,
    user: normalizeUser({ ...session?.user, ...user }),
  };
}

/**
 * Determine the default route for a user based on their role.
 */
export function getDefaultRoute(user) {
  if (!user) return "/login";

  const normalizedUser = normalizeUser(user);
  if (!normalizedUser) return "/login";

  if (normalizedUser.is_platform_admin === true) {
    return "/platform-admin";
  }
  const role = normalizeRole(normalizedUser.role);
  if (role === "platform_admin") {
    return "/platform-admin";
  }
  if (role === "super_admin") {
    return "/super-admin";
  }
  if (role === "category_admin") {
    return `/categories/${normalizedUser.category_scope || "ats"}/admin`;
  }
  if (role === "learner") {
    return "/learner";
  }
  return "/login";
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
