import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Login from "./pages/auth/Login";
import Signup from "./pages/auth/Signup";
import LandingPage from "./pages/landing/LandingPage";
import SuperAdminPage from "./pages/super-admin/SuperAdminPage";
import CategoryAdminPage from "./pages/company/CategoryAdminPage";
import CategoryStatsPage from "./pages/super-admin/CategoryStatsPage";
import LearnerPage from "./pages/learner/LearnerPage";
import AcceptInvitePage from "./pages/auth/AcceptInvitePage";
import { ToastProvider } from "./components/common/ui";
import { fetchMe, logoutRequest } from "./services/client";
import {
  clearSession,
  getDefaultRoute,
  getSession,
  mergeSessionUser,
  persistSession,
} from "./context/session";
import PlatformAdminPage from "./pages/platform-admin/PlatformAdminPage";

function FullPageMessage({ title, body }) {
  return (
    <div className="app-loader">
      <div className="app-loader__panel">
        <div className="spinner" />
        <h1>{title}</h1>
        <p>{body}</p>
      </div>
    </div>
  );
}

function ProtectedRoute({ session, allowRoles, children }) {
  if (!session?.accessToken) {
    return <Navigate to="/login" replace />;
  }
  if (allowRoles && !allowRoles.includes(session.user?.role)) {
    return <Navigate to={getDefaultRoute(session.user)} replace />;
  }
  return children;
}

function ProtectedPlatformRoute({ session, children }) {
  if (!session?.accessToken) {
    return <Navigate to="/login" replace />;
  }
  if (!session.user?.is_platform_admin && session.user?.role !== "platform_admin") {
    return <Navigate to={getDefaultRoute(session.user)} replace />;
  }
  return children;
}

function AppRoutes({ session, setSession, onLogout, booting }) {
  if (booting) {
    return (
      <FullPageMessage
        title="Loading Telite Systems LMS"
        body="Restoring your session and preparing the workspace."
      />
    );
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={
          session?.accessToken ? (
            <Navigate to={getDefaultRoute(session.user)} replace />
          ) : (
            <Login onAuthenticated={setSession} />
          )
        }
      />
      <Route
        path="/signup"
        element={
          session?.accessToken ? (
            <Navigate to={getDefaultRoute(session.user)} replace />
          ) : (
            <Signup />
          )
        }
      />
      <Route
        path="/accept-invite"
        element={
          session?.accessToken ? (
            <Navigate to={getDefaultRoute(session.user)} replace />
          ) : (
            <AcceptInvitePage onAuthenticated={setSession} />
          )
        }
      />
      <Route
        path="/platform-admin/*"
        element={
          <ProtectedPlatformRoute session={session}>
            <PlatformAdminPage session={session} onLogout={onLogout} />
          </ProtectedPlatformRoute>
        }
      />
      <Route
        path="/super-admin/*"
        element={
          <ProtectedRoute session={session} allowRoles={["super_admin"]}>
            <SuperAdminPage session={session} onLogout={onLogout} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/categories/:slug/admin/*"
        element={
          <ProtectedRoute session={session} allowRoles={["super_admin", "category_admin"]}>
            <CategoryAdminPage session={session} onLogout={onLogout} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/categories/:slug/stats"
        element={
          <ProtectedRoute session={session} allowRoles={["super_admin", "category_admin"]}>
            <CategoryStatsPage session={session} onLogout={onLogout} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/learner/*"
        element={
          <ProtectedRoute session={session} allowRoles={["learner"]}>
            <LearnerPage session={session} onLogout={onLogout} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          session?.accessToken ? (
            <Navigate to={getDefaultRoute(session.user)} replace />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route path="/" element={<LandingPage session={session} />} />
      <Route
        path="*"
        element={
          <Navigate
            to={session?.accessToken ? getDefaultRoute(session.user) : "/"}
            replace
          />
        }
      />
    </Routes>
  );
}

export default function App() {
  const [session, setSessionState] = useState(() => getSession());
  const [booting, setBooting] = useState(() => Boolean(getSession()?.accessToken));

  const setSession = (nextSession) => {
    if (nextSession?.accessToken) {
      persistSession(nextSession);
      setSessionState(nextSession);
    } else {
      clearSession();
      setSessionState(null);
    }
  };

  const onLogout = async () => {
    const activeSession = getSession();
    try {
      if (activeSession?.accessToken) {
        await logoutRequest(activeSession.refreshToken);
      }
    } catch {
      // Best-effort logout.
    } finally {
      clearSession();
      setSessionState(null);
      window.location.assign("/login");
    }
  };

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      const stored = getSession();
      if (!stored?.accessToken) {
        setBooting(false);
        return;
      }

      try {
        const me = await fetchMe();
        if (cancelled) {
          return;
        }
        const merged = mergeSessionUser(stored, me);
        persistSession(merged);
        setSessionState(merged);
      } catch {
        if (!cancelled) {
          clearSession();
          setSessionState(null);
        }
      } finally {
        if (!cancelled) {
          setBooting(false);
        }
      }
    }

    restoreSession();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <ToastProvider>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AppRoutes
          session={session}
          setSession={setSession}
          onLogout={onLogout}
          booting={booting}
        />
      </BrowserRouter>
    </ToastProvider>
  );
}
