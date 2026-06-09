import React, { useState, useEffect, useCallback } from "react";
import { Button, useToast, Panel, Field, Input, Select } from "../common/ui";
import { fetchDraftBranding, saveDraftBranding, publishBranding, rollbackBranding, fetchBrandingHistory, uploadOrganizationAsset, getErrorMessage } from "../../services/client";

export function BrandingSettingsTab({ organizations = [], session }) {
  const { showToast } = useToast();

  const isSuperAdmin = session?.user?.role === "super_admin";
  const userOrgId = session?.user?.org_id;
  const isFixedOrg = isSuperAdmin && userOrgId;

  const [selectedOrgId, setSelectedOrgId] = useState(isFixedOrg ? userOrgId : "");
  const selectedOrg = organizations.find(o => String(o.id) === String(selectedOrgId));
  const orgId = selectedOrg?.id;

  const [branding, setBranding] = useState({
    primary_color: "#2563EB",
    secondary_color: "#111827",
    font_family: "Inter",
    theme_mode: "light",
    custom_domain: "",
    logo: null,
    favicon: null,
    banner: null,
    terminology: {
      course: "Course",
      category: "Category",
      learner: "Learner"
    },
    email_template_id: "",
    certificate_template_url: ""
  });

  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [activeTab, setActiveTab] = useState("visual"); // visual, terminology, emails, history
  const [previewRole, setPreviewRole] = useState("learner"); // learner, category_admin, super_admin, public

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!orgId) return;
      setLoading(true);
      try {
        const data = await fetchDraftBranding(orgId);
        if (cancelled) return;
        
        const b = data.branding || {};
        setBranding({
          primary_color: b.primary_color || "#2563EB",
          secondary_color: b.secondary_color || "#111827",
          font_family: b.font || b.font_family || "Inter",
          theme_mode: b.theme || b.theme_mode || "light",
          custom_domain: b.custom_domain || "",
          logo: b.logo || b.logo_url || null,
          favicon: b.favicon || b.favicon_url || null,
          banner: b.banner || b.login_banner_url || null,
          terminology: b.terminology || { course: "Course", category: "Category", learner: "Learner" },
          email_template_id: b.email_template_id || "",
          certificate_template_url: b.certificate_template_url || ""
        });

        // Load history in background
        const histData = await fetchBrandingHistory(orgId);
        if (!cancelled) setHistory(histData.history || []);

      } catch (err) {
        if (!cancelled) showToast("Failed to load branding settings: " + getErrorMessage(err), "error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [orgId]);

  const handleUpdate = useCallback((field, value) => {
    setBranding(prev => ({ ...prev, [field]: value }));
  }, []);

  const handleTerminologyUpdate = (key, value) => {
    setBranding(prev => ({
      ...prev,
      terminology: { ...prev.terminology, [key]: value }
    }));
  };

  const handleSaveDraft = async () => {
    if (!orgId) return;
    setSaving(true);
    try {
      await saveDraftBranding(orgId, branding);
      showToast("Draft saved successfully!", "success");
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to save draft"), "error");
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!orgId) return;
    setPublishing(true);
    try {
      await publishBranding(orgId);
      showToast("Branding published live to all users!", "success");
      // Refresh history
      const histData = await fetchBrandingHistory(orgId);
      setHistory(histData.history || []);
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to publish branding"), "error");
    } finally {
      setPublishing(false);
    }
  };

  const handleRollback = async (versionId) => {
    if (!orgId || !window.confirm("Are you sure you want to rollback to this version? This will immediately overwrite the live site.")) return;
    try {
      await rollbackBranding(orgId, versionId);
      showToast("Rolled back successfully!", "success");
      
      // Reload draft
      const data = await fetchDraftBranding(orgId);
      const b = data.branding || {};
      setBranding({
        primary_color: b.primary_color || "#2563EB",
        secondary_color: b.secondary_color || "#111827",
        font_family: b.font || b.font_family || "Inter",
        theme_mode: b.theme || b.theme_mode || "light",
        custom_domain: b.custom_domain || "",
        logo: b.logo || b.logo_url || null,
        favicon: b.favicon || b.favicon_url || null,
        banner: b.banner || b.login_banner_url || null,
        terminology: b.terminology || { course: "Course", category: "Category", learner: "Learner" },
        email_template_id: b.email_template_id || "",
        certificate_template_url: b.certificate_template_url || ""
      });
    } catch (err) {
      showToast(getErrorMessage(err, "Rollback failed"), "error");
    }
  };

  const handleUpload = async (e, type) => {
    const file = e.target.files?.[0];
    if (!file || !orgId) return;

    try {
      const res = await uploadOrganizationAsset(orgId, type, file);
      showToast(`${type} uploaded successfully!`, "success");
      const key = type === "login_banner" ? "banner" : type === "certificate" ? "certificate_template_url" : type;
      setBranding(prev => ({ ...prev, [key]: res.url }));
    } catch (err) {
      showToast(getErrorMessage(err, `Failed to upload ${type}`), "error");
    }
  };

  if (!isFixedOrg && !selectedOrgId) {
    return (
      <Panel title="White-Label Engine" subtitle="Select a tenant to manage its complete enterprise identity.">
        <div style={{ padding: "24px 0" }}>
          <Field label="Select Organization">
            <Select
              value={selectedOrgId}
              onChange={(e) => setSelectedOrgId(e.target.value)}
              options={[
                { value: "", label: "Choose an organization..." },
                ...organizations.map(o => ({ value: o.id, label: `${o.name} (${o.domain})` }))
              ]}
            />
          </Field>
        </div>
      </Panel>
    );
  }

  return (
    <div className="dashboard-stack">
      {/* Action Header */}
      <div style={{
        background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: "16px 20px",
        display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 18 }}>Enterprise Identity Editor</h2>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
            Tenant: <strong>{selectedOrg?.name}</strong> • Status: <span style={{ color: "var(--warning)" }}>Draft Mode</span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <Button tone="neutral" loading={saving} onClick={handleSaveDraft}>Save Draft</Button>
          <Button tone="primary" loading={publishing} onClick={handlePublish}>Publish to Live</Button>
        </div>
      </div>

      <div className="grid-2">
        {/* Left Column: Settings Tabs */}
        <div className="dashboard-stack">
          {/* Tabs Navigation */}
          <div style={{ display: "flex", gap: 8, borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
            <Button tone={activeTab === "visual" ? "primary" : "neutral"} onClick={() => setActiveTab("visual")}>Visual & Assets</Button>
            <Button tone={activeTab === "terminology" ? "primary" : "neutral"} onClick={() => setActiveTab("terminology")}>Terminology</Button>
            <Button tone={activeTab === "emails" ? "primary" : "neutral"} onClick={() => setActiveTab("emails")}>Emails & Certs</Button>
            <Button tone={activeTab === "history" ? "primary" : "neutral"} onClick={() => setActiveTab("history")}>Audit</Button>
          </div>

          {loading ? (
            <div style={{ padding: 40, textAlign: "center" }}>Loading branding state...</div>
          ) : (
            <>
              {activeTab === "visual" && (
                <>
                  <Panel title="Color System">
                    <div className="grid-2">
                      <Field label="Primary Brand Color">
                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                          <input
                            type="color"
                            value={branding.primary_color}
                            onChange={(e) => handleUpdate("primary_color", e.target.value)}
                            style={{ width: 48, height: 36, border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer", padding: 2 }}
                          />
                          <span style={{ fontSize: 13, fontFamily: "monospace" }}>{branding.primary_color}</span>
                        </div>
                      </Field>
                      <Field label="Secondary Color">
                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                          <input
                            type="color"
                            value={branding.secondary_color}
                            onChange={(e) => handleUpdate("secondary_color", e.target.value)}
                            style={{ width: 48, height: 36, border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer", padding: 2 }}
                          />
                          <span style={{ fontSize: 13, fontFamily: "monospace" }}>{branding.secondary_color}</span>
                        </div>
                      </Field>
                    </div>
                  </Panel>

                  <Panel title="Typography & Theme">
                    <Field label="Font Family">
                      <Select
                        value={branding.font_family}
                        onChange={(e) => handleUpdate("font_family", e.target.value)}
                        options={[
                          { value: "Inter", label: "Inter (Default)" },
                          { value: "Roboto", label: "Roboto" },
                          { value: "Outfit", label: "Outfit" },
                        ]}
                      />
                    </Field>
                    <Field label="Theme Mode" style={{ marginTop: 12 }}>
                      <Select
                        value={branding.theme_mode}
                        onChange={(e) => handleUpdate("theme_mode", e.target.value)}
                        options={[
                          { value: "light", label: "Light Mode" },
                          { value: "dark", label: "Dark Mode" },
                        ]}
                      />
                    </Field>
                  </Panel>

                  <Panel title="Brand Assets">
                    <div className="dashboard-stack">
                      <Field label="Tenant Logo (Header)">
                        {branding.logo && <img src={branding.logo} alt="Logo" style={{ maxHeight: 48, marginBottom: 8, padding: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 6 }} />}
                        <input type="file" accept="image/png,image/jpeg,image/svg+xml" onChange={(e) => handleUpload(e, "logo")} />
                      </Field>
                      <Field label="Favicon">
                        {branding.favicon && <img src={branding.favicon} alt="Favicon" style={{ maxHeight: 32, marginBottom: 8, padding: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 6 }} />}
                        <input type="file" accept="image/png,image/x-icon,image/svg+xml" onChange={(e) => handleUpload(e, "favicon")} />
                      </Field>
                      <Field label="Login Banner">
                        {branding.banner && <img src={branding.banner} alt="Banner" style={{ maxHeight: 80, width: "100%", objectFit: "cover", marginBottom: 8, border: "1px solid var(--border)", borderRadius: 4 }} />}
                        <input type="file" accept="image/png,image/jpeg" onChange={(e) => handleUpload(e, "login_banner")} />
                      </Field>
                    </div>
                  </Panel>
                </>
              )}

              {activeTab === "terminology" && (
                <Panel title="Terminology Engine" subtitle="Override system defaults to match organizational terminology.">
                  <div className="dashboard-stack">
                    <Field label="Course (e.g., Program, Module)">
                      <Input
                        value={branding.terminology.course || "Course"}
                        onChange={(e) => handleTerminologyUpdate("course", e.target.value)}
                      />
                    </Field>
                    <Field label="Category (e.g., Department, Faculty)">
                      <Input
                        value={branding.terminology.category || "Category"}
                        onChange={(e) => handleTerminologyUpdate("category", e.target.value)}
                      />
                    </Field>
                    <Field label="Learner (e.g., Employee, Student)">
                      <Input
                        value={branding.terminology.learner || "Learner"}
                        onChange={(e) => handleTerminologyUpdate("learner", e.target.value)}
                      />
                    </Field>
                  </div>
                </Panel>
              )}

              {activeTab === "emails" && (
                <Panel title="Email & Certificate Templates" subtitle="Configure automated communications and completion certificates.">
                  <div className="dashboard-stack">
                    <Field label="Email Template ID (e.g., SendGrid/Postmark Template)">
                      <Input
                        value={branding.email_template_id || ""}
                        onChange={(e) => handleUpdate("email_template_id", e.target.value)}
                        placeholder="d-1234567890abcdef"
                      />
                    </Field>
                    <Field label="Certificate Template">
                      {branding.certificate_template_url && (
                        <div style={{ marginBottom: 8, padding: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 6 }}>
                          <a href={branding.certificate_template_url} target="_blank" rel="noreferrer">View Current Template</a>
                        </div>
                      )}
                      <input type="file" accept="application/pdf,image/png,image/jpeg" onChange={(e) => handleUpload(e, "certificate")} />
                    </Field>
                  </div>
                </Panel>
              )}

              {activeTab === "history" && (
                <Panel title="Version History & Rollback" subtitle="Audit trail of published branding versions.">
                  <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {history.length === 0 ? (
                      <div style={{ fontSize: 13, color: "var(--text-secondary)", textAlign: "center", padding: 20 }}>No published history yet.</div>
                    ) : (
                      history.map((v) => (
                        <div key={v.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 12, border: "1px solid var(--border)", borderRadius: 6, background: "var(--surface-sunken)" }}>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: 14 }}>Version {v.version_number}</div>
                            <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Published at {new Date(v.created_at).toLocaleString()}</div>
                          </div>
                          <Button tone="danger" onClick={() => handleRollback(v.id)}>Rollback to this</Button>
                        </div>
                      ))
                    )}
                  </div>
                </Panel>
              )}
            </>
          )}
        </div>

        {/* Right Column: Runtime Live Preview */}
        <div className="dashboard-stack">
          <Panel title="Runtime Live Preview" subtitle="Render actual application layouts with draft context.">
            
            {/* Role Context Switcher */}
            <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
              <Button tone={previewRole === "public" ? "primary" : "neutral"} onClick={() => setPreviewRole("public")}>Login View</Button>
              <Button tone={previewRole === "learner" ? "primary" : "neutral"} onClick={() => setPreviewRole("learner")}>Learner View</Button>
              <Button tone={previewRole === "category_admin" ? "primary" : "neutral"} onClick={() => setPreviewRole("category_admin")}>Admin View</Button>
            </div>

            <div style={{ 
              height: 600, 
              width: "100%", 
              borderRadius: 8, 
              border: "2px dashed var(--border)", 
              background: "var(--surface-sunken)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
              color: "var(--text-muted)",
              position: "relative"
            }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>🚀</div>
              <h3 style={{ margin: 0, marginBottom: 8 }}>Live Preview Coming Soon</h3>
              <p style={{ margin: 0, maxWidth: 300, textAlign: "center" }}>
                The runtime preview shell is currently disabled while we stabilize the rendering engine.
              </p>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
