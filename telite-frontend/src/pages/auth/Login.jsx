import { useState, useEffect, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { loginRequest, forgotPassword, getErrorMessage } from "../../services/client";
import { buildSessionFromAuth, getDefaultRoute } from "../../context/session";
import { canUseWebGL, loadVantaDependencies } from "../../utils/scriptLoader";
import "./Login.css";

// ── View modes ─────────────────────────────────────────────────────────────────
const VIEW_LOGIN = "login";
const VIEW_FORGOT = "forgot";
const VIEW_FORGOT_SENT = "forgot_sent";

export default function Login({ onAuthenticated }) {
  const navigate = useNavigate();

  // ── Login state ──────────────────────────────────────────────────────────────
  const [username, setUsername] = useState("superadmin");
  const [password, setPassword] = useState("Super@1234");
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  // ── Forgot-password state ────────────────────────────────────────────────────
  const [view, setView] = useState(VIEW_LOGIN);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotError, setForgotError] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [sentEmail, setSentEmail] = useState("");

  // ── Animation refs ───────────────────────────────────────────────────────────
  const vantaRef = useRef(null);
  const modalRef = useRef(null);
  const btnRef = useRef(null);
  const cursorRef = useRef(null);
  const cursorDotRef = useRef(null);
  const typedRef = useRef(null);

  // ── Vanta / GSAP / cursor setup ──────────────────────────────────────────────
  useEffect(() => {
    document.body.classList.add("login-active");

    let vantaEffect = null;
    const gsap = window.gsap;
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const enablePointerEffects =
      !prefersReduced &&
      window.matchMedia("(pointer: fine)").matches &&
      window.innerWidth >= 1100;

    const initVanta = async () => {
      if (prefersReduced || !canUseWebGL()) return;
      const VANTA = await loadVantaDependencies();
      if (VANTA && VANTA.NET && vantaRef.current) {
        try {
          vantaEffect = VANTA.NET({
            el: vantaRef.current,
            mouseControls: false,
            touchControls: false,
            gyroControls: false,
            minHeight: 200,
            minWidth: 200,
            scale: 1.0,
            color: 0x4648d4,
            backgroundColor: 0x0d0b2e,
            points: 8,
            maxDistance: 16,
            spacing: 22,
            showDots: false,
          });
        } catch (error) {
          console.warn("Login Vanta disabled:", error);
        }
      }
    };

    initVanta();

    const onMouseMove = (e) => {
      if (gsap && cursorRef.current && cursorDotRef.current) {
        gsap.to(cursorRef.current, {
          x: e.clientX,
          y: e.clientY,
          duration: 0.55,
          ease: "power2.out",
        });
        gsap.to(cursorDotRef.current, { x: e.clientX, y: e.clientY, duration: 0.1 });
      }

      if (btnRef.current && gsap) {
        const r = btnRef.current.getBoundingClientRect();
        if (
          e.clientX >= r.left &&
          e.clientX <= r.right &&
          e.clientY >= r.top &&
          e.clientY <= r.bottom
        ) {
          const x = (e.clientX - r.left - r.width / 2) * 0.38;
          const y = (e.clientY - r.top - r.height / 2) * 0.38;
          gsap.to(btnRef.current, { x, y, duration: 0.28, ease: "power2.out" });
        } else {
          gsap.to(btnRef.current, { x: 0, y: 0, duration: 0.65, ease: "elastic.out(1, 0.4)" });
        }
      }
    };

    if (enablePointerEffects) {
      document.addEventListener("mousemove", onMouseMove, { passive: true });
    }

    if (window.VanillaTilt && modalRef.current) {
      document.fonts.ready.then(() => {
        window.VanillaTilt.init(modalRef.current, {
          max: 5,
          speed: 700,
          glare: true,
          "max-glare": 0.07,
          scale: 1.012,
          perspective: 1400,
          "full-page-listening": false,
        });
      });
    }

    function startTyped() {
      if (window.Typed) {
        typedRef.current = new window.Typed("#typed-word", {
          strings: [
            "categories.",
            "learners.",
            "PAL tracking.",
            "Moodle launch.",
            "your institution.",
          ],
          typeSpeed: 62,
          backSpeed: 32,
          backDelay: 2200,
          loop: true,
          cursorChar: "_",
          smartBackspace: true,
        });
      }
    }

    if (prefersReduced) {
      document.querySelectorAll(".auth-hidden").forEach((el) =>
        el.classList.remove("auth-hidden")
      );
    } else if (gsap) {
      const tl = gsap.timeline({ delay: 0.15 });
      tl.fromTo(
        "#glassModal",
        { opacity: 0, y: 50, scale: 0.95 },
        {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 1.0,
          ease: "back.out(1.5)",
          onStart: () =>
            document.getElementById("glassModal")?.classList.remove("auth-hidden"),
        }
      );
    }

    return () => {
      document.body.classList.remove("login-active");
      document.removeEventListener("mousemove", onMouseMove);
      if (vantaEffect) vantaEffect.destroy();
      if (typedRef.current) typedRef.current.destroy();
      if (modalRef.current && modalRef.current.vanillaTilt) {
        modalRef.current.vanillaTilt.destroy();
      }
    };
  }, []);

  // ── Cursor scale helpers ─────────────────────────────────────────────────────
  const handleMouseEnter = () => {
    if (window.gsap && cursorRef.current) {
      window.gsap.to(cursorRef.current, { scale: 1.7, duration: 0.25 });
    }
  };
  const handleMouseLeave = () => {
    if (window.gsap && cursorRef.current) {
      window.gsap.to(cursorRef.current, { scale: 1.0, duration: 0.25 });
    }
  };

  // ── Login submit ─────────────────────────────────────────────────────────────
  async function handleLoginSubmit(event) {
    event.preventDefault();
    setLoginLoading(true);
    setLoginError("");
    try {
      const payload = await loginRequest(username, password);
      const session = buildSessionFromAuth(payload);
      onAuthenticated(session);
      navigate(getDefaultRoute(session.user), { replace: true });
    } catch (requestError) {
      setLoginError(getErrorMessage(requestError, "Invalid username or password."));
    } finally {
      setLoginLoading(false);
    }
  }

  // ── Forgot-password submit ───────────────────────────────────────────────────
  async function handleForgotSubmit(event) {
    event.preventDefault();
    setForgotError("");

    if (!forgotEmail.trim()) {
      setForgotError("Please enter your email address.");
      return;
    }

    setForgotLoading(true);
    try {
      await forgotPassword(forgotEmail.trim());
      setSentEmail(forgotEmail.trim());
      setView(VIEW_FORGOT_SENT);
    } catch (err) {
      // Always show a neutral message so as not to reveal account existence
      setForgotError(
        getErrorMessage(err, "Something went wrong. Please try again later.")
      );
    } finally {
      setForgotLoading(false);
    }
  }

  // ── Switch views ─────────────────────────────────────────────────────────────
  function showForgot() {
    setForgotEmail("");
    setForgotError("");
    setView(VIEW_FORGOT);
  }

  function showLogin() {
    setLoginError("");
    setView(VIEW_LOGIN);
  }

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <>
      <div className="custom-cursor" id="cursor" ref={cursorRef}></div>
      <div className="custom-cursor-dot" id="cursorDot" ref={cursorDotRef}></div>

      <div id="vanta-bg" ref={vantaRef}></div>

      <div className="auth-page-wrap">
        <div className="auth-modal-wrap">
          <div className="auth-glass-modal auth-hidden" id="glassModal" ref={modalRef}>

            {/* ── LOGIN VIEW ──────────────────────────────────────────────────── */}
            {view === VIEW_LOGIN && (
              <>
                <div className="auth-modal-title">Sign in</div>
                <div className="auth-modal-sub">
                  Use the seeded Telite credentials to open the live dashboards.
                </div>

                {loginError ? (
                  <div className="auth-form-alert">{loginError}</div>
                ) : null}

                <form onSubmit={handleLoginSubmit}>
                  <div className="auth-field-group">
                    <label className="auth-field-label" htmlFor="username">
                      Username
                    </label>
                    <input
                      className="auth-field-input"
                      type="text"
                      id="username"
                      name="username"
                      autoComplete="username"
                      spellCheck="false"
                      value={username}
                      onChange={(e) => {
                        setUsername(e.target.value);
                        if (loginError) setLoginError("");
                      }}
                      onMouseEnter={handleMouseEnter}
                      onMouseLeave={handleMouseLeave}
                      required
                    />
                  </div>

                  <div className="auth-field-group">
                    <div className="auth-field-label-row">
                      <label className="auth-field-label" htmlFor="password">
                        Password
                      </label>
                      <button
                        type="button"
                        className="auth-forgot-link"
                        onClick={showForgot}
                        onMouseEnter={handleMouseEnter}
                        onMouseLeave={handleMouseLeave}
                      >
                        Forgot password?
                      </button>
                    </div>
                    <input
                      className="auth-field-input"
                      type="password"
                      id="password"
                      name="password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        if (loginError) setLoginError("");
                      }}
                      onMouseEnter={handleMouseEnter}
                      onMouseLeave={handleMouseLeave}
                      required
                    />
                  </div>

                  <button
                    className="auth-btn-open"
                    id="btnOpen"
                    ref={btnRef}
                    type="submit"
                    disabled={loginLoading}
                    onMouseEnter={handleMouseEnter}
                    onMouseLeave={handleMouseLeave}
                  >
                    {loginLoading ? "Signing in..." : "Open workspace"}
                  </button>
                </form>

                <div className="auth-create-link">
                  Don't have an account?{" "}
                  <Link
                    to="/signup"
                    onMouseEnter={handleMouseEnter}
                    onMouseLeave={handleMouseLeave}
                  >
                    Create Account
                  </Link>
                </div>
              </>
            )}

            {/* ── FORGOT-PASSWORD VIEW ────────────────────────────────────────── */}
            {view === VIEW_FORGOT && (
              <>
                <button
                  type="button"
                  className="auth-back-btn"
                  onClick={showLogin}
                  onMouseEnter={handleMouseEnter}
                  onMouseLeave={handleMouseLeave}
                  aria-label="Back to sign in"
                >
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                    <path
                      d="M10 12L6 8L10 4"
                      stroke="currentColor"
                      strokeWidth="1.75"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  Back to sign in
                </button>

                <div className="auth-modal-title" style={{ marginTop: 8 }}>
                  Reset password
                </div>
                <div className="auth-modal-sub">
                  Enter the email address on your account and we'll send you a reset link.
                </div>

                {forgotError ? (
                  <div className="auth-form-alert">{forgotError}</div>
                ) : null}

                <form onSubmit={handleForgotSubmit}>
                  <div className="auth-field-group">
                    <label className="auth-field-label" htmlFor="forgot-email">
                      Email address
                    </label>
                    <input
                      className="auth-field-input"
                      type="email"
                      id="forgot-email"
                      name="email"
                      autoComplete="email"
                      placeholder="you@example.com"
                      value={forgotEmail}
                      onChange={(e) => {
                        setForgotEmail(e.target.value);
                        if (forgotError) setForgotError("");
                      }}
                      onMouseEnter={handleMouseEnter}
                      onMouseLeave={handleMouseLeave}
                      required
                    />
                  </div>

                  <button
                    className="auth-btn-open"
                    type="submit"
                    disabled={forgotLoading}
                    onMouseEnter={handleMouseEnter}
                    onMouseLeave={handleMouseLeave}
                  >
                    {forgotLoading ? "Sending..." : "Send reset link"}
                  </button>
                </form>
              </>
            )}

            {/* ── SENT CONFIRMATION VIEW ──────────────────────────────────────── */}
            {view === VIEW_FORGOT_SENT && (
              <>
                <div className="auth-sent-icon" aria-hidden="true">
                  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                    <circle cx="24" cy="24" r="24" fill="rgba(70,72,212,0.15)" />
                    <path
                      d="M14 24C14 18.477 18.477 14 24 14C29.523 14 34 18.477 34 24C34 29.523 29.523 34 24 34C18.477 34 14 29.523 14 24Z"
                      stroke="rgba(99,102,241,0.5)"
                      strokeWidth="1.5"
                    />
                    <path
                      d="M19 24.5L22.5 28L29 21"
                      stroke="#6366f1"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>

                <div className="auth-modal-title" style={{ marginTop: 16 }}>
                  Check your inbox
                </div>
                <div className="auth-modal-sub" style={{ marginBottom: 12 }}>
                  If <strong style={{ color: "rgba(255,255,255,0.7)" }}>{sentEmail}</strong> is
                  registered, a password reset link has been sent. It expires in 15 minutes.
                </div>
                <div className="auth-modal-sub" style={{ marginBottom: 28 }}>
                  Didn't receive it? Check your spam folder or{" "}
                  <button
                    type="button"
                    className="auth-inline-link"
                    onClick={() => {
                      setForgotEmail(sentEmail);
                      setForgotError("");
                      setView(VIEW_FORGOT);
                    }}
                    onMouseEnter={handleMouseEnter}
                    onMouseLeave={handleMouseLeave}
                  >
                    try again
                  </button>
                  .
                </div>

                <button
                  className="auth-btn-open"
                  type="button"
                  onClick={showLogin}
                  onMouseEnter={handleMouseEnter}
                  onMouseLeave={handleMouseLeave}
                >
                  Back to sign in
                </button>
              </>
            )}

          </div>
        </div>
      </div>
    </>
  );
}
