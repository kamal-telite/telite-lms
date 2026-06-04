import React, { useEffect, useState, lazy, Suspense } from "react";
import Lenis from "lenis";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ToastProvider } from "./components/common/ui";
import { fetchMe, logoutRequest } from "./services/client";
import {
  clearSession,
  getDefaultRoute,
  getSession,
  mergeSessionUser,
  persistSession,
} from "./context/session";

// Theme and Branding Providers
import { ThemeProvider } from "./providers/ThemeProvider";
import { BrandingProvider } from "./providers/BrandingProvider";

// Modular Domain Routers
import PlatformRouter from "./routes/platform_router";
import OrgRouter from "./routes/org_router";
import LearnerRouter from "./routes/learner_router";

// Lazy Loaded Root Auth/Public Components
const Login = lazy(() => import("./pages/auth/Login"));
const Signup = lazy(() => import("./pages/auth/Signup"));
const LandingPage = lazy(() => import("./pages/landing/LandingPage"));
const AcceptInvitePage = lazy(() => import("./pages/auth/AcceptInvitePage"));
const ResetPasswordPage = lazy(() => import("./pages/auth/ResetPasswordPage"));

function FullPageMessage({ title, body }) {
  return (
    <div className="loader" style={{ display: 'flex', flexDirection: 'column', zIndex: 999999 }}>
      <div className="loader-logo">Telite <span>LMS</span></div>
      <div style={{ marginTop: '24px', fontSize: '13px', color: 'rgba(255,255,255,0.5)', letterSpacing: '0.05em' }}>
        {title === "Loading..." ? "Preparing Workspace..." : title}
      </div>
    </div>
  );
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
    <Suspense fallback={null}>
      <Routes>
        <Route
          path="/login"
          element={
            session?.user ? (
              <Navigate to={getDefaultRoute(session.user)} replace />
            ) : (
              <Login onAuthenticated={setSession} />
            )
          }
        />
        <Route
          path="/signup"
          element={
            session?.user ? (
              <Navigate to={getDefaultRoute(session.user)} replace />
            ) : (
              <Signup />
            )
          }
        />
        <Route
          path="/accept-invite"
          element={<AcceptInvitePage onAuthenticated={setSession} />}
        />
        <Route
          path="/set-password"
          element={<AcceptInvitePage onAuthenticated={setSession} />}
        />
        <Route
          path="/reset-password"
          element={<ResetPasswordPage />}
        />
        
        {/* Modular Routers */}
        <Route
          path="/platform-admin/*"
          element={<PlatformRouter session={session} onLogout={onLogout} />}
        />
        
        <Route
          path="/super-admin/*"
          element={<OrgRouter session={session} onLogout={onLogout} />}
        />
        <Route
          path="/categories/:slug/*"
          element={<OrgRouter session={session} onLogout={onLogout} />}
        />
        
        <Route
          path="/learner/*"
          element={<LearnerRouter session={session} onLogout={onLogout} />}
        />
        
        <Route
          path="/dashboard"
          element={
            session?.user ? (
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
              to={session?.user ? getDefaultRoute(session.user) : "/"}
              replace
            />
          }
        />
      </Routes>
    </Suspense>
  );
}

export default function App() {
  const [session, setSessionState] = useState(() => getSession());
  const [booting, setBooting] = useState(() => Boolean(getSession()?.user));

  const setSession = (nextSession) => {
    if (nextSession?.user) {
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
      if (activeSession?.user) {
        await logoutRequest();
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
    // Initialize smooth scrolling
    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      direction: "vertical",
      gestureDirection: "vertical",
      smooth: true,
      mouseMultiplier: 1,
      smoothTouch: false,
      touchMultiplier: 2,
      infinite: false,
    });
    function raf(time) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);

    return () => {
      lenis.destroy();
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      const stored = getSession();
      if (!stored?.user) {
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
    <ThemeProvider>
      <BrandingProvider session={session}>
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
      </BrandingProvider>
    </ThemeProvider>
  );
}
