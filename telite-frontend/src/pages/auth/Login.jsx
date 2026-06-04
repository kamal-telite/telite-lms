import { useState, useEffect, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { loginRequest, getErrorMessage } from "../../services/client";
import { buildSessionFromAuth, getDefaultRoute } from "../../context/session";
import { canUseWebGL, loadVantaDependencies } from "../../utils/scriptLoader";
import "./Login.css";

const credentialRows = [
  ["superadmin", "Super@1234", "Super Admin"],
  ["anika", "Admin@1234", "ATS Admin"],
  ["rahul", "Learner@1234", "Learner"],
];

export default function Login({ onAuthenticated }) {
  const navigate = useNavigate();
  const [username, setUsername] = useState("superadmin");
  const [password, setPassword] = useState("Super@1234");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const vantaRef = useRef(null);
  const modalRef = useRef(null);
  const btnRef = useRef(null);
  const cursorRef = useRef(null);
  const cursorDotRef = useRef(null);
  const typedRef = useRef(null);

  useEffect(() => {
    document.body.classList.add("login-active");

    let vantaEffect = null;
    const gsap = window.gsap;
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const enablePointerEffects = !prefersReduced && window.matchMedia("(pointer: fine)").matches && window.innerWidth >= 1100;

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
            showDots: false
          });
        } catch (error) {
          console.warn("Login Vanta disabled:", error);
        }
      }
    };

    initVanta();

    const onMouseMove = (e) => {
      if (gsap && cursorRef.current && cursorDotRef.current) {
        gsap.to(cursorRef.current, { x: e.clientX, y: e.clientY, duration: 0.55, ease: "power2.out" });
        gsap.to(cursorDotRef.current, { x: e.clientX, y: e.clientY, duration: 0.1 });
      }

      if (gsap) {
        // Only parallax on the background if desired, or skip.
      }

      // Magnetic Button
      if (btnRef.current && gsap) {
        const r = btnRef.current.getBoundingClientRect();
        if (e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom) {
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
          "full-page-listening": false
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
            "your institution."
          ],
          typeSpeed: 62,
          backSpeed: 32,
          backDelay: 2200,
          loop: true,
          cursorChar: "_",
          smartBackspace: true
        });
      }
    }

    if (prefersReduced) {
      document.querySelectorAll(".auth-hidden").forEach(el => el.classList.remove("auth-hidden"));
    } else if (gsap) {
      const tl = gsap.timeline({ delay: 0.15 });

      tl.fromTo("#glassModal",
        { opacity: 0, y: 50, scale: 0.95 },
        { opacity: 1, y: 0, scale: 1, duration: 1.0, ease: "back.out(1.5)", onStart: () => document.getElementById("glassModal")?.classList.remove("auth-hidden") }
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

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const payload = await loginRequest(username, password);
      const session = buildSessionFromAuth(payload);
      onAuthenticated(session);
      navigate(getDefaultRoute(session.user), { replace: true });
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Invalid username or password."));
    } finally {
      setLoading(false);
    }
  }

  function fillCreds(user, pass) {
    setUsername(user);
    setPassword(pass);
    setError("");
    
    if (window.gsap) {
      const uI = document.getElementById("username");
      const pI = document.getElementById("password");
      if (uI && pI) {
        window.gsap.fromTo([uI, pI],
          { borderColor: "rgba(99,102,241,0.9)" },
          { borderColor: "rgba(255,255,255,0.1)", duration: 0.8, ease: "power2.out" }
        );
        window.gsap.fromTo([uI, pI],
          { boxShadow: "0 0 0 3px rgba(70,72,212,0.45)" },
          { boxShadow: "0 0 0 0px rgba(70,72,212,0)", duration: 0.8, ease: "power2.out" }
        );
      }
    }
  }

  return (
    <>
      <div className="custom-cursor" id="cursor" ref={cursorRef}></div>
      <div className="custom-cursor-dot" id="cursorDot" ref={cursorDotRef}></div>

      <div id="vanta-bg" ref={vantaRef}></div>

      <div className="auth-page-wrap">
        <div className="auth-modal-wrap">
          <div className="auth-glass-modal auth-hidden" id="glassModal" ref={modalRef}>
            <div className="auth-modal-title">Sign in</div>
            <div className="auth-modal-sub">Use the seeded Telite credentials to open the live dashboards.</div>

            {error ? <div className="auth-form-alert">{error}</div> : null}

            <form onSubmit={handleSubmit}>
              <div className="auth-field-group">
                <label className="auth-field-label" htmlFor="username">Username</label>
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
                    if (error) setError("");
                  }}
                  onMouseEnter={handleMouseEnter}
                  onMouseLeave={handleMouseLeave}
                  required
                />
              </div>

              <div className="auth-field-group">
                <label className="auth-field-label" htmlFor="password">Password</label>
                <input
                  className="auth-field-input"
                  type="password"
                  id="password"
                  name="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError("");
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
                disabled={loading}
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}
              >
                {loading ? "Signing in..." : "Open workspace"}
              </button>
            </form>

            <div className="auth-qs-section">
              <div className="auth-qs-label">Quick Sign-In</div>

              {credentialRows.map(([seedUsername, seedPassword, label], idx) => (
                <div
                  key={idx}
                  className="auth-qs-row"
                  onClick={() => fillCreds(seedUsername, seedPassword)}
                  onMouseEnter={handleMouseEnter}
                  onMouseLeave={handleMouseLeave}
                >
                  <div>
                    <div className="auth-qs-role-name">{label}</div>
                    <div className="auth-qs-username">{seedUsername}</div>
                  </div>
                  <div className="auth-qs-pass">{seedPassword}</div>
                </div>
              ))}
            </div>

            <div className="auth-create-link">
              Don't have an account? <Link to="/signup" onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>Create Account</Link>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
