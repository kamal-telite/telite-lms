import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { loginRequest, getErrorMessage } from "../../services/client";
import { buildSessionFromAuth, getDefaultRoute } from "../../context/session";

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

  return (
    <div className="login-page" data-theme="super">
      <div className="login-page__glow login-page__glow--violet" />
      <div className="login-page__glow login-page__glow--blue" />

      <div className="login-shell">
        <section className="login-hero">
          <div className="login-brand">
            <div className="login-brand__mark">TS</div>
            <div>
              <div className="login-brand__title">Telite Systems LMS</div>
              <div className="login-brand__subtitle">Role-aware learning operations for ATS</div>
            </div>
          </div>

          <div className="login-copy">
            <p className="eyebrow">Internal learning platform</p>
            <h1>One workspace for categories, learners, PAL tracking, and Moodle launch.</h1>
            <p className="login-copy__body">
              Sign in as Super Admin, ATS Admin, or a learner to access the real dashboards wired
              to the Telite backend.
            </p>
          </div>

          <div className="login-showcase">
            <div className="login-showcase__line">
              <strong>Super Admin</strong>
              <span>Cross-category control, audit, admin delegation, and enrollment approvals.</span>
            </div>
            <div className="login-showcase__line">
              <strong>ATS Admin</strong>
              <span>Course operations, learner management, PAL tracking, and task assignment.</span>
            </div>
            <div className="login-showcase__line">
              <strong>Learner</strong>
              <span>Progress view, Moodle launch, tasks, notifications, and personal PAL insight.</span>
            </div>
          </div>
        </section>

        <section className="login-card">
          <div className="login-card__header">
            <h2>Sign in</h2>
            <p>Use the seeded Telite credentials to open the live dashboards.</p>
          </div>

          {error ? <div className="form-alert form-alert--error">{error}</div> : null}

          <form className="form-stack" onSubmit={handleSubmit}>
            <label className="field">
              <span className="field__label">Username</span>
              <input
                className={`field__input ${error ? "is-invalid" : ""}`}
                type="text"
                value={username}
                onChange={(event) => {
                  setUsername(event.target.value);
                  if (error) {
                    setError("");
                  }
                }}
                placeholder="Enter your username"
                autoComplete="username"
                required
              />
            </label>

            <label className="field">
              <span className="field__label">Password</span>
              <input
                className={`field__input ${error ? "is-invalid" : ""}`}
                type="password"
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value);
                  if (error) {
                    setError("");
                  }
                }}
                placeholder="Enter your password"
                autoComplete="current-password"
                required
              />
            </label>

            <button className="btn btn--primary btn--block" type="submit" disabled={loading}>
              {loading ? "Signing in..." : "Open workspace"}
            </button>
          </form>

          <div className="credential-card">
            <div className="credential-card__title">Quick sign-in</div>
            <div className="credential-card__list">
              {credentialRows.map(([seedUsername, seedPassword, label]) => (
                <button
                  key={seedUsername}
                  className="credential-row"
                  type="button"
                  onClick={() => {
                    setUsername(seedUsername);
                    setPassword(seedPassword);
                    setError("");
                  }}
                >
                  <span>
                    <strong>{label}</strong>
                    <small>{seedUsername}</small>
                  </span>
                  <code>{seedPassword}</code>
                </button>
              ))}
            </div>
          </div>

          <div className="login-signup-link">
            Don't have an account?
            <Link to="/signup">Create Account</Link>
          </div>
        </section>
      </div>
    </div>
  );
}
