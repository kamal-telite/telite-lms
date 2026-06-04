import { useMemo, useState } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { resetPassword, getErrorMessage } from "../../services/client";
import { useToast } from "../../components/common/ui";
import { getSession } from "../../context/session";

function useResetToken() {
  const { search } = useLocation();
  return useMemo(() => new URLSearchParams(search).get("token") || "", [search]);
}

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const token = useResetToken();
  const { showToast } = useToast();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const [activeSession] = useState(() => getSession());

  async function handleSubmit(event) {
    event.preventDefault();
    setErrorMsg("");

    if (!token) {
      setErrorMsg("Missing reset token.");
      return;
    }

    if (password.length < 8) {
      setErrorMsg("Password must be at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setErrorMsg("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await resetPassword(token, password);
      showToast("Password reset successfully. You can now log in.", "success");
      navigate("/login", { replace: true });
    } catch (error) {
      setErrorMsg(getErrorMessage(error, "Failed to reset password. The link might be expired."));
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <div className="login-page" data-theme="brand">
        <div className="login-shell">
          <section className="login-card" style={{ marginTop: "10vh", marginInline: "auto" }}>
            <div className="login-card__header">
              <h2>Invalid Link</h2>
              <p>The password reset link is missing or invalid.</p>
            </div>
            <Link to="/login" className="btn btn--primary btn--block">Return to Login</Link>
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page" data-theme="brand">
      <div className="login-page__glow login-page__glow--violet" />
      <div className="login-page__glow login-page__glow--blue" />

      <div className="login-shell">
        <section className="login-hero">
          <div className="login-brand">
            <div className="login-brand__mark">TS</div>
            <div>
              <div className="login-brand__title">Telite Systems LMS</div>
              <div className="login-brand__subtitle">Password Reset</div>
            </div>
          </div>

          <div className="login-copy">
            <p className="eyebrow">Choose a new password</p>
            <h1>Reset your account password.</h1>
            <p className="login-copy__body">
              Enter your new password below to regain access to your account.
            </p>
          </div>
        </section>

        <section className="login-card">
          <div className="login-card__header">
            <h2>Reset Password</h2>
            <p>Please provide your new password.</p>
          </div>

          {activeSession ? (
            <div className="form-alert" style={{ marginBottom: 16, backgroundColor: "#fffbeb", borderColor: "#fcd34d", color: "#92400e" }}>
              <strong>Heads up:</strong> You are currently logged in as <strong>{activeSession.user?.email || "another user"}</strong>. After resetting the password, you may need to log out to access the affected account.
            </div>
          ) : null}

          {errorMsg ? (
            <div className="form-alert form-alert--error">{errorMsg}</div>
          ) : null}

          <form className="form-stack" onSubmit={handleSubmit}>
            <label className="field">
              <span className="field__label">New Password</span>
              <input
                className={`field__input ${errorMsg ? "is-invalid" : ""}`}
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter new password"
                autoComplete="new-password"
                required
              />
            </label>

            <label className="field">
              <span className="field__label">Confirm Password</span>
              <input
                className={`field__input ${errorMsg ? "is-invalid" : ""}`}
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="Re-enter new password"
                autoComplete="new-password"
                required
              />
            </label>

            <button className="btn btn--primary btn--block" type="submit" disabled={submitting}>
              {submitting ? "Resetting..." : "Reset password"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
