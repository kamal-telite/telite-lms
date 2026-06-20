import React, { useEffect, useState, lazy, Suspense } from "react";
import Lenis from "lenis";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { ToastProvider } from "./components/common/ui";
import { fetchMe, logoutRequest } from "./services/client";
import {
  clearClientSessionState,
  clearSession,
  getDefaultRoute,
  getSession,
  mergeSessionUser,
  persistSession,
} from "./context/session";
import { offlineSyncManager } from "./lib/offlineSyncManager";

// Theme and Branding Providers
import { ThemeProvider } from "./providers/ThemeProvider";
import { BrandingProvider } from "./providers/BrandingProvider";
import { ThemeEngine } from "./utils/ThemeEngine";

// Modular Domain Routers
import PlatformRouter from "./routes/platform_router";
import OrgRouter from "./routes/org_router";
import LearnerRouter from "./routes/learner_router";

// Lazy Loaded Root Auth/Public Components
const Login = lazy(() => import("./pages/auth/Login"));

const LandingPage = lazy(() => import("./pages/landing/LandingPage"));
const AcceptInvitePage = lazy(() => import("./pages/auth/AcceptInvitePage"));
const ResetPasswordPage = lazy(() => import("./pages/auth/ResetPasswordPage"));
const AUTH_EXPIRED_EVENT = "telite:auth-expired";
const ROUTER_NAVIGATE_EVENT = "telite:router-navigate";
const CHUNK_RELOAD_KEY = "telite_chunk_reload_at";

function isDynamicImportError(error) {
  const message = String(error?.message || error || "");
  return (
    message.includes("Failed to fetch dynamically imported module") ||
    message.includes("Importing a module script failed") ||
    message.includes("error loading dynamically imported module") ||
    message.includes("Expected a JavaScript-or-Wasm module script")
  );
}

class LazyChunkErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error) {
    if (!isDynamicImportError(error) || typeof window === "undefined") {
      return;
    }

    const now = Date.now();
    const lastReload = Number(window.sessionStorage.getItem(CHUNK_RELOAD_KEY) || 0);
    if (now - lastReload > 30000) {
      window.sessionStorage.setItem(CHUNK_RELOAD_KEY, String(now));
      window.location.replace(window.location.href);
    }
  }

  render() {
    if (this.state.error) {
      return (
        <FullPageMessage
          title="Refreshing TELITE"
          body="Reloading the latest application bundle."
        />
      );
    }

    return this.props.children;
  }
}

function FullPageMessage({ title, body }) {
  return (
    <div className="loader" style={{ display: 'flex', flexDirection: 'column', zIndex: 999999 }}>
      <div className="loader-logo">Telite <span>LMS</span></div>
      <div style={{ marginTop: '24px', fontSize: '13px', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
        {title === "Loading..." ? "Preparing Workspace..." : title}
      </div>
      {body ? (
        <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
          {body}
        </div>
      ) : null}
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
          element={<Navigate to="/login" replace />}
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
        
        {/* Catch-all */}       
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

function RouterNavigationBridge({ setSession }) {
  const navigate = useNavigate();

  useEffect(() => {
    const handleAuthExpired = () => {
      void offlineSyncManager.clearQueue().catch(() => {});
      clearClientSessionState();
      ThemeEngine.resetBrandingStyles();
      setSession(null);
      window.location.replace("/login");
    };

    const handleNavigate = (event) => {
      const to = event.detail?.to;
      if (!to) return;
      navigate(to, { replace: event.detail?.replace !== false });
    };

    const handlePageShow = (event) => {
      if (event.persisted) {
        const currentSession = getSession();
        if (!currentSession?.user) {
          window.location.reload();
        }
      }
    };

    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    window.addEventListener(ROUTER_NAVIGATE_EVENT, handleNavigate);
    window.addEventListener("pageshow", handlePageShow);
    return () => {
      window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
      window.removeEventListener(ROUTER_NAVIGATE_EVENT, handleNavigate);
      window.removeEventListener("pageshow", handlePageShow);
    };
  }, [navigate, setSession]);

  return null;
}

function AppShell({ session, setSession, onLogout, booting }) {
  const location = useLocation();
  const locationKey = `${location.pathname}${location.search}`;

  return (
    <BrandingProvider session={session} locationKey={locationKey}>
      <ToastProvider>
        <RouterNavigationBridge setSession={setSession} />
        <LazyChunkErrorBoundary key={session?.user?.user_id || "anonymous"}>
          <AppRoutes
            session={session}
            setSession={setSession}
            onLogout={onLogout}
            booting={booting}
          />
        </LazyChunkErrorBoundary>
      </ToastProvider>
    </BrandingProvider>
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
      await offlineSyncManager.clearQueue().catch(() => {});
      clearClientSessionState();
      ThemeEngine.resetBrandingStyles();
      setSessionState(null);
      window.location.replace("/login");
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
    <ThemeProvider session={session} onSessionChange={setSession}>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AppShell
          session={session}
          setSession={setSession}
          onLogout={onLogout}
          booting={booting}
        />
      </BrowserRouter>
    </ThemeProvider>
  );
}
