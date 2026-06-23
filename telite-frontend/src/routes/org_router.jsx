import React, { lazy, Suspense } from "react";
import { Route, Routes, useLocation, useParams } from "react-router-dom";
import { ProtectedRoute } from "./ProtectedRoutes";

const SuperAdminPage = lazy(() => import("../pages/super-admin/SuperAdminPage"));
const CategoryAdminPage = lazy(() => import("../pages/company/CategoryAdminPage"));
const CategoryStatsPage = lazy(() => import("../pages/super-admin/CategoryStatsPage"));
const CourseBuilderPage = lazy(() => import("../pages/authoring/CourseBuilderPage"));
const LearningPathBuilder = lazy(() => import('../pages/authoring/LearningPathBuilder'));
const QuestionBankManagerPage = lazy(() => import('../pages/authoring/QuestionBankManagerPage'));
const AnnouncementManagementPage = lazy(() => import('../pages/authoring/AnnouncementManagementPage'));
const BulkEnrollmentPage = lazy(() => import('../pages/super-admin/BulkEnrollmentPage'));

export default function OrgRouter({ session, onLogout }) {
  const location = useLocation();
  const isCategoryContext = location.pathname.startsWith("/categories");

  return (
    <Suspense fallback={null}>
      <Routes>
        {/* If matched under /categories/:slug/* parent path */}
        {isCategoryContext && (
          <>
            <Route
              path="admin/*"
              element={
                <ProtectedRoute session={session} allowRoles={["category_admin"]}>
                  <CategoryAdminPage session={session} onLogout={onLogout} />
                </ProtectedRoute>
              }
            />
            <Route
              path="stats"
              element={
                <ProtectedRoute session={session} allowRoles={["category_admin"]}>
                  <CategoryStatsPage session={session} onLogout={onLogout} />
                </ProtectedRoute>
              }
            />
            <Route
              path="builder/:course_id"
              element={
                <ProtectedRoute session={session} allowRoles={["category_admin"]}>
                  <CourseBuilderPage session={session} onLogout={onLogout} />
                </ProtectedRoute>
              }
            />
            <Route
              path="paths/:pathId"
              element={
                <ProtectedRoute session={session} allowRoles={["category_admin"]}>
                  <LearningPathBuilder session={session} onLogout={onLogout} />
                </ProtectedRoute>
              }
            />
            <Route
              path="question-banks/*"
              element={
                <ProtectedRoute session={session} allowRoles={["category_admin"]}>
                  <QuestionBankManagerPage session={session} onLogout={onLogout} />
                </ProtectedRoute>
              }
            />
            <Route
              path="announcements"
              element={
                <ProtectedRoute session={session} allowRoles={["category_admin"]}>
                  <AnnouncementManagementPage session={session} onLogout={onLogout} />
                </ProtectedRoute>
              }
            />
          </>
        )}

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
