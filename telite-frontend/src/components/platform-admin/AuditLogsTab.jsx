import { useState, useMemo } from "react";
import { useToast } from "../../components/common/ui";
import { downloadCSV } from "../../utils/csvExport";

export default function AuditLogsTab({ searchQuery }) {
  const { showToast } = useToast();
  const [dateRange, setDateRange] = useState("24h");
  const [orgFilter, setOrgFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [searchTarget, setSearchTarget] = useState("");
  const [expandedRow, setExpandedRow] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const initialAuditLogs = [
    { ts: '2026-05-26 09:40:00', action: 'org.suspend', actor: 'Global Admin', actorInit: 'G', actorColor: 'var(--primary)', target: 'org:2', desc: "Set organization 'Telite Systems' to suspended", status: 'success', severity: 'critical' },
    { ts: '2026-05-26 08:30:00', action: 'org.activate', actor: 'Global Admin', actorInit: 'G', actorColor: 'var(--primary)', target: 'org:2', desc: "Set organization 'Telite Systems' to active", status: 'success', severity: 'info' },
    { ts: '2026-05-25 16:34:00', action: 'admin.suspend', actor: 'Global Admin', actorInit: 'G', actorColor: 'var(--primary)', target: 'user:user-global-admin', desc: "Set admin 'Global Admin' to suspended", status: 'success', severity: 'critical' },
    { ts: '2026-05-25 14:12:00', action: 'admin.restore', actor: 'Global Admin', actorInit: 'G', actorColor: 'var(--primary)', target: 'user:user-global-admin', desc: "Restored admin 'Global Admin' access", status: 'success', severity: 'info' },
    { ts: '2026-05-24 09:12:00', action: 'invite.send', actor: 'Global Admin', actorInit: 'G', actorColor: 'var(--primary)', target: 'email:newadmin@telite.io', desc: 'Invitation sent to newadmin@telite.io', status: 'success', severity: 'info' },
    { ts: '2026-05-23 15:11:00', action: 'course.delete', actor: 'Vikram Sethi', actorInit: 'V', actorColor: '#7C3AED', target: 'course:course-intro-k8s', desc: 'Vikram Sethi deleted course Intro to K8s', status: 'success', severity: 'warning' },
    { ts: '2026-05-22 11:05:00', action: 'enrol.reject', actor: 'Anika Kapoor', actorInit: 'A', actorColor: 'var(--green)', target: 'request:req-varun-rejected', desc: 'Anika Kapoor rejected enrollment Varun N. (other.com)', status: 'success', severity: 'info' },
    { ts: '2026-05-21 08:00:00', action: 'login.fail', actor: 'Unknown', actorInit: '?', actorColor: 'var(--red)', target: '/api/v1/auth/login', desc: 'Failed login attempt from IP: 45.22.112.9 (Tokyo,JP)', status: 'fail', severity: 'critical' },
    { ts: '2026-05-20 15:55:00', action: 'admin.assign', actor: 'Rajan Mehra', actorInit: 'R', actorColor: '#2563EB', target: 'user:user-priya-sharma', desc: 'Rajan Mehra assigned Priya S. → Cloud admin', status: 'success', severity: 'info' },
    { ts: '2026-05-19 14:10:00', action: 'org.create', actor: 'Global Admin', actorInit: 'G', actorColor: 'var(--primary)', target: 'org:1', desc: "Created organization 'Telite University'", status: 'success', severity: 'info' },
  ];

  const actionColors = {
    'org.suspend': '#FEF2F2', 'org.activate': '#ECFDF5', 'org.create': '#EEF2FF',
    'admin.suspend': '#FEF2F2', 'admin.restore': '#ECFDF5', 'admin.assign': '#EFF6FF',
    'invite.send': '#EEF2FF', 'course.delete': '#FFFBEB', 'enrol.reject': '#FFFBEB',
    'login.fail': '#FEF2F2',
  };
  const actionTextColors = {
    'org.suspend': '#991B1B', 'org.activate': '#065F46', 'org.create': 'var(--primary-tx)',
    'admin.suspend': '#991B1B', 'admin.restore': '#065F46', 'admin.assign': '#1E40AF',
    'invite.send': 'var(--primary-tx)', 'course.delete': '#92400E', 'enrol.reject': '#92400E',
    'login.fail': '#991B1B',
  };

  const filteredLogs = useMemo(() => {
    let result = initialAuditLogs;
    if (orgFilter) {
      result = result.filter(l => l.desc.toLowerCase().includes(orgFilter.toLowerCase()));
    }
    if (severityFilter) {
      result = result.filter(l => l.severity === severityFilter);
    }
    const query = (searchTarget || searchQuery || "").toLowerCase();
    if (query && query.length >= 2) {
      result = result.filter(l => 
        l.actor.toLowerCase().includes(query) || 
        l.action.toLowerCase().includes(query) || 
        l.target.toLowerCase().includes(query) ||
        l.desc.toLowerCase().includes(query)
      );
    }
    return result;
  }, [orgFilter, severityFilter, searchTarget, searchQuery, initialAuditLogs]);

  const handleRefresh = () => {
    setRefreshing(true);
    setTimeout(() => {
      setRefreshing(false);
      showToast('System audit logs refreshed successfully', 'success');
    }, 1500);
  };

  const handleExportCSV = () => {
    const headers = ['Timestamp', 'Action', 'Actor', 'Target', 'Description', 'Status', 'Severity'];
    const rows = filteredLogs.map(l => [l.ts, l.action, l.actor, l.target, l.desc, l.status, l.severity]);
    downloadCSV(rows, headers, 'platform-audit-logs.csv');
    showToast('Audit logs exported successfully', 'success');
  };

  return (
    <div className="page" style={{ display: 'block' }}>
      <div className="page-header">
        <div>
          <div className="page-title">System Audit Log</div>
          <div className="page-sub">Real-time mission control monitoring of all administrative actions and security events.</div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={handleExportCSV}>
            <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>download</span> Export CSV
          </button>
          <button className="btn btn-primary" onClick={handleRefresh} disabled={refreshing}>
            <span className="material-symbols-outlined" style={{ fontSize: '15px', animation: refreshing ? 'spin 1.5s linear infinite' : 'none' }}>refresh</span> 
            {refreshing ? 'Refreshing…' : 'Refresh Logs'}
          </button>
        </div>
      </div>

      <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '14px 18px', marginBottom: '16px', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
        <div>
          <label className="field-label" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--tx3)' }}>Date Range</label>
          <select className="field-select" style={{ height: '34px' }} value={dateRange} onChange={e => setDateRange(e.target.value)}>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
        </div>
        <div>
          <label className="field-label" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--tx3)' }}>Organization</label>
          <select className="field-select" style={{ height: '34px' }} value={orgFilter} onChange={e => setOrgFilter(e.target.value)}>
            <option value="">All Organizations</option>
            <option value="Telite University">Telite University</option>
            <option value="Telite Systems">Telite Systems</option>
          </select>
        </div>
        <div>
          <label className="field-label" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--tx3)' }}>Severity</label>
          <select className="field-select" style={{ height: '34px' }} value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}>
            <option value="">All Levels</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>
        </div>
        <div>
          <label className="field-label" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--tx3)' }}>Search Target</label>
          <input className="field-input" style={{ height: '34px' }} value={searchTarget} onChange={e => setSearchTarget(e.target.value)} placeholder="ID, Actor, or IP…" />
        </div>
      </div>

      <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden', marginBottom: '16px' }}>
        <table style={{ width: '100%' }}>
          <thead>
            <tr style={{ background: 'var(--page)' }}>
              <th style={{ padding: '9px 16px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em', width: '160px' }}>Timestamp</th>
              <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Action</th>
              <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Actor</th>
              <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Target</th>
              <th style={{ padding: '9px 14px', textAlign: 'center', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Status</th>
              <th style={{ width: '40px' }}></th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.map((l, i) => {
              const isExpanded = expandedRow === i;
              return (
                <React.Fragment key={i}>
                  <tr style={{ borderTop: '1px solid var(--border2)' }}>
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--fm)', fontSize: '12px', color: 'var(--primary)' }}>{l.ts}</td>
                    <td style={{ padding: '12px 14px' }}>
                      <span style={{ background: actionColors[l.action] || 'var(--border2)', color: actionTextColors[l.action] || 'var(--tx2)', padding: '3px 10px', borderRadius: '100px', fontSize: '11px', fontWeight: 600, fontFamily: 'var(--fm)' }}>{l.action}</span>
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: `${l.actorColor}22`, color: l.actorColor, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', fontWeight: 700, flexShrink: 0 }}>{l.actorInit}</div>
                        <div>
                          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--tx1)' }}>{l.actor}</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--tx1)' }}>{l.target}</div>
                      <div style={{ fontSize: '11px', color: 'var(--tx2)', marginTop: '2px', maxWidth: '280px', lineHeight: '1.4' }}>{l.desc}</div>
                    </td>
                    <td style={{ padding: '12px 14px', textAlign: 'center' }}>
                      <span className="material-symbols-outlined" style={{ color: l.status === 'success' ? 'var(--green)' : 'var(--red)', fontSize: '18px' }}>{l.status === 'success' ? 'check_circle' : 'cancel'}</span>
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <button className="btn-icon btn" onClick={() => setExpandedRow(isExpanded ? null : i)}>
                        <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>{isExpanded ? 'expand_less' : 'expand_more'}</span>
                      </button>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr>
                      <td colSpan="6" style={{ padding: '0' }}>
                        <div style={{ background: '#0F172A', padding: '14px 18px', fontFamily: 'var(--fm)', fontSize: '12px', color: '#94A3B8', lineHeight: '1.6' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <span style={{ color: '#A5B4FC', fontWeight: 700, fontSize: '11px', letterSpacing: '.1em', textTransform: 'uppercase' }}>Metadata Payload</span>
                            <span style={{ color: '#475569', fontSize: '10px' }}>TRACE-ID: {(i + 158302).toString(16).toUpperCase()}-LMS-2026</span>
                          </div>
                          <pre style={{ color: '#E2E8F0', fontSize: '11px', lineHeight: '1.65', overflowX: 'auto', margin: '0' }}>{JSON.stringify({
                            actor: l.actor.toLowerCase().replace(' ', '.'),
                            action: l.action.toUpperCase().replace('.', '_'),
                            target: l.target,
                            severity: l.severity,
                            timestamp: Date.now() - (i * 360000)
                          }, null, 2)}</pre>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
        <div style={{ padding: '10px 16px', borderTop: '1px solid var(--border2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: 'var(--tx2)' }}>
          <span>Showing {filteredLogs.length} events</span>
          <div className="page-btns">
            <div className="pg-btn">‹</div>
            <div className="pg-btn active">1</div>
            <div className="pg-btn">›</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' }}>
        <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px', borderLeft: '4px solid var(--red)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--red)' }}>Security Alerts</span>
            <span className="badge badge-red" style={{ fontSize: '10px' }}>CRITICAL</span>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--tx1)', fontFamily: 'var(--fm)', marginBottom: '8px' }}>12</div>
          <div style={{ height: '4px', background: 'var(--border2)', borderRadius: '4px', overflow: 'hidden', marginBottom: '8px' }}>
            <div style={{ width: '65%', height: '100%', background: 'var(--red)' }}></div>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--tx2)' }}>Suspicious login attempts in Tokyo region.</div>
        </div>
        <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px', borderLeft: '4px solid var(--primary)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--primary)' }}>System Throughput</span>
            <span className="badge badge-green" style={{ fontSize: '10px' }}>HEALTHY</span>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--tx1)', fontFamily: 'var(--fm)', marginBottom: '8px' }}>4.2k</div>
          <div style={{ height: '4px', background: 'var(--border2)', borderRadius: '4px', overflow: 'hidden', marginBottom: '8px' }}>
            <div style={{ width: '82%', height: '100%', background: 'var(--primary)' }}></div>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--tx2)' }}>Admin ops per hour within normal baseline.</div>
        </div>
        <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px', borderLeft: '4px solid var(--green)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--green)' }}>Active Sessions</span>
            <span className="badge badge-green" style={{ fontSize: '10px' }}>STABLE</span>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--tx1)', fontFamily: 'var(--fm)', marginBottom: '8px' }}>84</div>
          <div style={{ height: '4px', background: 'var(--border2)', borderRadius: '4px', overflow: 'hidden', marginBottom: '8px' }}>
            <div style={{ width: '45%', height: '100%', background: 'var(--green)' }}></div>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--tx2)' }}>Authorized administrator sessions currently live.</div>
        </div>
      </div>
    </div>
  );
}
