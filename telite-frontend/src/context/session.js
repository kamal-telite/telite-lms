const ACCESS_TOKEN_KEY = "telite_access_token";
const REFRESH_TOKEN_KEY = "telite_refresh_token";
const USER_KEY = "telite_user";

function readStorage(key) {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}

export function getSession() {
  const accessToken = readStorage(ACCESS_TOKEN_KEY);
  const refreshToken = readStorage(REFRESH_TOKEN_KEY);
  const rawUser = readStorage(USER_KEY);

  if (!accessToken || !rawUser) {
    return null;
  }

  try {
    return {
      accessToken,
      refreshToken,
      user: JSON.parse(rawUser),
    };
  } catch {
    return null;
  }
}

export function persistSession(session) {
  if (typeof window === "undefined" || !session?.accessToken || !session?.user) {
    return;
  }

  window.localStorage.setItem(ACCESS_TOKEN_KEY, session.accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, session.refreshToken || "");
  window.localStorage.setItem(USER_KEY, JSON.stringify(session.user));
}

export function clearSession() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export function buildSessionFromAuth(payload) {
  return {
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    user: {
      user_id: payload.user_id,
      role: payload.role,
      name: payload.name,
      email: payload.email,
      category_scope: payload.category_scope,
      org_id: payload.org_id,
      is_platform_admin: payload.is_platform_admin,
    },
  };
}

export function mergeAuthPayload(session, payload) {
  return {
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token || session.refreshToken,
    user: {
      ...session.user,
      user_id: payload.user_id || session.user?.user_id,
      role: payload.role || session.user?.role,
      name: payload.name || session.user?.name,
      email: payload.email || session.user?.email,
      category_scope: payload.category_scope ?? session.user?.category_scope ?? null,
    },
  };
}

export function mergeSessionUser(session, user) {
  return {
    ...session,
    user: {
      ...session.user,
      ...user,
    },
  };
}

export function getDefaultRoute(user) {
  if (!user) {
    return "/login";
  }

  // Platform admin gets the platform dashboard
  if (user.is_platform_admin || user.role === "platform_admin") {
    return "/platform-admin";
  }

  if (user.role === "super_admin") {
    return "/super-admin";
  }

  if (user.role === "category_admin" || user.role === "college_super_admin" || user.role === "company_super_admin") {
    return `/categories/${user.category_scope || "ats"}/admin`;
  }

  return "/learner";
}
