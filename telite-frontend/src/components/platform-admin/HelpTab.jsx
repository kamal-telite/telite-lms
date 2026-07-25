import { useState } from "react";
import { useToast } from "../../components/common/ui";

export default function HelpTab({ onOpenOrgModal, onOpenInviteModal, onNavigate }) {
  const { showToast } = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  
  const [guides, setGuides] = useState([
    { title: "Organization Creation & Onboarding", open: true, content: ["Navigate to the Organizations panel and select \"New Organization\".", "Define the organizational domain, type (College / Company), and metadata.", "Assign the primary Administrator and send an invite email.", "Configure feature flags per organization tier in the Feature Flags Matrix."] },
    { title: "Audit Log Export for Compliance", open: false, content: ["Navigate to Audit Logs from the System Section.", "Set Date Range, Organization, and Severity filters as needed.", "Use the Search Target field to isolate specific actor IDs or IP addresses.", "Click \"Export CSV\" to download the filtered results."] },
  ]);

  const shortcuts = [
    { action: "Quick Search", shortcut: "⌘ K", scope: "Global" },
    { action: "New Organization", shortcut: "⌥ N", scope: "Organizations" },
    { action: "Send Invitation", shortcut: "⌥ I", scope: "Admin Control" },
    { action: "Export Audit Log", shortcut: "⇧ E", scope: "Audit Logs" },
    { action: "Toggle Sidebar", shortcut: "⌘ \\", scope: "Global" },
    { action: "Save Settings", shortcut: "⌘ S", scope: "Settings" },
  ];

  const bentoCards = [
    { title: "Organizations", sub: "Multi-tenant Management", icon: "corporate_fare", page: "organizations", bg: "var(--primary-lt)", color: "var(--primary)" },
    { title: "Admin Control", sub: "Permissions & Roles", icon: "admin_panel_settings", page: "admins", bg: "#EFF6FF", color: "#2563EB" },
    { title: "Feature Flags", sub: "System Capabilities", icon: "flag", page: "features", bg: "#ECFDF5", color: "#059669" },
  ];

  const toggleGuide = (idx) => {
    setGuides(current => current.map((g, i) => i === idx ? { ...g, open: !g.open } : g));
  };

  const filteredBento = bentoCards.filter(c => 
    c.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
    c.sub.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredGuides = guides.filter(g => 
    g.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
    g.content.some(line => line.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const filteredShortcuts = shortcuts.filter(s => 
    s.action.toLowerCase().includes(searchQuery.toLowerCase()) || 
    s.scope.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="page" style={{ display: 'block' }}>
      <div className="page-header">
        <div>
          <div className="page-title">Help & Support</div>
          <div className="page-sub">Documentation, guides, keyboard shortcuts, and contact options.</div>
        </div>
      </div>

      <div style={{ background: '#fff', borderRadius: '16px', padding: '32px', border: '1px solid var(--border)', marginBottom: '24px', boxShadow: 'var(--shadow)' }}>
        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
          <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--tx1)' }}>How can we help you?</div>
          <div style={{ fontSize: '13px', color: 'var(--tx2)', marginTop: '4px' }}>Search across platform docs, guides, and troubleshooting articles.</div>
        </div>
        <div style={{ position: 'relative', maxWidth: '640px', margin: '0 auto 16px' }}>
          <span className="material-symbols-outlined" style={{ position: 'absolute', left: '14px', top: '10px', color: 'var(--tx3)' }}>search</span>
          <input 
            className="field-input" 
            style={{ height: '42px', paddingLeft: '42px', paddingRight: '48px', borderRadius: '24px' }} 
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search documentation…" 
          />
          <kbd className="kbd-chip" style={{ position: 'absolute', right: '14px', top: '9px' }}>⌘K</kbd>
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
          <button className="btn btn-primary" onClick={() => showToast('Opening documentation portal…', 'success')}>📖 Read full docs</button>
          <button className="btn btn-secondary" onClick={() => showToast('Tutorial library coming soon', 'info')}>▶ Watch tutorials</button>
          <button className="btn btn-secondary" onClick={() => {
            const el = document.getElementById('helpContactCard');
            el?.scrollIntoView({ behavior: 'smooth' });
          }}>🎧 Contact support</button>
        </div>
      </div>

      {filteredBento.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
          {filteredBento.map((card, idx) => (
            <div 
              key={idx} 
              className="metric-card" 
              onClick={() => onNavigate(card.page)}
              style={{ cursor: 'pointer', transition: 'transform .2s ease, box-shadow .2s ease', border: '1px solid var(--border)' }}
              onMouseOver={e => { e.currentTarget.style.transform = 'translateY(-3px)'; e.currentTarget.style.boxShadow = 'var(--shadow-md)'; }}
              onMouseOut={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none'; }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: card.bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <span className="material-symbols-outlined" style={{ color: card.color }}>{card.icon}</span>
                </div>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--tx1)' }}>{card.title}</div>
                  <div style={{ fontSize: '11px', color: 'var(--tx2)', marginTop: '2px' }}>{card.sub}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <span className="material-symbols-outlined" style={{ color: 'var(--primary)' }}>auto_stories</span>
            <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--tx1)' }}>Step-by-Step Guides</span>
          </div>
          <div style={{ marginBottom: '24px' }}>
            {filteredGuides.map((guide, idx) => (
              <details key={idx} className="help-accordion" open={guide.open}>
                <summary onClick={(e) => { e.preventDefault(); toggleGuide(idx); }}>
                  {guide.title}
                  <span className="material-symbols-outlined chevron">expand_more</span>
                </summary>
                <div className="accordion-body">
                  <ol style={{ listStyleType: 'decimal', paddingLeft: '20px', margin: '0', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {guide.content.map((step, sIdx) => (
                      <li key={sIdx}>{step}</li>
                    ))}
                  </ol>
                </div>
              </details>
            ))}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <span className="material-symbols-outlined" style={{ color: 'var(--primary)' }}>keyboard</span>
            <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--tx1)' }}>Global Keyboard Shortcuts</span>
          </div>
          <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden' }}>
            <table style={{ width: '100%' }}>
              <thead>
                <tr style={{ background: 'var(--page)' }}>
                  <th style={{ padding: '9px 16px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Action</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Shortcut</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Scope</th>
                </tr>
              </thead>
              <tbody>
                {filteredShortcuts.map((s, idx) => (
                  <tr key={idx} style={{ borderTop: '1px solid var(--border2)' }}>
                    <td style={{ padding: '10px 16px', fontSize: '13px' }}>{s.action}</td>
                    <td style={{ padding: '10px 14px' }}><kbd className="kbd-chip">{s.shortcut}</kbd></td>
                    <td style={{ padding: '10px 14px', fontSize: '12px', color: 'var(--tx2)' }}>{s.scope}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div id="helpContactCard" style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px' }}>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--tx1)', marginBottom: '14px' }}>Contact Support</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', background: 'var(--page)', borderRadius: 'var(--r)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'var(--primary-lt)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span className="material-symbols-outlined" style={{ color: 'var(--primary)', fontSize: '16px' }}>chat_bubble</span>
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--tx1)' }}>Live Chat</div>
                    <div style={{ fontSize: '10px', color: 'var(--tx2)' }}>2h avg response</div>
                  </div>
                </div>
                <button onClick={() => showToast('Opening live chat… (feature coming soon)', 'info')} style={{ fontSize: '12px', fontWeight: 700, color: 'var(--primary)', background: 'none', border: 'none', cursor: 'pointer' }}>Start</button>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', background: 'var(--page)', borderRadius: 'var(--r)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: '#F3F0FF', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span className="material-symbols-outlined" style={{ color: '#7C3AED', fontSize: '16px' }}>mail</span>
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--tx1)' }}>Email Ticket</div>
                    <div style={{ fontSize: '10px', color: 'var(--tx2)' }}>24h response time</div>
                  </div>
                </div>
                <a href="mailto:support@telite.io" style={{ fontSize: '12px', fontWeight: 700, color: 'var(--primary)', textDecoration: 'none' }}>Open</a>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', background: 'var(--red-bg)', borderRadius: 'var(--r)', border: '1px solid rgba(220,38,38,.15)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(220,38,38,.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span className="material-symbols-outlined" style={{ color: 'var(--red)', fontSize: '16px' }}>emergency_home</span>
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--red)' }}>Critical Escalation</div>
                    <div style={{ fontSize: '10px', color: 'var(--red-tx)' }}>24/7 Phone Support</div>
                  </div>
                </div>
                <button onClick={() => showToast('Escalation line: +1-800-TELITE-LMS', 'warn')} style={{ fontSize: '12px', fontWeight: 700, color: 'var(--red)', background: 'none', border: 'none', cursor: 'pointer' }}>Call</button>
              </div>
            </div>
          </div>

          <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--tx1)' }}>System Status</div>
              <span className="badge badge-green" style={{ fontSize: '10px' }}>ALL SYSTEMS LIVE</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: 'var(--tx2)' }}>
                <span>Database Clusters</span>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 0 0 rgba(5,150,105,.4)', animation: 'gatewayPulse 2s infinite' }}></div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: 'var(--tx2)' }}>
                <span>SMTP Relay</span>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 0 0 rgba(5,150,105,.4)', animation: 'gatewayPulse 1.8s infinite' }}></div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: 'var(--tx2)' }}>
                <span>Cron Jobs</span>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 0 0 rgba(5,150,105,.4)', animation: 'gatewayPulse 2.5s infinite' }}></div>
              </div>
            </div>
          </div>

          <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px' }}>
            <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.12em', marginBottom: '10px' }}>Admin Quick Links</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div onClick={() => onNavigate("dashboard")} className="help-ql-row">Overview Dashboard <span className="material-symbols-outlined help-ql-arrow">arrow_forward</span></div>
              <div onClick={() => { onNavigate("organizations"); onOpenOrgModal(); }} className="help-ql-row">New Org Wizard <span className="material-symbols-outlined help-ql-arrow">arrow_forward</span></div>
            </div>
          </div>
        </div>
      </div>

      <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '14px 20px', display: 'flex', alignItems: 'center', gap: '16px', marginTop: '20px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', paddingRight: '16px', borderRight: '1px solid var(--border)', flexShrink: 0 }}>
          <span style={{ background: 'var(--primary)', color: '#fff', padding: '3px 10px', borderRadius: '6px', fontFamily: 'var(--fm)', fontSize: '11px', fontWeight: 700 }}>v5.1.0</span>
          <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.1em' }}>Latest Update</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', flex: 1 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px' }}><span style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'var(--primary)', flexShrink: 0 }}></span><strong>Multi-tenant Migration:</strong><span style={{ color: 'var(--tx2)' }}>Optimised data isolation layers.</span></span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px' }}><span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#7C3AED', flexShrink: 0 }}></span><strong>Invitation Flow:</strong><span style={{ color: 'var(--tx2)' }}>Secure automated setup tokens.</span></span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px' }}><span style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'var(--tx3)', flexShrink: 0 }}></span><strong>Security:</strong><span style={{ color: 'var(--tx2)' }}>CVE-2024-9981 Patch deployed.</span></span>
        </div>
        <button onClick={() => showToast('Changelog portal coming soon', 'info')} style={{ fontSize: '12px', fontWeight: 700, color: 'var(--primary)', background: 'none', border: 'none', cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0 }}>View Changelog →</button>
      </div>
    </div>
  );
}
