import React, { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./ProtectedRoutes";
import { getSession, normalizeRole } from "../context/session";

const LearnerPage = lazy(() => import("../pages/learner/LearnerPage"));

export default function LearnerRouter({ session, onLogout }) {
  const currentSession = session?.user ? session : getSession();
  const userRole = currentSession?.user?.role;
  console.log("[LEARNER_ROUTER] LearnerRouter - session:", currentSession, "userRole:", userRole);
  
  return (
    <Suspense fallback={null}>
      <Routes>
        <Route
          path="/*"
          element={
            <>
              {console.log("[LEARNER_ROUTER] LearnerRouter - rendering learner route guard for role:", normalizeRole(userRole))}
              <ProtectedRoute session={session} allowRoles={["learner"]}>
                <LearnerPage session={session} onLogout={onLogout} />
              </ProtectedRoute>
            </>
          }
        />
      </Routes>
    </Suspense>
  );
}
