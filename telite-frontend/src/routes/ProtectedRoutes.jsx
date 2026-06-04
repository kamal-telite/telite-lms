import React from "react";
import { Navigate } from "react-router-dom";
import { getDefaultRoute } from "../context/session";

/**
 * Route guard for standard organization-scoped routes.
 */
export function ProtectedRoute({ session, allowRoles, children }) {
  if (!session?.user) {
    return <Navigate to="/login" replace />;
  }
  if (allowRoles && !allowRoles.includes(session.user?.role)) {
    return <Navigate to={getDefaultRoute(session.user)} replace />;
  }
  return children;
}

/**
 * Route guard for platform-wide admin routes.
 */
export function ProtectedPlatformRoute({ session, children }) {
  if (!session?.user) {
    return <Navigate to="/login" replace />;
  }
  if (!session.user?.is_platform_admin && session.user?.role !== "platform_admin") {
    return <Navigate to={getDefaultRoute(session.user)} replace />;
  }
  return children;
}
