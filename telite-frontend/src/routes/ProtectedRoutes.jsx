import React from "react";

import { Navigate } from "react-router-dom";
import { getDefaultRoute, getSession } from "../context/session";

/**
 * Route guard for standard organization-scoped routes.
 */
export function ProtectedRoute({ session: _staleSession, allowRoles, children }) {
  const currentSession = getSession();

  if (!currentSession?.user) {
    return <Navigate to="/login" replace />;
  }

  const user = currentSession.user;

  // Explicitly block Platform Admins from accessing tenant/org-scoped routes
  if (user.is_platform_admin) {
    return <Navigate to="/platform-admin" replace />;
  }

  if (allowRoles && !allowRoles.includes(user.role)) {
    return <Navigate to={getDefaultRoute(user)} replace />;
  }
  
  return children;
}

/**
 * Route guard for platform-wide admin routes.
 */
export function ProtectedPlatformRoute({ session: _staleSession, children }) {
  const currentSession = getSession();

  if (!currentSession?.user) {
    return <Navigate to="/login" replace />;
  }
  
  if (!currentSession.user.is_platform_admin) {
    return <Navigate to={getDefaultRoute(currentSession.user)} replace />;
  }
  
  return children;
}
