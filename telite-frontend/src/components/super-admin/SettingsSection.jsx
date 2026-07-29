import { Panel, Badge, IconButton, Button } from "../../components/common/ui";

export default function SettingsSection({ 
  settings, 
  isMoodleSource, 
  newDomain, 
  newDomainLabel, 
  setNewDomain, 
  setNewDomainLabel, 
  handleAddDomain, 
  handleDeleteDomain 
}) {
  if (!settings) {
    return (
      <section id="section-settings">
        <Panel
          title="System settings"
          subtitle="This legacy system-settings service is not available in the current backend."
        >
          <div className="soft-card soft-card--tinted">
            <div className="row-title">Settings unavailable</div>
            <div className="row-subtitle">
              The rest of the super-admin dashboard remains available. Contact an administrator if system settings are required.
            </div>
          </div>
        </Panel>
      </section>
    );
  }

  return (
    <section id="section-settings">
      <Panel
        title="System settings"
        subtitle={isMoodleSource ? "Live Moodle service configuration" : "Current backend and Moodle configuration"}
      >
        <div className="grid-3">
          <div className="soft-card soft-card--tinted">
            <div className="row-subtitle">Moodle URL</div>
            <div className="row-title">{settings?.moodle_url}</div>
          </div>
          <div className="soft-card soft-card--tinted">
            <div className="row-subtitle">{isMoodleSource ? "Moodle release" : "API version"}</div>
            <div className="row-title mono">{isMoodleSource ? settings?.moodle_release : settings?.api_version}</div>
          </div>
          <div className="soft-card soft-card--tinted">
            <div className="row-subtitle">{isMoodleSource ? "Live categories" : "Category slugs"}</div>
            <div className="row-title">
              {isMoodleSource ? settings?.moodle_category_count : (settings?.category_slugs || []).join(", ")}
            </div>
          </div>
        </div>
        <div style={{ marginTop: 24, borderTop: "1px solid var(--border)", paddingTop: 24 }}>
          <div className="row-title" style={{ marginBottom: 4 }}>
            Allowed company domains
          </div>
          <div className="row-subtitle" style={{ marginBottom: 16 }}>
            Restrict signups to these verified email domains for corporate roles.
          </div>
          
          <div className="table-wrap" style={{ marginBottom: 16 }}>
            <table>
              <thead>
                <tr>
                  <th>Domain</th>
                  <th>Organization / Label</th>
                  <th style={{ width: 80 }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {(settings?.allowed_domains || []).map((item) => (
                  <tr key={item.domain}>
                    <td className="mono" style={{ fontWeight: 600 }}>{item.domain}</td>
                    <td>
                      <Badge tone="accent">{item.label}</Badge>
                    </td>
                    <td>
                      <IconButton 
                        icon="trash" 
                        label="Delete domain" 
                        onClick={() => handleDeleteDomain(item.domain)}
                      />
                    </td>
                  </tr>
                ))}
                {(!settings?.allowed_domains || settings.allowed_domains.length === 0) && (
                  <tr>
                    <td colSpan="3" style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)' }}>
                      No allowed domains configured
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="toolbar" style={{ alignItems: "flex-end" }}>
            <label className="field" style={{ flex: 1, maxWidth: 250 }}>
              <span className="field__label">Label (e.g. Acme Corp)</span>
              <input 
                className="field__input" 
                type="text" 
                value={newDomainLabel}
                onChange={(e) => setNewDomainLabel(e.target.value)}
                placeholder="Company Name"
              />
            </label>
            <label className="field" style={{ flex: 1, maxWidth: 250 }}>
              <span className="field__label">Domain</span>
              <input 
                className="field__input" 
                type="text" 
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                placeholder="@company.com"
              />
            </label>
            <Button tone="primary" onClick={handleAddDomain}>
              + Add domain
            </Button>
          </div>
        </div>
        {isMoodleSource && settings?.service_functions?.length ? (
          <div style={{ marginTop: 16 }}>
            <div className="row-title" style={{ marginBottom: 10 }}>
              Exposed Moodle functions
            </div>
            <div className="toolbar">
              {settings.service_functions.map((name) => (
                <Badge key={name} tone="neutral">
                  {name}
                </Badge>
              ))}
            </div>
          </div>
        ) : null}
      </Panel>
    </section>
  );
}
