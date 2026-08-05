import { useState, useEffect, useMemo } from "react";
import { Panel, Button, Badge, Avatar, useToast, Icon } from "../../common/ui";
import { getSession } from "../../../context/session";
import { fetchMe, api } from "../../../services/client";
import { getInitials } from "../../../utils/formatters";
import { NotificationPreferencesPanel } from "../../common/NotificationPreferencesPanel";

export function SettingsSection() {
  const { showToast } = useToast();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Profile forms
  const [profileForm, setProfileForm] = useState({
    full_name: "",
    email: "",
  });
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  // Password forms
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSavingPassword, setIsSavingPassword] = useState(false);

  // Initialize and load user
  const loadUser = async () => {
    setLoading(true);
    setError(null);
    try {
      const userData = await fetchMe();
      setUser(userData);
    } catch (err) {
      console.error("Failed to load user profile:", err);
      // Fallback to session storage if API fails or skipped
      const session = getSession();
      if (session?.user) {
        setUser(session.user);
      } else {
        setError("Failed to load user settings.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUser();
  }, []);

  // Update profile inputs when user loads
  useEffect(() => {
    if (user) {
      setProfileForm({
        full_name: user.name || user.full_name || "",
        email: user.email || "",
      });
    }
  }, [user]);

  // Profile change handler
  const handleProfileChange = (e) => {
    setProfileForm({ ...profileForm, [e.target.name]: e.target.value });
  };

  // Password change handler
  const handlePasswordChange = (e) => {
    setPasswordForm({ ...passwordForm, [e.target.name]: e.target.value });
  };

  // Password rules validation
  const passwordValidation = useMemo(() => {
    const pass = passwordForm.new_password || "";
    return {
      hasMinLength: pass.length >= 8,
      hasNumber: /\d/.test(pass),
      hasSpecial: /[!@#$%^&*(),.?":{}|<>]/.test(pass),
    };
  }, [passwordForm.new_password]);

  // Password strength score
  const passwordStrength = useMemo(() => {
    if (!passwordForm.new_password) return { label: "Too Short", color: "var(--border)", pct: 0, tone: "neutral" };
    
    let score = 0;
    if (passwordValidation.hasMinLength) score += 1;
    if (passwordValidation.hasNumber) score += 1;
    if (passwordValidation.hasSpecial) score += 1;

    if (score === 1) return { label: "Weak", color: "var(--danger)", pct: 33, tone: "critical" };
    if (score === 2) return { label: "Medium", color: "var(--warn)", pct: 66, tone: "warn" };
    if (score === 3) return { label: "Strong", color: "var(--emerald)", pct: 100, tone: "success" };
    
    return { label: "Weak", color: "var(--danger)", pct: 20, tone: "critical" };
  }, [passwordForm.new_password, passwordValidation]);

  // Save profile info
  const handleSaveProfile = async (e) => {
    e.preventDefault();
    if (!profileForm.full_name.trim()) {
      showToast("Full name is required", "error");
      return;
    }
    if (!profileForm.email.trim()) {
      showToast("Email address is required", "error");
      return;
    }

    setIsSavingProfile(true);
    try {
      await api.patch("/auth/me", profileForm);
      showToast("Profile settings updated successfully", "success");
      await loadUser();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to update profile", "error");
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Update/Save password
  const handleSavePassword = async (e) => {
    e.preventDefault();
    if (!passwordForm.current_password) {
      showToast("Current password is required", "error");
      return;
    }
    if (!passwordForm.new_password) {
      showToast("New password is required", "error");
      return;
    }
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      showToast("New passwords do not match", "error");
      return;
    }
    if (passwordForm.new_password.length < 8) {
      showToast("New password must be at least 8 characters", "error");
      return;
    }

    setIsSavingPassword(true);
    try {
      const res = await api.post("/auth/me/password", {
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      showToast(res.data.message || "Password updated successfully. Please log in again.", "success");
      setPasswordForm({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
      
      // Auto logout after brief delay since password change revokes backend session
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to update password", "error");
    } finally {
      setIsSavingPassword(false);
    }
  };

  if (loading && !user) {
    return (
      <div style={{ padding: "40px", display: "flex", flexDirection: "column", gap: "20px" }}>
        <div style={{ height: "40px", background: "var(--border)", borderRadius: "6px", width: "200px" }} className="skeleton" />
        <div className="settings-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
          <div style={{ height: "300px", background: "var(--border)", borderRadius: "12px" }} className="skeleton" />
          <div style={{ height: "300px", background: "var(--border)", borderRadius: "12px" }} className="skeleton" />
        </div>
      </div>
    );
  }

  if (error && !user) {
    return (
      <div style={{ padding: "40px", textAlign: "center" }}>
        <p style={{ color: "var(--danger)", marginBottom: "16px" }}>{error}</p>
        <Button tone="primary" onClick={loadUser}>Retry</Button>
      </div>
    );
  }

  const userInitials = getInitials(user?.name || user?.full_name || "Learner");
  
  // Format dates
  const joinedDate = user?.created_at 
    ? new Date(user.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
    : "Not Available";

  const lastLoginDate = user?.last_login
    ? new Date(user.last_login).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
    : "Not Available";

  return (
    <div id="section-settings" className="dashboard-stack" style={{ padding: "4px" }}>
      
      <div className="settings-grid">
        
        {/* Left Column Stack */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          
          {/* Card 1 - Profile */}
          <Panel title="Profile" subtitle="Manage your public avatar and contact details.">
            <form onSubmit={handleSaveProfile} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "8px" }}>
                <Avatar initials={userInitials} size={64} gradient={["#0ea5e9", "#6366f1"]} />
                <div>
                  <h4 style={{ margin: 0, fontSize: "16px", color: "var(--text-primary)" }}>
                    {user?.name || user?.full_name || "Learner"}
                  </h4>
                  <p style={{ margin: "4px 0 0 0", fontSize: "13px", color: "var(--text-muted)" }}>
                    Joined {joinedDate}
                  </p>
                </div>
              </div>

              <div className="grid-2" style={{ display: "grid", gap: "16px", gridTemplateColumns: "1fr 1fr" }}>
                <div className="field">
                  <label className="field__label" htmlFor="full_name">Full Name</label>
                  <input
                    id="full_name"
                    className="field__input"
                    name="full_name"
                    type="text"
                    value={profileForm.full_name}
                    onChange={handleProfileChange}
                    placeholder="e.g. Jane Doe"
                    required
                  />
                </div>

                <div className="field">
                  <label className="field__label" htmlFor="email">Email Address</label>
                  <input
                    id="email"
                    className="field__input"
                    name="email"
                    type="email"
                    value={profileForm.email}
                    onChange={handleProfileChange}
                    placeholder="e.g. jane@company.com"
                    required
                  />
                </div>

                <div className="field">
                  <label className="field__label" htmlFor="phone">Phone Number</label>
                  <input
                    id="phone"
                    className="field__input"
                    type="text"
                    value="Not Available"
                    disabled
                    readOnly
                    style={{ background: "var(--bg-disabled)", color: "var(--text-muted)", cursor: "not-allowed" }}
                  />
                </div>

                <div className="field">
                  <label className="field__label" htmlFor="org">Organization</label>
                  <input
                    id="org"
                    className="field__input"
                    type="text"
                    value={user?.org_id ? `Organization ID: ${user.org_id}` : "Not Available"}
                    disabled
                    readOnly
                    style={{ background: "var(--bg-disabled)", color: "var(--text-muted)", cursor: "not-allowed" }}
                  />
                </div>

                <div className="field">
                  <label className="field__label" htmlFor="role">Role</label>
                  <input
                    id="role"
                    className="field__input"
                    type="text"
                    value={user?.role ? String(user.role).toUpperCase() : "LEARNER"}
                    disabled
                    readOnly
                    style={{ background: "var(--bg-disabled)", color: "var(--text-muted)", cursor: "not-allowed" }}
                  />
                </div>

                <div className="field">
                  <label className="field__label" htmlFor="joined">Joined Date</label>
                  <input
                    id="joined"
                    className="field__input"
                    type="text"
                    value={joinedDate}
                    disabled
                    readOnly
                    style={{ background: "var(--bg-disabled)", color: "var(--text-muted)", cursor: "not-allowed" }}
                  />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "8px" }}>
                <Button tone="primary" type="submit" disabled={isSavingProfile} icon="save">
                  {isSavingProfile ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </form>
          </Panel>

          {/* Card 2 - Security */}
          <Panel title="Security" subtitle="Update your account password. Log out occurs automatically after change.">
            <form onSubmit={handleSavePassword} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              <div className="field">
                <label className="field__label" htmlFor="current_password">Current Password</label>
                <div style={{ position: "relative" }}>
                  <input
                    id="current_password"
                    className="field__input"
                    name="current_password"
                    type={showCurrentPassword ? "text" : "password"}
                    value={passwordForm.current_password}
                    onChange={handlePasswordChange}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    style={{
                      position: "absolute",
                      right: "12px",
                      top: "50%",
                      transform: "translateY(-50%)",
                      background: "transparent",
                      border: "none",
                      cursor: "pointer",
                      color: "var(--text-muted)",
                      display: "flex",
                      alignItems: "center"
                    }}
                    title={showCurrentPassword ? "Hide password" : "Show password"}
                  >
                    <Icon name={showCurrentPassword ? "eye-off" : "eye"} size={16} />
                  </button>
                </div>
              </div>

              <div className="field">
                <label className="field__label" htmlFor="new_password">New Password</label>
                <div style={{ position: "relative" }}>
                  <input
                    id="new_password"
                    className="field__input"
                    name="new_password"
                    type={showNewPassword ? "text" : "password"}
                    value={passwordForm.new_password}
                    onChange={handlePasswordChange}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    style={{
                      position: "absolute",
                      right: "12px",
                      top: "50%",
                      transform: "translateY(-50%)",
                      background: "transparent",
                      border: "none",
                      cursor: "pointer",
                      color: "var(--text-muted)",
                      display: "flex",
                      alignItems: "center"
                    }}
                    title={showNewPassword ? "Hide password" : "Show password"}
                  >
                    <Icon name={showNewPassword ? "eye-off" : "eye"} size={16} />
                  </button>
                </div>
              </div>

              {/* Password strength and validations */}
              {passwordForm.new_password && (
                <div style={{ marginTop: "-8px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Password Strength:</span>
                    <span style={{ fontSize: "12px", fontWeight: "600", color: passwordStrength.color }}>
                      {passwordStrength.label}
                    </span>
                  </div>
                  <div style={{ height: "4px", width: "100%", background: "var(--border)", borderRadius: "99px", overflow: "hidden", marginBottom: "12px" }}>
                    <div style={{ height: "100%", width: `${passwordStrength.pct}%`, background: passwordStrength.color, transition: "width 0.3s ease" }} />
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "6px", background: "var(--background)", padding: "10px", borderRadius: "6px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: passwordValidation.hasMinLength ? "var(--emerald)" : "var(--text-muted)" }}>
                      <Icon name={passwordValidation.hasMinLength ? "check" : "circle"} size={12} stroke={3} style={{ color: passwordValidation.hasMinLength ? "var(--emerald)" : "var(--text-muted)" }} />
                      <span>At least 8 characters</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: passwordValidation.hasNumber ? "var(--emerald)" : "var(--text-muted)" }}>
                      <Icon name={passwordValidation.hasNumber ? "check" : "circle"} size={12} stroke={3} style={{ color: passwordValidation.hasNumber ? "var(--emerald)" : "var(--text-muted)" }} />
                      <span>Contains a number</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: passwordValidation.hasSpecial ? "var(--emerald)" : "var(--text-muted)" }}>
                      <Icon name={passwordValidation.hasSpecial ? "check" : "circle"} size={12} stroke={3} style={{ color: passwordValidation.hasSpecial ? "var(--emerald)" : "var(--text-muted)" }} />
                      <span>Contains a special character</span>
                    </div>
                  </div>
                </div>
              )}

              <div className="field">
                <label className="field__label" htmlFor="confirm_password">Confirm Password</label>
                <div style={{ position: "relative" }}>
                  <input
                    id="confirm_password"
                    className="field__input"
                    name="confirm_password"
                    type={showConfirmPassword ? "text" : "password"}
                    value={passwordForm.confirm_password}
                    onChange={handlePasswordChange}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    style={{
                      position: "absolute",
                      right: "12px",
                      top: "50%",
                      transform: "translateY(-50%)",
                      background: "transparent",
                      border: "none",
                      cursor: "pointer",
                      color: "var(--text-muted)",
                      display: "flex",
                      alignItems: "center"
                    }}
                    title={showConfirmPassword ? "Hide password" : "Show password"}
                  >
                    <Icon name={showConfirmPassword ? "eye-off" : "eye"} size={16} />
                  </button>
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "8px" }}>
                <Button tone="primary" type="submit" disabled={isSavingPassword} icon="lock">
                  {isSavingPassword ? "Updating..." : "Update Password"}
                </Button>
              </div>
            </form>
          </Panel>

        </div>

        {/* Right Column Stack */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          
          {/* Card 3 - Account Information */}
          <Panel title="Account Information" subtitle="System metadata and logs for your profile.">
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Icon name="lock" size={16} style={{ color: "var(--text-muted)" }} />
                  <span style={{ fontSize: "14px", fontWeight: "500", color: "var(--text-primary)" }}>Learner ID</span>
                </div>
                <span style={{ fontSize: "13px", color: "var(--text-secondary)", fontFamily: "monospace", background: "var(--background)", padding: "2px 6px", borderRadius: "4px" }}>
                  {user?.user_id || user?.id || "Not Available"}
                </span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Icon name="users" size={16} style={{ color: "var(--text-muted)" }} />
                  <span style={{ fontSize: "14px", fontWeight: "500", color: "var(--text-primary)" }}>Organization</span>
                </div>
                <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                  {user?.org_id ? `Org ID: ${user.org_id}` : "Not Available"}
                </span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Icon name="shield" size={16} style={{ color: "var(--text-muted)" }} />
                  <span style={{ fontSize: "14px", fontWeight: "500", color: "var(--text-primary)" }}>Role</span>
                </div>
                <Badge tone="accent">{user?.role ? String(user.role).replace("_", " ").toUpperCase() : "LEARNER"}</Badge>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Icon name="circle" size={16} style={{ color: "var(--emerald)" }} />
                  <span style={{ fontSize: "14px", fontWeight: "500", color: "var(--text-primary)" }}>Account Status</span>
                </div>
                <Badge tone="success">Active</Badge>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Icon name="course" size={16} style={{ color: "var(--text-muted)" }} />
                  <span style={{ fontSize: "14px", fontWeight: "500", color: "var(--text-primary)" }}>Joined Date</span>
                </div>
                <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                  {joinedDate}
                </span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Icon name="clock" size={16} style={{ color: "var(--text-muted)" }} />
                  <span style={{ fontSize: "14px", fontWeight: "500", color: "var(--text-primary)" }}>Last Login</span>
                </div>
                <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                  {lastLoginDate}
                </span>
              </div>
            </div>
          </Panel>

          {/* Card 4 - Notification Preferences */}
          <NotificationPreferencesPanel />

          {/* Card 5 - Preferences */}
          <Panel title="Preferences" subtitle="Personalize language, dark theme and timezone.">
            <div style={{ position: "relative" }}>
              
              <div style={{ display: "flex", flexDirection: "column", gap: "16px", opacity: 0.5, pointerEvents: "none" }}>
                <div className="field">
                  <label className="field__label" htmlFor="pref_theme">Theme</label>
                  <select id="pref_theme" className="field__input" defaultValue="system" disabled>
                    <option value="light">Light Theme</option>
                    <option value="dark">Dark Theme</option>
                    <option value="system">System Default</option>
                  </select>
                </div>

                <div className="field">
                  <label className="field__label" htmlFor="pref_lang">Language</label>
                  <select id="pref_lang" className="field__input" defaultValue="en" disabled>
                    <option value="en">English (US)</option>
                    <option value="es">Español</option>
                    <option value="fr">Français</option>
                  </select>
                </div>

                <div className="field">
                  <label className="field__label" htmlFor="pref_tz">Timezone</label>
                  <select id="pref_tz" className="field__input" defaultValue="utc" disabled>
                    <option value="utc">Coordinated Universal Time (UTC)</option>
                    <option value="est">Eastern Standard Time (EST)</option>
                    <option value="pst">Pacific Standard Time (PST)</option>
                  </select>
                </div>
              </div>

              <div style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "rgba(var(--surface-rgb), 0.3)",
                backdropFilter: "blur(1px)",
                borderRadius: "8px"
              }}>
                <Badge tone="neutral" style={{ padding: "8px 16px", fontSize: "14px", fontWeight: "600", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)" }}>
                  Coming Soon
                </Badge>
              </div>

            </div>
          </Panel>

        </div>

      </div>

      {/* Responsive layout styles helper */}
      <style>{`
        .settings-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 24px;
          margin-top: 12px;
        }
        @media (min-width: 1024px) {
          .settings-grid {
            grid-template-columns: 1fr 1fr;
          }
        }
        .settings-grid form .field {
          margin-bottom: 0;
        }
      `}</style>

    </div>
  );
}
