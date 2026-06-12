import React, { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./ProtectedRoutes";
import RouteChunkFallback from "../components/common/RouteChunkFallback";

const LearnerPage = lazy(() => import("../pages/learner/LearnerPage"));

export default function LearnerRouter({ session, onLogout }) {
  return (
    <Suspense fallback={<RouteChunkFallback />}>
      <Routes>
        <Route
          path="/*"
          element={
            <ProtectedRoute session={session} allowRoles={["learner"]}>
              <LearnerPage session={session} onLogout={onLogout} />
            </ProtectedRoute>
          }
        />
      </Routes>
    </Suspense>
  );
}
