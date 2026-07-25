import { useState } from "react";
import { useToast } from "../../components/common/ui";
import { useAdminStore } from "../../store/adminConsoleStore";

export default function SettingsTab() {
  const { showToast } = useToast();
  const { settingsState, updateSetting, updateGeneralSetting } = useAdminStore();
  const [saving, setSaving] = useState(false);

  const [platformName, setPlatformName] = useState(settingsState.platformName);
  const [supportEmail, setSupportEmail] = useState(settingsState.supportEmail);
  const [timezone, setTimezone] = useState(settingsState.timezone);
  const [language, setLanguage] = useState(settingsState.language);

  const handleSave = () => {
    if (!platformName.trim() || !supportEmail.trim()) {
      showToast('Please fill in all required fields', 'error');
      return;
    }
    setSaving(true);
    setTimeout(() => {
      updateGeneralSetting('platformName', platformName);
      updateGeneralSetting('supportEmail', supportEmail);
      updateGeneralSetting('timezone', timezone);
      updateGeneralSetting('language', language);
      setSaving(false);
      showToast(`Settings saved successfully — Platform: "${platformName}"`, 'success');
    }, 1200);
  };

  const handleSecToggle = (key) => {
    const nextVal = !settingsState.security[key];
    updateSetting('security', key, nextVal);
    showToast(`${key.replace(/([A-Z])/g, ' $1')} ${nextVal ? 'enabled' : 'disabled'}`, nextVal ? 'success' : 'info');
  };

  const handleNotifToggle = (key) => {
    const nextVal = !settingsState.notifications[key];
    updateSetting('notifications', key, nextVal);
    showToast(`${key.replace(/([A-Z])/g, ' $1')} ${nextVal ? 'enabled' : 'disabled'}`, nextVal ? 'success' : 'info');
  };

  return (
    <div className="page" style={{ display: 'block' }}>
      <div className="page-header">
        <div>
          <div className="page-title">Settings</div>
          <div className="page-sub">Configure your global platform preferences and security policies.</div>
        </div>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          <span className="material-symbols-outlined" style={{ fontSize: '15px', animation: saving ? 'spin 1.5s linear infinite' : 'none' }}>
            {saving ? 'sync' : 'save'}
          </span> 
          {saving ? 'Saving…' : 'Save Changes'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'var(--primary-lt)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className="material-symbols-outlined" style={{ color: 'var(--primary)', fontSize: '18px' }}>tune</span>
            </div>
            <div style={{ fontSize: '17px', fontWeight: 700, color: 'var(--tx1)' }}>General</div>
          </div>
          <div className="field-group">
            <label className="field-label">Platform Name</label>
            <input className="field-input" value={platformName} onChange={e => setPlatformName(e.target.value)} />
          </div>
          <div className="field-group">
            <label className="field-label">Support Email</label>
            <input className="field-input" type="email" value={supportEmail} onChange={e => setSupportEmail(e.target.value)} />
          </div>
          <div className="field-group">
            <label className="field-label">Default Timezone</label>
            <select className="field-select" value={timezone} onChange={e => setTimezone(e.target.value)}>
              <option value="IST">Asia/Kolkata (IST)</option>
              <option value="UTC">UTC</option>
              <option value="EST">America/New_York (EST)</option>
              <option value="PST">America/Los_Angeles (PST)</option>
              <option value="GMT">Europe/London (GMT)</option>
            </select>
          </div>
          <div className="field-group">
            <label className="field-label">Default Language</label>
            <select className="field-select" value={language} onChange={e => setLanguage(e.target.value)}>
              <option value="en">English (US)</option>
              <option value="hi">Hindi</option>
              <option value="fr">French</option>
            </select>
          </div>
        </div>

        <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: '#EFF6FF', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className="material-symbols-outlined" style={{ color: '#2563EB', fontSize: '18px' }}>security</span>
            </div>
            <div style={{ fontSize: '17px', fontWeight: 700, color: 'var(--tx1)' }}>Security</div>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {Object.entries(settingsState.security).map(([key, s]) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px', background: 'var(--page)', borderRadius: 'var(--r-lg)' }}>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--tx1)' }}>{s.label}</div>
                  <div style={{ fontSize: '12px', color: 'var(--tx2)', marginTop: '2px' }}>{s.desc}</div>
                </div>
                <div onClick={() => handleSecToggle(key)} style={{ width: '42px', height: '24px', borderRadius: '12px', background: s.on ? 'var(--primary)' : '#D1D5DB', position: 'relative', transition: 'background .2s', cursor: 'pointer' }}>
                  <div style={{ position: 'absolute', top: '3px', left: s.on ? '20px' : '3px', width: '18px', height: '18px', borderRadius: '50%', background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,.2)', transition: 'left .2s' }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'var(--amber-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span className="material-symbols-outlined" style={{ color: 'var(--amber)', fontSize: '18px' }}>notifications</span>
          </div>
          <div style={{ fontSize: '17px', fontWeight: 700, color: 'var(--tx1)' }}>Notifications</div>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' }}>
          {Object.entries(settingsState.notifications).map(([key, n]) => (
            <div key={key} style={{ padding: '16px', background: 'var(--page)', borderRadius: 'var(--r-lg)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--tx1)' }}>{n.label}</div>
                <div style={{ fontSize: '12px', color: 'var(--tx2)', marginTop: '2px' }}>{n.desc}</div>
              </div>
              <div onClick={() => handleNotifToggle(key)} style={{ width: '42px', height: '24px', borderRadius: '12px', background: n.on ? 'var(--primary)' : '#D1D5DB', position: 'relative', transition: 'background .2s', cursor: 'pointer', marginLeft: '12px', flexShrink: 0 }}>
                <div style={{ position: 'absolute', top: '3px', left: n.on ? '20px' : '3px', width: '18px', height: '18px', borderRadius: '50%', background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,.2)', transition: 'left .2s' }}></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
