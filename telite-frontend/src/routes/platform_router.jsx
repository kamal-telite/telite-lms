import React, { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { ProtectedPlatformRoute } from "./ProtectedRoutes";
import RouteChunkFallback from "../components/common/RouteChunkFallback";

const PlatformAdminPage = lazy(() => import("../pages/platform-admin/PlatformAdminPage"));

export default function PlatformRouter({ session, onLogout }) {
  return (
    <Suspense fallback={<RouteChunkFallback />}>
      <Routes>
        <Route
          path="/*"
          element={
            <ProtectedPlatformRoute session={session}>
              <PlatformAdminPage session={session} onLogout={onLogout} />
            </ProtectedPlatformRoute>
          }
        />
      </Routes>
    </Suspense>
  );
}
