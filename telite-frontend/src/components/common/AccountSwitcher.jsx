import { useEffect, useMemo, useState } from "react";
import {
  addAccountRequest,
  fetchActiveSessions,
  getErrorMessage,
  revokeSession,
  switchAccountRequest,
} from "../../services/client";
import {
  buildSessionFromAuth,
  getAllAccounts as getAccounts,
  getDefaultRoute,
  getSession,
  persistSession,
  removeAccount,
} from "../../context/session";
import { Button, useToast } from "./ui";

function initialsFor(account) {
  return (account?.name || account?.email || "U")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "U";
}

function roleLabel(account) {
  if (account?.is_platform_admin) return "platform admin";
  return String(account?.role || "user").replaceAll("_", " ");
}

export default function AccountSwitcher({ session, onSessionChange }) {
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [accounts, setAccounts] = useState(() => getAccounts());
  const [sessions, setSessions] = useState([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ username: "", password: "" });
  const [busyUserId, setBusyUserId] = useState("");

  const currentUserId = session?.user?.user_id;
  const visibleAccounts = useMemo(() => {
    const byId = new Map();
    accounts.forEach((account) => {
      if (account?.user_id) byId.set(account.user_id, account);
    });
    if (session?.user?.user_id) byId.set(session.user.user_id, session.user);
    return Array.from(byId.values());
  }, [accounts, session]);

  useEffect(() => {
    if (!open) return;
    setAccounts(getAccounts());
    setLoadingSessions(true);
    fetchActiveSessions()
      .then(setSessions)
      .catch(() => setSessions([]))
      .finally(() => setLoadingSessions(false));
  }, [open]);

  async function handleSwitch(account) {
    if (account.user_id === currentUserId) {
      setOpen(false);
      return;
    }

    setBusyUserId(account.user_id);
    try {
      const payload = await switchAccountRequest(account.user_id);
      const nextSession = buildSessionFromAuth(payload);
      persistSession(nextSession);
      onSessionChange?.(nextSession);
      setAccounts(getAccounts());
      setOpen(false);
      window.location.assign(getDefaultRoute(nextSession.user));
    } catch (error) {
      showToast(getErrorMessage(error, "Add this account again to switch to it."), "warning");
    } finally {
      setBusyUserId("");
    }
  }

  async function handleAddAccount(event) {
    event.preventDefault();
    if (!form.username || !form.password) return;

    setAdding(true);
    try {
      const payload = await addAccountRequest(form.username, form.password);
      const nextSession = buildSessionFromAuth(payload);
      persistSession(nextSession);
      onSessionChange?.(nextSession);
      setForm({ username: "", password: "" });
      setAccounts(getAccounts());
      setOpen(false);
      showToast("Account added and switched.", "success");
      window.location.assign(getDefaultRoute(nextSession.user));
    } catch (error) {
      showToast(getErrorMessage(error, "Could not add account."), "error");
    } finally {
      setAdding(false);
    }
  }

  async function handleRevoke(sessionId) {
    try {
      await revokeSession(sessionId);
      setSessions((current) => current.filter((item) => item.session_id !== sessionId));
      showToast("Session revoked.", "success");
    } catch (error) {
      showToast(getErrorMessage(error, "Could not revoke session."), "error");
    }
  }

  function handleForget(account) {
    if (account.user_id === currentUserId) return;
    removeAccount(account.user_id);
    setAccounts(getAccounts());
  }

  return (
    <div className="account-switcher">
      <button
        type="button"
        className="account-switcher__trigger"
        onClick={() => setOpen((value) => !value)}
        title="Switch accounts"
      >
        <span>{initialsFor(session?.user)}</span>
        <strong>{session?.user?.name || "Account"}</strong>
      </button>

      {open ? (
        <div className="account-switcher__panel">
          <div className="account-switcher__header">
            <div>
              <strong>Accounts</strong>
              <small>Tenant-aware browser sessions</small>
            </div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close account switcher">
              ×
            </button>
          </div>

          <div className="account-switcher__list">
            {visibleAccounts.map((account) => (
              <div className="account-switcher__account" key={account.user_id}>
                <button type="button" onClick={() => handleSwitch(account)}>
                  <span className="account-switcher__avatar">{initialsFor(account)}</span>
                  <span>
                    <strong>{account.name || account.email}</strong>
                    <small>
                      {roleLabel(account)}
                      {account.org_id ? ` · org ${account.org_id}` : ""}
                      {account.user_id === currentUserId ? " · active" : ""}
                    </small>
                  </span>
                </button>
                {account.user_id !== currentUserId ? (
                  <button type="button" className="account-switcher__forget" onClick={() => handleForget(account)}>
                    Forget
                  </button>
                ) : null}
                {busyUserId === account.user_id ? <em>Switching…</em> : null}
              </div>
            ))}
          </div>

          <form className="account-switcher__form" onSubmit={handleAddAccount}>
            <strong>Add another account</strong>
            <input
              value={form.username}
              onChange={(event) => setForm((value) => ({ ...value, username: event.target.value }))}
              placeholder="Email or username"
              autoComplete="username"
            />
            <input
              value={form.password}
              onChange={(event) => setForm((value) => ({ ...value, password: event.target.value }))}
              placeholder="Password"
              type="password"
              autoComplete="current-password"
            />
            <Button tone="primary" type="submit" disabled={adding}>
              {adding ? "Adding..." : "Add account"}
            </Button>
          </form>

          <div className="account-switcher__sessions">
            <strong>Active sessions</strong>
            {loadingSessions ? <small>Loading devices…</small> : null}
            {!loadingSessions && sessions.length === 0 ? <small>No active device data.</small> : null}
            {sessions.slice(0, 4).map((item) => (
              <div className="account-switcher__session" key={item.session_id}>
                <span>
                  <strong>{item.is_current ? "This browser" : "Active device"}</strong>
                  <small>{item.ip_address || "unknown IP"} · expires {item.expires_at}</small>
                </span>
                {!item.is_current ? (
                  <button type="button" onClick={() => handleRevoke(item.session_id)}>
                    Revoke
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
