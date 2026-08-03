import { useState, useEffect } from "react";
import { Panel, Button, Badge, useToast } from "./ui";
import { getSession } from "../../context/session";
import { fetchMe, api } from "../../services/client";

export function AccountSettingsPanel() {
  const { showToast } = useToast();
  const [user, setUser] = useState(null);
  
  const refetchUser = async () => {
    try {
      const userData = await fetchMe();
      setUser(userData);
    } catch (err) {
      console.error("Failed to refetch user:", err);
    }
  };
  
  const [profileForm, setProfileForm] = useState({
    full_name: "",
    email: "",
    username: "",
  });
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isSavingPassword, setIsSavingPassword] = useState(false);
  
  useEffect(() => {
    // Initialize user from session
    const session = getSession();
    if (session?.user) {
      setUser(session.user);
    }
  }, []);
  
  useEffect(() => {
    if (user) {
      setProfileForm({
        full_name: user.full_name || "",
        email: user.email || "",
        username: user.username || "",
      });
    }
  }, [user]);

  const handleProfileChange = (e) => {
    setProfileForm({ ...profileForm, [e.target.name]: e.target.value });
  };

  const handlePasswordChange = (e) => {
    setPasswordForm({ ...passwordForm, [e.target.name]: e.target.value });
  };

  const saveProfile = async () => {
    setIsSavingProfile(true);
    try {
      await api.patch("/auth/me", profileForm);
      showToast("Profile updated successfully", "success");
      await refetchUser();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to update profile", "error");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const savePassword = async () => {
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      showToast("New passwords do not match", "error");
      return;
    }
    if (passwordForm.new_password.length < 8) {
      showToast("Password must be at least 8 characters long", "error");
      return;
    }
    
    setIsSavingPassword(true);
    try {
      const res = await api.post("/auth/me/password", {
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      showToast(res.data.message || "Password updated successfully", "success");
      setPasswordForm({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
      // The API clears cookies, so refetching user should ideally trigger a 401 and redirect to login
      await refetchUser();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to update password", "error");
    } finally {
      setIsSavingPassword(false);
    }
  };

  if (!user) return null;

  return (
    <div className="account-settings">
      <Panel title="Profile Details" subtitle="Update your personal information">
        <div className="grid-2">
          <div className="field">
            <label className="field__label">Full Name</label>
            <input
              className="field__input"
              name="full_name"
              value={profileForm.full_name}
              onChange={handleProfileChange}
              placeholder="e.g. Jane Doe"
            />
          </div>
          <div className="field">
            <label className="field__label">Email Address</label>
            <input
              className="field__input"
              type="email"
              name="email"
              value={profileForm.email}
              onChange={handleProfileChange}
            />
          </div>
          <div className="field">
            <label className="field__label">Username</label>
            <input
              className="field__input"
              name="username"
              value={profileForm.username}
              onChange={handleProfileChange}
            />
          </div>
          <div className="field">
            <label className="field__label">Role</label>
            <div style={{ marginTop: 8 }}>
              <Badge tone="accent">{user.role}</Badge>
            </div>
          </div>
        </div>
        <div className="panel-actions" style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end' }}>
          <Button tone="primary" onClick={saveProfile} disabled={isSavingProfile}>
            {isSavingProfile ? "Saving..." : "Save Profile"}
          </Button>
        </div>
      </Panel>

      <Panel title="Security" subtitle="Manage your password" style={{ marginTop: 24 }}>
        <div className="grid-1" style={{ maxWidth: 400 }}>
          <div className="field">
            <label className="field__label">Current Password</label>
            <input
              className="field__input"
              type="password"
              name="current_password"
              value={passwordForm.current_password}
              onChange={handlePasswordChange}
            />
          </div>
          <div className="field">
            <label className="field__label">New Password</label>
            <input
              className="field__input"
              type="password"
              name="new_password"
              value={passwordForm.new_password}
              onChange={handlePasswordChange}
            />
          </div>
          <div className="field">
            <label className="field__label">Confirm New Password</label>
            <input
              className="field__input"
              type="password"
              name="confirm_password"
              value={passwordForm.confirm_password}
              onChange={handlePasswordChange}
            />
          </div>
        </div>
        <div className="panel-actions" style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end' }}>
          <Button tone="primary" onClick={savePassword} disabled={isSavingPassword}>
            {isSavingPassword ? "Updating..." : "Update Password"}
          </Button>
        </div>
      </Panel>
    </div>
  );
}
