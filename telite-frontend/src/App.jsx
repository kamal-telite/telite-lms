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
const CertificateVerifyPage = lazy(() => import("./pages/public/CertificateVerifyPage"));
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
    this.state = { error: null, isChunkError: false };
  }

  static getDerivedStateFromError(error) {
    return {
      error,
      isChunkError: isDynamicImportError(error),
    };
  }

  componentDidCatch(error) {
    if (!isDynamicImportError(error) || typeof window === "undefined") {
      // Non-chunk errors must not force a full page reload
      console.error("Application render error:", error);
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
      if (this.state.isChunkError) {
        return (
          <FullPageMessage
            title="Refreshing TELITE"
            body="Reloading the latest application bundle."
          />
        );
      }

      return (
        <FullPageMessage
          title="Something went wrong"
          body="An unexpected error occurred while rendering this view. Try refreshing the page."
        />
      );
    }

    return this.props.children;
  }
}

function FullPageMessage({ title, body }) {
  const heading = title === "Loading..." ? "Preparing Workspace..." : title;

  return (
    <div className="app-loader" role="status" aria-live="polite" aria-busy="true">
      <div className="app-loader__panel">
        <div className="app-loader__brand">
          Telite <span>LMS</span>
        </div>
        <div className="spinner" aria-hidden="true" />
        <h1 className="app-loader__title">{heading}</h1>
        {body ? <p className="app-loader__body">{body}</p> : null}
      </div>
    </div>
  );
}

function AppRoutes({ session, setSession, onLogout, booting }) {
  console.log("[APP] AppRoutes - session:", session, "booting:", booting);
  if (booting) {
    console.log("[APP] AppRoutes - still booting, showing loader");
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
              <>
                {console.log("[APP] AppRoutes /login - user logged in, redirecting to:", getDefaultRoute(session.user))}
                <Navigate to={getDefaultRoute(session.user)} replace />
              </>
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
        
        {/* Public Certificate Verification */}
        <Route
          path="/public/verify/:token"
          element={<CertificateVerifyPage />}
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
          path="/dashboard/*"
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
      console.log("[APP] restoreSession - stored session:", stored);
      if (!stored?.user) {
        console.log("[APP] restoreSession - no stored user, setting boot to false");
        setBooting(false);
        return;
      }

      try {
        console.log("[APP] restoreSession - calling fetchMe for user:", stored.user.user_id);
        const me = await fetchMe();
        console.log("[APP] restoreSession - /auth/me response:", me);
        if (cancelled) {
          console.log("[APP] restoreSession - cancelled");
          return;
        }
        const merged = mergeSessionUser(stored, me);
        console.log("[APP] restoreSession - merged session:", merged);
        persistSession(merged);
        setSessionState(merged);
      } catch (error) {
        console.error("[APP] restoreSession - error:", error);
        if (!cancelled) {
          clearSession();
          setSessionState(null);
        }
      } finally {
        if (!cancelled) {
          console.log("[APP] restoreSession - setting boot to false");
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
