import React, { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./ProtectedRoutes";

const SuperAdminPage = lazy(() => import("../pages/super-admin/SuperAdminPage"));
const CategoryAdminPage = lazy(() => import("../pages/company/CategoryAdminPage"));
const CategoryStatsPage = lazy(() => import("../pages/super-admin/CategoryStatsPage"));

export default function OrgRouter({ session, onLogout }) {
  return (
    <Suspense fallback={null}>
      <Routes>
        {/* If matched under /categories/:slug/* parent path */}
        <Route
          path="admin/*"
          element={
            <ProtectedRoute session={session} allowRoles={["super_admin", "category_admin"]}>
              <CategoryAdminPage session={session} onLogout={onLogout} />
            </ProtectedRoute>
          }
        />
        <Route
          path="stats"
          element={
            <ProtectedRoute session={session} allowRoles={["super_admin", "category_admin"]}>
              <CategoryStatsPage session={session} onLogout={onLogout} />
            </ProtectedRoute>
          }
        />

        {/* If matched under /super-admin/* parent path (or fallback splat relative to parent) */}
        <Route
          path="*"
          element={
            <ProtectedRoute session={session} allowRoles={["super_admin"]}>
              <SuperAdminPage session={session} onLogout={onLogout} />
            </ProtectedRoute>
          }
        />
      </Routes>
    </Suspense>
  );
}
