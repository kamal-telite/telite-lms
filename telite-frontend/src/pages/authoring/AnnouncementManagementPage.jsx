import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  createAnnouncement,
  deleteAnnouncement,
  fetchAnnouncements,
  getErrorMessage,
  updateAnnouncement,
} from "../../services/client";
import { DashboardShell, ProfileDropdown } from "../../layouts/DashboardLayout";
import { Badge, Button, EmptyState, ErrorState, LoadingState, Panel, useToast } from "../../components/common/ui";
import { formatMonthDate, getInitials, titleize } from "../../utils/formatters";

const EMPTY_FORM = {
  title: "",
  body: "",
  audience_type: "all",
  audience_value: "",
  status: "published",
};

export default function AnnouncementManagementPage({ session, onLogout }) {
  const { slug = "category" } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);

  const navGroups = useMemo(
    () => [
      {
        label: "Management",
        items: [
          { id: "dashboard", label: "Dashboard", icon: "dashboard" },
          { id: "announcements", label: "Announcements", icon: "bell" },
        ],
      },
    ],
    []
  );

  async function loadAnnouncements() {
    setLoading(true);
    setError("");
    try {
      const response = await fetchAnnouncements();
      setItems(Array.isArray(response.items) ? response.items : []);
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to load announcements."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAnnouncements();
  }, []);

  function startEdit(announcement) {
    const audience = announcement.audiences?.[0] || {};
    setEditingId(announcement.id);
    setForm({
      title: announcement.title || "",
      body: announcement.body || "",
      audience_type: audience.audience_type || "all",
      audience_value: audience.audience_value || "",
      status: announcement.status || "published",
    });
  }

  function resetForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function submitForm(event) {
    event.preventDefault();
    setSaving(true);
    const payload = {
      ...form,
      audience_value: form.audience_type === "all" ? null : form.audience_value,
    };
    try {
      if (editingId) {
        await updateAnnouncement(editingId, payload);
        showToast("Announcement updated.", "success");
      } else {
        await createAnnouncement(payload);
        showToast("Announcement created.", "success");
      }
      resetForm();
      await loadAnnouncements();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to save announcement."), "error");
    } finally {
      setSaving(false);
    }
  }

  async function removeAnnouncement(id) {
    try {
      await deleteAnnouncement(id);
      showToast("Announcement deleted.", "warning");
      await loadAnnouncements();
    } catch (requestError) {
      showToast(getErrorMessage(requestError, "Unable to delete announcement."), "error");
    }
  }

  return (
    <DashboardShell
      variant={slug}
      brandMark={{ label: slug.substring(0, 3).toUpperCase(), background: "#2563EB" }}
      brandTitle="Telite LMS"
      brandSubtitle={`${slug} announcements`}
      navGroups={navGroups}
      activeNav="announcements"
      onNavClick={(item) => {
        if (item.id === "dashboard") navigate(`/categories/${slug}/admin`);
      }}
      profile={{
        initials: getInitials(session?.user?.name || "Admin User"),
        gradient: ["#2563EB", "#7C3AED"],
        name: session?.user?.name || "Admin User",
        roleLabel: "category admin",
      }}
      title="Announcement Center"
      subtitle="Create and manage organization announcements"
      topbarActions={
        <ProfileDropdown
          profile={{
            initials: getInitials(session?.user?.name || "Admin User"),
            gradient: ["#2563EB", "#7C3AED"],
            name: session?.user?.name || "Admin User",
            roleLabel: "category admin",
          }}
          onLogout={onLogout}
          onNavigate={(path) => navigate(`/categories/${slug}/admin/${path}`)}
        />
      }
    >
      <div className="dashboard-stack">
        <Panel title={editingId ? "Edit Announcement" : "Create Announcement"} subtitle="Audience targeting is resolved by the backend runtime.">
          <form className="form-stack" onSubmit={submitForm}>
            <label className="field">
              <span className="field__label">Title</span>
              <input
                className="field__input"
                value={form.title}
                onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                required
              />
            </label>
            <label className="field">
              <span className="field__label">Body</span>
              <textarea
                className="field__input"
                rows={4}
                value={form.body}
                onChange={(event) => setForm((current) => ({ ...current, body: event.target.value }))}
                required
              />
            </label>
            <div className="grid-3">
              <label className="field">
                <span className="field__label">Audience</span>
                <select
                  className="field__select"
                  value={form.audience_type}
                  onChange={(event) => setForm((current) => ({ ...current, audience_type: event.target.value, audience_value: "" }))}
                >
                  <option value="all">All users</option>
                  <option value="role">Role</option>
                  <option value="category">Category</option>
                  <option value="user">Specific user</option>
                </select>
              </label>
              <label className="field">
                <span className="field__label">Audience Value</span>
                <input
                  className="field__input"
                  value={form.audience_value}
                  disabled={form.audience_type === "all"}
                  placeholder={form.audience_type === "all" ? "Not required" : "learner, science, or user id"}
                  onChange={(event) => setForm((current) => ({ ...current, audience_value: event.target.value }))}
                />
              </label>
              <label className="field">
                <span className="field__label">Status</span>
                <select
                  className="field__select"
                  value={form.status}
                  onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}
                >
                  <option value="draft">Draft</option>
                  <option value="published">Published</option>
                  <option value="archived">Archived</option>
                </select>
              </label>
            </div>
            <div className="split-actions">
              <Button tone="primary" type="submit" disabled={saving}>
                {saving ? "Saving..." : editingId ? "Update Announcement" : "Create Announcement"}
              </Button>
              {editingId ? <Button tone="ghost" onClick={resetForm}>Cancel</Button> : null}
            </div>
          </form>
        </Panel>

        <Panel title="Announcements" subtitle="Runtime records visible through the Announcement Center">
          {loading ? (
            <LoadingState title="Loading announcements..." />
          ) : error ? (
            <ErrorState body={error} action={<Button tone="primary" onClick={loadAnnouncements}>Retry</Button>} />
          ) : items.length === 0 ? (
            <EmptyState title="No announcements yet" body="Create the first organization announcement." />
          ) : (
            <div className="dashboard-stack">
              {items.map((announcement) => {
                const audience = announcement.audiences?.[0] || {};
                return (
                  <article className="soft-card" key={announcement.id}>
                    <div className="split-actions" style={{ alignItems: "flex-start" }}>
                      <div>
                        <div className="row-title">{announcement.title}</div>
                        <div className="row-subtitle">
                          {formatMonthDate(announcement.created_at)} · {titleize(audience.audience_type || "all")}
                          {audience.audience_value ? `: ${audience.audience_value}` : ""}
                        </div>
                      </div>
                      <Badge tone={announcement.status === "published" ? "success" : announcement.status === "draft" ? "neutral" : "warn"}>
                        {titleize(announcement.status)}
                      </Badge>
                    </div>
                    <p className="muted" style={{ marginTop: 12 }}>{announcement.body}</p>
                    <div className="split-actions" style={{ marginTop: 14 }}>
                      <Button size="small" tone="ghost" onClick={() => startEdit(announcement)}>Edit</Button>
                      <Button size="small" tone="danger" onClick={() => removeAnnouncement(announcement.id)}>Delete</Button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </Panel>
      </div>
    </DashboardShell>
  );
}
