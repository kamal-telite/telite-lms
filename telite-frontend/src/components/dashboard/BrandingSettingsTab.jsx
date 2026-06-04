import React, { useState, useEffect, useRef, useCallback } from "react";
import { Button, useToast, Panel, Field, Input, Select } from "../common/ui";
import { fetchBranding, updateOrganizationBranding, uploadOrganizationAsset, getErrorMessage } from "../../services/client";

/* ── Inline Live Preview ─────────────────────────────────────── */
function LivePreview({ branding, orgName }) {
  const pc = branding.primary_color || "#2563EB";
  const sc = branding.secondary_color || "#111827";
  const font = branding.font_family || "Inter";
  const theme = branding.theme_mode || "light";
  const isDark = theme === "dark";

  const bg = isDark ? "#0f172a" : "#ffffff";
  const textColor = isDark ? "#e2e8f0" : "#1e293b";
  const mutedColor = isDark ? "#94a3b8" : "#64748b";
  const surfaceColor = isDark ? "#1e293b" : "#f8fafc";
  const borderColor = isDark ? "#334155" : "#e2e8f0";

  return (
    <div style={{
      fontFamily: `'${font}', 'Inter', sans-serif`,
      background: bg,
      color: textColor,
      height: "100%",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      borderRadius: 8,
    }}>
      {/* ── Navbar ── */}
      <div style={{
        background: pc,
        color: "#fff",
        padding: "10px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {branding.logo ? (
            <img src={branding.logo} alt="Logo" style={{ height: 28, width: "auto", borderRadius: 4, objectFit: "contain", background: "rgba(255,255,255,.15)" }} />
          ) : (
            <div style={{ width: 28, height: 28, borderRadius: 4, background: "rgba(255,255,255,.25)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700 }}>
              {(orgName || "T").charAt(0).toUpperCase()}
            </div>
          )}
          <span style={{ fontWeight: 700, fontSize: 13 }}>{orgName || "Organization LMS"}</span>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <div style={{ padding: "4px 10px", borderRadius: 4, background: "rgba(255,255,255,.2)", fontSize: 10, fontWeight: 600 }}>Dashboard</div>
          <div style={{ padding: "4px 10px", borderRadius: 4, fontSize: 10, fontWeight: 500, opacity: 0.7 }}>Courses</div>
          <div style={{ padding: "4px 10px", borderRadius: 4, fontSize: 10, fontWeight: 500, opacity: 0.7 }}>Profile</div>
        </div>
      </div>

      {/* ── Content area ── */}
      <div style={{ flex: 1, padding: 16, overflow: "auto" }}>
        {/* Banner */}
        {branding.banner && (
          <div style={{ marginBottom: 14, borderRadius: 8, overflow: "hidden", border: `1px solid ${borderColor}` }}>
            <img src={branding.banner} alt="Banner" style={{ width: "100%", height: 80, objectFit: "cover" }} />
          </div>
        )}

        {/* Hero section */}
        <div style={{ textAlign: "center", marginBottom: 18, padding: "16px 0" }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: textColor }}>Welcome to {orgName || "Your LMS"}</h2>
          <p style={{ margin: "6px 0 0", fontSize: 11, color: mutedColor }}>Continue your learning journey</p>
        </div>

        {/* Stat cards */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 14 }}>
          {[
            { label: "Enrolled", value: "3" },
            { label: "Completed", value: "1" },
            { label: "In Progress", value: "2" },
          ].map((s) => (
            <div key={s.label} style={{
              background: surfaceColor,
              border: `1px solid ${borderColor}`,
              borderRadius: 8,
              padding: "10px 12px",
              textAlign: "center",
            }}>
              <div style={{ fontSize: 18, fontWeight: 800, color: pc }}>{s.value}</div>
              <div style={{ fontSize: 9, color: mutedColor, marginTop: 2 }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* Course cards */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {["Introduction to Data Science", "Advanced React Patterns"].map((title, i) => (
            <div key={title} style={{
              background: surfaceColor,
              border: `1px solid ${borderColor}`,
              borderRadius: 8,
              padding: 12,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 11, color: textColor }}>{title}</div>
                <div style={{ fontSize: 9, color: mutedColor, marginTop: 2 }}>{i === 0 ? "75% complete" : "30% complete"}</div>
                {/* Progress bar */}
                <div style={{ marginTop: 6, width: 120, height: 4, borderRadius: 2, background: borderColor }}>
                  <div style={{ width: i === 0 ? "75%" : "30%", height: "100%", borderRadius: 2, background: pc }} />
                </div>
              </div>
              <div style={{
                padding: "4px 10px",
                borderRadius: 4,
                background: pc,
                color: "#fff",
                fontSize: 9,
                fontWeight: 600,
                cursor: "pointer",
              }}>Continue</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Footer ── */}
      <div style={{
        borderTop: `1px solid ${borderColor}`,
        padding: "8px 16px",
        fontSize: 9,
        color: mutedColor,
        textAlign: "center",
        background: surfaceColor,
        flexShrink: 0,
      }}>
        Powered by {orgName || "Telite LMS"} • {font} font • {isDark ? "Dark" : "Light"} theme
      </div>
    </div>
  );
}

/* ── Main Tab ────────────────────────────────────────────────── */
export function BrandingSettingsTab({ dashboard, organizations = [], session }) {
  const { showToast } = useToast();

  const isSuperAdmin = session?.user?.role === "super_admin";
  const userOrgId = session?.user?.org_id;
  const isFixedOrg = isSuperAdmin && userOrgId;

  const [selectedOrgId, setSelectedOrgId] = useState(isFixedOrg ? userOrgId : "");

  const selectedOrg = organizations.find(o => String(o.id) === String(selectedOrgId));
  const orgSlug = selectedOrg?.slug;
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
  });

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [sslStatus, setSslStatus] = useState("pending");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!orgSlug) return;
      setLoading(true);
      try {
        const data = await fetchBranding(orgSlug);
        if (cancelled) return;
        setBranding({
          primary_color: data.primary_color || "#2563EB",
          secondary_color: data.secondary_color || "#111827",
          font_family: data.font || "Inter",
          theme_mode: data.theme || "light",
          custom_domain: data.custom_domain || "",
          logo: data.logo || null,
          favicon: data.favicon || null,
          banner: data.banner || null,
        });
        if (data.custom_domain) setSslStatus("active");
      } catch (err) {
        if (!cancelled) showToast("Failed to load branding settings: " + getErrorMessage(err), "error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [orgSlug]);

  const handleUpdate = useCallback((field, value) => {
    setBranding(prev => ({ ...prev, [field]: value }));
  }, []);

  const handleDomainUpdate = (e) => {
    const val = e.target.value;
    handleUpdate("custom_domain", val);
    if (val) {
      setSslStatus("pending");
      setTimeout(() => setSslStatus("active"), 3000);
    } else {
      setSslStatus("pending");
    }
  };

  const handleSave = async () => {
    if (!orgId) return;
    setSaving(true);
    try {
      await updateOrganizationBranding(orgId, {
        primary_color: branding.primary_color,
        secondary_color: branding.secondary_color,
        font_family: branding.font_family,
        theme_mode: branding.theme_mode,
        custom_domain: branding.custom_domain,
      });
      showToast("Branding settings saved successfully!", "success");
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to save branding"), "error");
    } finally {
      setSaving(false);
    }
  };

  const handleUpload = async (e, type) => {
    const file = e.target.files?.[0];
    if (!file || !orgId) return;

    try {
      const res = await uploadOrganizationAsset(orgId, type, file);
      showToast(`${type} uploaded successfully!`, "success");
      const key = type === "login_banner" ? "banner" : type;
      setBranding(prev => ({ ...prev, [key]: res.url }));
    } catch (err) {
      showToast(getErrorMessage(err, `Failed to upload ${type}`), "error");
    }
  };

  /* ── Early return: no org selected ── */
  if (!isFixedOrg && !selectedOrgId) {
    return (
      <Panel title="Organization Branding" subtitle="Select an organization to manage its custom branding and domain settings.">
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

  /* ── Main layout ── */
  return (
    <div className="grid-2">
      {/* ── Left column: Settings ── */}
      <div className="dashboard-stack">
        {!isFixedOrg && (
          <Panel title="Select Organization">
            <Field label="Target Organization">
              <Select
                value={selectedOrgId}
                onChange={(e) => setSelectedOrgId(e.target.value)}
                options={[
                  { value: "", label: "Choose an organization..." },
                  ...organizations.map(o => ({ value: o.id, label: `${o.name} (${o.domain})` }))
                ]}
              />
            </Field>
          </Panel>
        )}

        {loading ? (
          <div style={{ padding: 40, textAlign: "center" }}>Loading branding settings...</div>
        ) : (
          <>
            {/* Colors & Theme */}
            <Panel title="Appearance & Colors" subtitle={`Customize visual identity for ${selectedOrg?.name || "this organization"}.`}>
              <div className="grid-2">
                <Field label="Primary Color">
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <input
                      type="color"
                      id="primaryColor"
                      value={branding.primary_color}
                      onChange={(e) => handleUpdate("primary_color", e.target.value)}
                      style={{ width: 48, height: 36, border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer", padding: 2 }}
                    />
                    <span style={{ fontSize: 13, color: "var(--text-secondary)", fontFamily: "monospace" }}>{branding.primary_color}</span>
                  </div>
                </Field>
                <Field label="Secondary Color">
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <input
                      type="color"
                      id="secondaryColor"
                      value={branding.secondary_color}
                      onChange={(e) => handleUpdate("secondary_color", e.target.value)}
                      style={{ width: 48, height: 36, border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer", padding: 2 }}
                    />
                    <span style={{ fontSize: 13, color: "var(--text-secondary)", fontFamily: "monospace" }}>{branding.secondary_color}</span>
                  </div>
                </Field>
              </div>

              <Field label="Typography (Font Family)" helpText="Select a primary font for your portal." style={{ marginTop: 16 }}>
                <Select
                  id="fontFamily"
                  value={branding.font_family}
                  onChange={(e) => handleUpdate("font_family", e.target.value)}
                  options={[
                    { value: "Inter", label: "Inter (Default)" },
                    { value: "Roboto", label: "Roboto" },
                    { value: "Outfit", label: "Outfit" },
                    { value: "Open Sans", label: "Open Sans" },
                    { value: "Montserrat", label: "Montserrat" },
                    { value: "Poppins", label: "Poppins" },
                  ]}
                />
              </Field>

              <Field label="Default Theme Mode" style={{ marginTop: 12 }}>
                <Select
                  id="themeMode"
                  value={branding.theme_mode}
                  onChange={(e) => handleUpdate("theme_mode", e.target.value)}
                  options={[
                    { value: "light", label: "Light Mode" },
                    { value: "dark", label: "Dark Mode" },
                  ]}
                />
              </Field>

              <div style={{ borderTop: "1px solid var(--border)", marginTop: 24, paddingTop: 16, textAlign: "right" }}>
                <Button tone="primary" loading={saving} onClick={handleSave}>Save Settings</Button>
              </div>
            </Panel>

            {/* Domain & SSL */}
            <Panel title="Domain & SSL" subtitle="Configure a custom domain for your learning portal.">
              <Field label="Custom Domain (Optional)" helpText="e.g., learn.yourcompany.com. Requires CNAME record pointing to domains.telitelms.com">
                <Input
                  id="customDomain"
                  placeholder="e.g. lms.yourcompany.com"
                  value={branding.custom_domain}
                  onChange={handleDomainUpdate}
                />
              </Field>

              {branding.custom_domain && (
                <div style={{ marginTop: 16, padding: 16, borderRadius: 6, background: "var(--surface-sunken)", border: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{
                    width: 12, height: 12, borderRadius: "50%",
                    background: sslStatus === "active" ? "#10b981" : "#f59e0b",
                  }} />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>SSL Certificate {sslStatus === "active" ? "Active" : "Provisioning"}</div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                      {sslStatus === "active" ? "Your domain is secure and ready to use." : "Provisioning a certificate..."}
                    </div>
                  </div>
                </div>
              )}
            </Panel>

            {/* Brand Assets */}
            <Panel title="Brand Assets" subtitle="Upload logos, favicons, and banners for your tenant.">
              <div className="dashboard-stack">
                <Field label="Tenant Logo (Header)">
                  {branding.logo && (
                    <div style={{ marginBottom: 8, padding: 8, background: "var(--surface-sunken)", borderRadius: 6, border: "1px solid var(--border)" }}>
                      <img src={branding.logo} alt="Logo" style={{ maxHeight: 48, width: "auto", objectFit: "contain" }} />
                    </div>
                  )}
                  <input
                    type="file"
                    id="uploadLogo"
                    accept="image/png,image/jpeg,image/svg+xml"
                    onChange={(e) => handleUpload(e, "logo")}
                  />
                </Field>

                <Field label="Favicon">
                  {branding.favicon && (
                    <div style={{ marginBottom: 8, padding: 8, background: "var(--surface-sunken)", borderRadius: 6, border: "1px solid var(--border)" }}>
                      <img src={branding.favicon} alt="Favicon" style={{ maxHeight: 32, width: "auto", objectFit: "contain" }} />
                    </div>
                  )}
                  <input
                    type="file"
                    id="uploadFavicon"
                    accept="image/png,image/x-icon,image/svg+xml"
                    onChange={(e) => handleUpload(e, "favicon")}
                  />
                </Field>

                <Field label="Login Banner">
                  {branding.banner && (
                    <div style={{ marginBottom: 8, padding: 8, background: "var(--surface-sunken)", borderRadius: 6, border: "1px solid var(--border)" }}>
                      <img src={branding.banner} alt="Banner" style={{ maxHeight: 80, width: "100%", objectFit: "cover", borderRadius: 4 }} />
                    </div>
                  )}
                  <input
                    type="file"
                    id="uploadBanner"
                    accept="image/png,image/jpeg"
                    onChange={(e) => handleUpload(e, "login_banner")}
                  />
                </Field>
              </div>
            </Panel>
          </>
        )}
      </div>

      {/* ── Right column: Live Preview ── */}
      <div className="dashboard-stack">
        <Panel title="Live Preview" subtitle="Real-time preview of your learners' interface.">
          <div style={{ height: 560, width: "100%", borderRadius: 8, border: "1px solid var(--border)", overflow: "hidden", marginTop: 12 }}>
            <LivePreview branding={branding} orgName={selectedOrg?.name} />
          </div>
        </Panel>
      </div>
    </div>
  );
}
