import React from "react";

import { Navigate } from "react-router-dom";
import { getDefaultRoute, getSession, normalizeRole } from "../context/session";

/**
 * Route guard for standard organization-scoped routes.
 */
export function ProtectedRoute({ session: _staleSession, allowRoles, children }) {
  const currentSession = _staleSession?.user ? _staleSession : getSession();
  console.log("[PROTECTED_ROUTE] ProtectedRoute - currentSession:", currentSession, "allowRoles:", allowRoles);

  if (!currentSession?.user) {
    console.log("[PROTECTED_ROUTE] ProtectedRoute - no user, redirecting to /login");
    return <Navigate to="/login" replace />;
  }

  const user = currentSession.user;
  const role = normalizeRole(user.role);
  console.log("[PROTECTED_ROUTE] ProtectedRoute - user role:", role, "is_platform_admin:", user.is_platform_admin);

  // Explicitly block Platform Admins from accessing tenant/org-scoped routes
  if (user.is_platform_admin) {
    console.log("[PROTECTED_ROUTE] ProtectedRoute - blocking platform admin from tenant route, redirecting to /platform-admin");
    return <Navigate to="/platform-admin" replace />;
  }

  if (allowRoles && !allowRoles.includes(role)) {
    const defaultRoute = getDefaultRoute(user);
    console.log("[PROTECTED_ROUTE] ProtectedRoute - role", role, 'not in allowRoles', allowRoles, 'redirecting to:', defaultRoute);
    return <Navigate to={defaultRoute} replace />;
  }
  
  console.log("[PROTECTED_ROUTE] ProtectedRoute - allowing access to protected route for role:", role);
  return children;
}

/**
 * Route guard for platform-wide admin routes.
 */
export function ProtectedPlatformRoute({ session: _staleSession, children }) {
  const currentSession = _staleSession?.user ? _staleSession : getSession();

  if (!currentSession?.user) {
    return <Navigate to="/login" replace />;
  }
  
  if (!currentSession.user.is_platform_admin) {
    return <Navigate to={getDefaultRoute(currentSession.user)} replace />;
  }
  
  return children;
}
