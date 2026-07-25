import { useState } from "react";
import { useToast } from "../../components/common/ui";
import { downloadCSV } from "../../utils/csvExport";

export default function FeatureFlagsTab() {
  const { showToast } = useToast();
  const [resyncing, setResyncing] = useState(false);
  
  const featureColumns = [
    { key: 'analytics', label: 'Analytics', icon: 'insights' },
    { key: 'ats', label: 'ATS Integration', icon: 'manage_history' },
    { key: 'cloud', label: 'Cloud Modules', icon: 'cloud' },
    { key: 'devops', label: 'Devops Courses', icon: 'terminal' },
    { key: 'pal', label: 'PAL Tracking', icon: 'track_changes' },
  ];

  const [featureFlags, setFeatureFlags] = useState({
    'Telite University': { analytics: true, ats: false, cloud: false, devops: false, pal: true },
    'Telite Systems': { analytics: true, ats: false, cloud: false, devops: false, pal: true },
  });

  const handleFlagClick = (orgName, key) => {
    setFeatureFlags(current => {
      const wasOn = current[orgName][key];
      const nowOn = !wasOn;
      
      showToast(`${key} ${nowOn ? 'enabled' : 'disabled'} for ${orgName}`, nowOn ? 'success' : 'warn');

      return {
        ...current,
        [orgName]: {
          ...current[orgName],
          [key]: nowOn
        }
      };
    });
  };

  const handleResyncAll = () => {
    setResyncing(true);
    setTimeout(() => {
      setResyncing(false);
      showToast('All feature flags synced to cloud storage', 'success');
    }, 2000);
  };

  const handleExportCSV = () => {
    const headers = ['Organization', ...featureColumns.map(c => c.label)];
    const rows = Object.entries(featureFlags).map(([org, flags]) =>
      [org, ...featureColumns.map(c => flags[c.key] ? 'ON' : 'OFF')]
    );
    downloadCSV(rows, headers, 'feature-flags-matrix.csv');
    showToast('Feature flags report downloaded successfully', 'success');
  };

  return (
    <div className="page" style={{ display: 'block' }}>
      <div className="page-header">
        <div>
          <div className="page-title">Feature Flags Matrix</div>
          <div className="page-sub">Manage system capabilities across your client ecosystem.</div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={handleExportCSV}>
            <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>download</span> Export Report
          </button>
          <button className="btn btn-primary" onClick={handleResyncAll} disabled={resyncing}>
            <span className="material-symbols-outlined" style={{ fontSize: '15px', animation: resyncing ? 'spin 1.5s linear infinite' : 'none' }}>refresh</span> 
            {resyncing ? 'Syncing…' : 'Re-sync All'}
          </button>
        </div>
      </div>

      <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden', marginBottom: '20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '260px repeat(6, 1fr)', borderBottom: '1px solid var(--border)', background: 'var(--page)', position: 'sticky', top: '52px', zIndex: 10 }}>
          <div style={{ padding: '12px 18px', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Organization</div>
          {featureColumns.map((c, i) => (
            <div key={i} style={{ padding: '12px 8px', textAlign: 'center' }}>
              <span className="material-symbols-outlined" style={{ color: 'var(--primary)', fontSize: '18px', display: 'block', marginBottom: '4px' }}>{c.icon}</span>
              <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em', lineHeight: '1.3' }}>{c.label}</div>
            </div>
          ))}
        </div>
        
        {Object.entries(featureFlags).map(([orgName, flags]) => (
          <div key={orgName} style={{ display: 'grid', gridTemplateColumns: '260px repeat(6, 1fr)', borderTop: '1px solid var(--border2)', alignItems: 'center' }}>
            <div style={{ padding: '16px 18px', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '34px', height: '34px', borderRadius: '8px', background: 'var(--primary-lt)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span className="material-symbols-outlined" style={{ color: 'var(--primary)', fontSize: '18px' }}>business</span>
              </div>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--tx1)' }}>{orgName}</div>
                <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Tenant</div>
              </div>
            </div>
            
            {featureColumns.map((c, i) => {
              const isOn = flags[c.key];
              return (
                <div key={i} style={{ padding: '14px 8px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                  <div 
                    onClick={() => handleFlagClick(orgName, c.key)}
                    style={{ 
                      width: '40px', 
                      height: '22px', 
                      borderRadius: '11px', 
                      background: isOn ? 'var(--primary)' : '#D1D5DB', 
                      position: 'relative', 
                      transition: 'background .2s', 
                      cursor: 'pointer', 
                      flexShrink: 0 
                    }}
                  >
                    <div style={{ position: 'absolute', top: '3px', left: isOn ? '19px' : '3px', width: '16px', height: '16px', borderRadius: '50%', background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,.2)', transition: 'left .2s' }}></div>
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>

      <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <span className="material-symbols-outlined" style={{ color: 'var(--primary)', fontSize: '18px' }}>info</span>
          <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--tx1)' }}>Configuration Legend</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
            <div style={{ width: '4px', height: '48px', background: 'var(--primary)', borderRadius: '4px', flexShrink: 0, marginTop: '2px' }}></div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--tx1)', marginBottom: '4px' }}>Active State (ON)</div>
              <div style={{ fontSize: '12px', color: 'var(--tx2)', lineHeight: '1.55' }}>Enables the feature key immediately for all users. Syncs with cloud storage in &lt;200ms.</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
            <div style={{ width: '4px', height: '48px', background: 'var(--border)', borderRadius: '4px', flexShrink: 0, marginTop: '2px' }}></div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--tx1)', marginBottom: '4px' }}>Inactive State (OFF)</div>
              <div style={{ fontSize: '12px', color: 'var(--tx2)', lineHeight: '1.55' }}>Disables the module. Users will see a &apos;Coming Soon&apos; placeholder or the entry point hidden.</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
            <div style={{ width: '4px', height: '48px', background: 'var(--primary-lt)', borderRadius: '4px', flexShrink: 0, marginTop: '2px', border: '1px solid var(--primary)' }}></div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--tx1)', marginBottom: '4px' }}>Inherited Settings</div>
              <div style={{ fontSize: '12px', color: 'var(--tx2)', lineHeight: '1.55' }}>Some flags locked based on license tier (Enterprise vs Partner). Check tier settings.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
