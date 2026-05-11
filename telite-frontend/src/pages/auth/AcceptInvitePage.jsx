import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { platformApi } from "../../services/platform";
import { getDefaultRoute, buildSessionFromAuth } from "../../context/session";
import { getErrorMessage } from "../../services/client";
import { useToast } from "../../components/common/ui";

function useInviteToken() {
  const { search } = useLocation();
  return useMemo(() => new URLSearchParams(search).get("token") || "", [search]);
}

export default function AcceptInvitePage({ onAuthenticated }) {
  const navigate = useNavigate();
  const token = useInviteToken();
  const { showToast } = useToast();

  const [invitation, setInvitation] = useState(null);
  const [loadingInvite, setLoadingInvite] = useState(true);
  const [inviteError, setInviteError] = useState("");

  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadInvitation() {
      if (!token) {
        setInviteError("Missing invitation token.");
        setLoadingInvite(false);
        return;
      }

      setLoadingInvite(true);
      setInviteError("");
      try {
        const res = await platformApi.validateInvitation(token);
        if (!cancelled) {
          setInvitation(res.data);
        }
      } catch (error) {
        if (!cancelled) {
          setInviteError(getErrorMessage(error, "Invitation not found or expired."));
        }
      } finally {
        if (!cancelled) {
          setLoadingInvite(false);
        }
      }
    }

    loadInvitation();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function handleSubmit(event) {
    event.preventDefault();
    setInviteError("");

    if (!token) {
      setInviteError("Missing invitation token.");
      return;
    }

    if (!fullName.trim()) {
      setInviteError("Please enter your full name.");
      return;
    }

    if (password.length < 8) {
      setInviteError("Password must be at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setInviteError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      const payload = await platformApi.acceptInvitation({
        token,
        full_name: fullName.trim(),
        password,
      });
      const session = buildSessionFromAuth(payload.data);
      onAuthenticated?.(session);
      showToast("Invitation accepted. Welcome!", "success");
      navigate(getDefaultRoute(session.user), { replace: true });
    } catch (error) {
      setInviteError(getErrorMessage(error, "Failed to accept invitation."));
    } finally {
      setSubmitting(false);
    }
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
              <div className="login-brand__subtitle">Organization invitation</div>
            </div>
          </div>

          <div className="login-copy">
            <p className="eyebrow">Accept invite</p>
            <h1>Join your organization workspace.</h1>
            <p className="login-copy__body">
              Set your name and password to activate your admin account.
            </p>
          </div>
        </section>

        <section className="login-card">
          <div className="login-card__header">
            <h2>Complete signup</h2>
            <p>We’ll verify the invitation token and create your account.</p>
          </div>

          {loadingInvite ? <div className="spinner" /> : null}
          {!loadingInvite && inviteError ? (
            <div className="form-alert form-alert--error">{inviteError}</div>
          ) : null}

          {!loadingInvite && invitation ? (
            <>
              <div className="form-alert" style={{ marginBottom: 12 }}>
                <strong>{invitation.org_name}</strong> · {invitation.role} · {invitation.email}
              </div>

              <form className="form-stack" onSubmit={handleSubmit}>
                <label className="field">
                  <span className="field__label">Full name</span>
                  <input
                    className={`field__input ${inviteError ? "is-invalid" : ""}`}
                    type="text"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    placeholder="Enter your full name"
                    autoComplete="name"
                    required
                  />
                </label>

                <label className="field">
                  <span className="field__label">Password</span>
                  <input
                    className={`field__input ${inviteError ? "is-invalid" : ""}`}
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Create a password"
                    autoComplete="new-password"
                    required
                  />
                </label>

                <label className="field">
                  <span className="field__label">Confirm password</span>
                  <input
                    className={`field__input ${inviteError ? "is-invalid" : ""}`}
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="Re-enter your password"
                    autoComplete="new-password"
                    required
                  />
                </label>

                <button className="btn btn--primary btn--block" type="submit" disabled={submitting}>
                  {submitting ? "Creating account..." : "Accept invitation"}
                </button>
              </form>
            </>
          ) : null}
        </section>
      </div>
    </div>
  );
}

