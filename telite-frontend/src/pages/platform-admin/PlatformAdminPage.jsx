import React, { useEffect, useState, useMemo, useRef } from "react";
import { createPortal } from "react-dom";
import { Routes, Route, useLocation, useNavigate, Link } from "react-router-dom";
import { useShallow } from "zustand/react/shallow";
import { useToast } from "../../components/common/ui";
import { platformApi } from "../../services/platform";
import "../../styles/platform-admin.css";

// ── CSV Export Utility ──
function downloadCSV(rows, headers, filename) {
  const csv = [headers, ...rows].map(r => r.map(c => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

import { useAdminStore } from "../../store/adminConsoleStore";

export default function PlatformAdminPage({ session, onLogout }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const searchRef = useRef(null);

  const {
    sidebarCollapsed, toggleSidebar,
    searchQuery, setSearchQuery,
    notifications, markAllRead,
    organizations, loadOrganizations,
    admins, loadAdmins,
    syncTenants, triggerGlobalSync, settingsState
  } = useAdminStore(useShallow((state) => ({
    sidebarCollapsed: state.sidebarCollapsed,
    toggleSidebar: state.toggleSidebar,
    searchQuery: state.searchQuery,
    setSearchQuery: state.setSearchQuery,
    notifications: state.notifications,
    markAllRead: state.markAllRead,
    organizations: state.organizations,
    loadOrganizations: state.loadOrganizations,
    admins: state.admins,
    loadAdmins: state.loadAdmins,
    syncTenants: state.syncTenants,
    triggerGlobalSync: state.triggerGlobalSync,
    settingsState: state.settingsState,
  })));

  useEffect(() => {
    loadOrganizations();
    loadAdmins();
  }, [loadOrganizations, loadAdmins]);

  const searchResults = useMemo(() => {
    if (searchQuery.length < 2) return null;
    const lowerQ = searchQuery.toLowerCase();
    const matchingOrgs = organizations.filter(o => 
      o.name?.toLowerCase().includes(lowerQ) || 
      o.domain?.toLowerCase().includes(lowerQ)
    ).slice(0, 3);
    const matchingAdmins = admins.filter(a => 
      (a.full_name || a.name || '').toLowerCase().includes(lowerQ) || 
      (a.email || '').toLowerCase().includes(lowerQ)
    ).slice(0, 3);
    const matchingSync = syncTenants.filter(t =>
      t.catId.toLowerCase().includes(lowerQ) ||
      t.catName.toLowerCase().includes(lowerQ) ||
      t.tenant.toLowerCase().includes(lowerQ)
    ).slice(0, 3);
    return { orgs: matchingOrgs, admins: matchingAdmins, sync: matchingSync };
  }, [searchQuery, organizations, admins, syncTenants]);

  const [notifOpen, setNotifOpen] = useState(false);
  const [appsOpen, setAppsOpen] = useState(false);
  
  const [fabOpen, setFabOpen] = useState(false);
  const [createOrgOpen, setCreateOrgOpen] = useState(false);
  const [inviteAdminOpen, setInviteAdminOpen] = useState(false);
  const [viewOrgData, setViewOrgData] = useState(null);

  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = useState(null);
  const showConfirm = (opts) => new Promise(resolve => setConfirmDialog({ ...opts, resolve }));
  const handleConfirm = () => { confirmDialog?.resolve(true); setConfirmDialog(null); };
  const handleCancel = () => { confirmDialog?.resolve(false); setConfirmDialog(null); };

  const unreadCount = notifications.filter(n => !n.read).length;

  // Global Keyboard Shortcuts (7 fully wired)
  useEffect(() => {
    const handler = (e) => {
      const mod = e.metaKey || e.ctrlKey;
      const shift = e.shiftKey;
      const alt = e.altKey;

      // ⌘K - Focus search
      if (mod && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        searchRef.current?.focus();
      }
      // ⌥N - New Organization
      if (alt && e.key.toLowerCase() === 'n') {
        e.preventDefault();
        navigate('/platform-admin/organizations');
        setCreateOrgOpen(true);
      }
      // ⌥I - Send Invitation
      if (alt && e.key.toLowerCase() === 'i') {
        e.preventDefault();
        navigate('/platform-admin/admins');
        setInviteAdminOpen(true);
      }
      // ⇧E - Export Audit Log
      if (shift && e.key.toUpperCase() === 'E') {
        e.preventDefault();
        navigate('/platform-admin/audit');
        // Trigger CSV download
        showToast('Exporting audit logs…', 'info');
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
        const headers = ['Timestamp', 'Action', 'Actor', 'Target', 'Description', 'Status', 'Severity'];
        const rows = initialAuditLogs.map(l => [l.ts, l.action, l.actor, l.target, l.desc, l.status, l.severity]);
        downloadCSV(rows, headers, 'platform-audit-logs.csv');
        showToast('Audit logs exported successfully', 'success');
      }
      // ⌘\ - Toggle Sidebar
      if (mod && e.key === '\\') {
        e.preventDefault();
        toggleSidebar();
      }
      // ⌘⇧S - Moodle global sync
      if (mod && shift && e.key.toLowerCase() === 's') {
        e.preventDefault();
        navigate('/platform-admin/moodle-sync');
        triggerGlobalSync();
      }
      // ⌘S - Save settings (if on Settings tab)
      if (mod && !shift && e.key.toLowerCase() === 's') {
        if (pathname.endsWith('/settings')) {
          e.preventDefault();
          showToast(`Settings saved successfully — Platform: "${settingsState.platformName}"`, 'success');
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [navigate, toggleSidebar, triggerGlobalSync, pathname, settingsState]);
  
  // Close popovers
  useEffect(() => {
    const handleGlobalClick = (e) => {
      if (!e.target.closest(".popover") && !e.target.closest(".tb-icon-btn")) {
        setNotifOpen(false);
        setAppsOpen(false);
      }
      if (!e.target.closest("#fab") && !e.target.closest(".fab-action-btn")) {
        setFabOpen(false);
      }
    };
    document.addEventListener("click", handleGlobalClick);
    return () => document.removeEventListener("click", handleGlobalClick);
  }, []);

  const navGroups = [
    { section: "Core Section", items: [
      { id: "/platform-admin", icon: "dashboard", label: "Dashboard", exact: true },
      { id: "/platform-admin/organizations", icon: "corporate_fare", label: "Organizations" },
      { id: "/platform-admin/admins", icon: "admin_panel_settings", label: "Admin Control" },
    ]},
    { section: "Insights Section", items: [
      { id: "/platform-admin/moodle-sync", icon: "sync", label: "Moodle Sync" },
      { id: "/platform-admin/analytics", icon: "insights", label: "Analytics" },
    ]},
    { section: "System Section", items: [
      { id: "/platform-admin/audit", icon: "history_edu", label: "Audit Logs" },
      { id: "/platform-admin/features", icon: "flag", label: "Feature Flags" },
      { id: "/platform-admin/settings", icon: "settings", label: "Settings" },
    ]},
  ];

  return (
    <div className="platform-admin-root">
      <aside id="sidebar" className={sidebarCollapsed ? "collapsed" : ""}>
        <div className="sb-head">
          <div className="sb-logo">
            <span className="sb-logo-name">Telite LMS</span>
            <span className="sb-logo-sub">Global Admin Console</span>
          </div>
          <button className="sb-toggle" onClick={toggleSidebar} title="Toggle sidebar">
            <span className="material-symbols-outlined" style={{fontSize: '16px'}}>menu</span>
          </button>
        </div>

        <nav className="sb-nav">
          {navGroups.map((group, idx) => (
            <div className="sb-section" key={idx}>
              <div className="sb-section-label">{group.section}</div>
              {group.items.map(item => {
                const isActive = item.exact ? pathname === item.id : pathname.startsWith(item.id);
                if (item.action) {
                  return (
                    <div key={item.id} className={`nav-item ${isActive ? 'active' : ''}`} onClick={item.action}>
                      <span className="material-symbols-outlined">{item.icon}</span>
                      <span className="nav-label">{item.label}</span>
                    </div>
                  );
                }
                return (
                  <Link key={item.id} to={item.id} className={`nav-item ${isActive ? 'active' : ''}`}>
                    <span className="material-symbols-outlined">{item.icon}</span>
                    <span className="nav-label">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sb-footer">
          <Link to="/platform-admin/help" className={`nav-item ${pathname.startsWith('/platform-admin/help') ? 'active' : ''}`}>
            <span className="material-symbols-outlined">help</span>
            <span className="nav-label">Help</span>
          </Link>
          <div className="nav-item" onClick={onLogout} style={{color: 'var(--tx3)', marginTop: '4px'}}>
            <span className="material-symbols-outlined">logout</span>
            <span className="nav-label">Logout</span>
          </div>
        </div>
      </aside>

      <div id="main-wrap">
        <header id="topbar">
          <div className="tb-left">
            <div className="tb-search" id="searchWrap" style={{position: 'relative'}}>
              <span className="material-symbols-outlined s-ico" style={{fontSize: '15px'}}>search</span>
              <input 
                ref={searchRef}
                type="text" 
                placeholder="Global search… (⌘K)" 
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <span className="material-symbols-outlined s-clear" style={{display:'block', cursor:'pointer'}} onClick={() => setSearchQuery('')}>close</span>
              )}
              {searchResults && (searchResults.orgs?.length > 0 || searchResults.admins?.length > 0 || searchResults.sync?.length > 0) && (
                <div className="popover show" style={{top: '100%', left: 0, width: '320px', marginTop: '8px'}}>
                  <div className="popover-head">
                    <span className="popover-title">Search Results</span>
                  </div>
                  <div style={{padding: '8px 0'}}>
                    {searchResults.orgs?.length > 0 && (
                      <div style={{marginBottom: '12px'}}>
                        <div style={{padding: '0 14px', fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', textTransform: 'uppercase', marginBottom: '4px'}}>Organizations</div>
                        {searchResults.orgs.map(org => (
                          <div key={org.id} className="notif-item" style={{padding: '6px 14px', gap: '8px', alignItems: 'center'}} onClick={() => { setSearchQuery(''); navigate('/platform-admin/organizations'); }}>
                            <div className="notif-icon-wrap" style={{width: '24px', height: '24px', background: 'var(--primary-lt)'}}>
                              <span className="material-symbols-outlined" style={{color: 'var(--primary)', fontSize: '14px'}}>business</span>
                            </div>
                            <div>
                              <div className="notif-title" style={{fontSize: '12px'}}>{org.name}</div>
                              <div className="notif-sub" style={{fontSize: '10px'}}>{org.domain}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {searchResults.admins?.length > 0 && (
                      <div style={{marginBottom: '12px'}}>
                        <div style={{padding: '0 14px', fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', textTransform: 'uppercase', marginBottom: '4px'}}>Administrators</div>
                        {searchResults.admins.map(admin => (
                          <div key={admin.id} className="notif-item" style={{padding: '6px 14px', gap: '8px', alignItems: 'center'}} onClick={() => { setSearchQuery(''); navigate('/platform-admin/admins'); }}>
                            <div className="avatar" style={{width: '24px', height: '24px', fontSize: '10px', background: 'var(--green-bg)', color: 'var(--green)'}}>
                              {(admin.full_name || admin.email || 'U').substring(0, 2).toUpperCase()}
                            </div>
                            <div>
                              <div className="notif-title" style={{fontSize: '12px'}}>{admin.full_name || admin.email}</div>
                              <div className="notif-sub" style={{fontSize: '10px'}}>{admin.role?.replace('_', ' ')}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {searchResults.sync?.length > 0 && (
                      <div>
                        <div style={{padding: '0 14px', fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', textTransform: 'uppercase', marginBottom: '4px'}}>Moodle Sync Categories</div>
                        {searchResults.sync.map(t => (
                          <div key={t.catId} className="notif-item" style={{padding: '6px 14px', gap: '8px', alignItems: 'center'}} onClick={() => { setSearchQuery(''); navigate('/platform-admin/moodle-sync'); }}>
                            <div className="notif-icon-wrap" style={{width: '24px', height: '24px', background: 'var(--primary-lt)'}}>
                              <span className="material-symbols-outlined" style={{color: 'var(--primary)', fontSize: '14px'}}>sync</span>
                            </div>
                            <div>
                              <div className="notif-title" style={{fontSize: '12px'}}>{t.catId} - {t.catName}</div>
                              <div className="notif-sub" style={{fontSize: '10px'}}>{t.tenant}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
            <nav className="tb-nav">
              <Link to="/platform-admin" className={`tb-nav-item ${pathname === '/platform-admin' ? 'active' : ''}`}>Overview</Link>
              <Link to="/platform-admin/organizations" className={`tb-nav-item ${pathname.startsWith('/platform-admin/organizations') ? 'active' : ''}`}>Organizations</Link>
              <Link to="/platform-admin/admins" className={`tb-nav-item ${pathname.startsWith('/platform-admin/admins') ? 'active' : ''}`}>Admin Control</Link>
            </nav>
          </div>
          <div className="tb-right">
            <div style={{position: 'relative'}}>
              <button className="tb-icon-btn" onClick={() => { setNotifOpen(!notifOpen); setAppsOpen(false); }} title="Notifications">
                <span className="material-symbols-outlined">notifications</span>
                {unreadCount > 0 && <span className="badge-dot"></span>}
              </button>
              <div className={`popover ${notifOpen ? 'show' : ''}`} style={{right: 0, top: '38px', width: '300px'}}>
                <div className="popover-head">
                  <span className="popover-title">Notifications</span>
                  <span style={{fontSize: '11px', color: 'var(--primary)', cursor: 'pointer', fontWeight: 600}} onClick={markAllRead}>Mark all read</span>
                </div>
                <div>
                  {notifications.map(n => {
                    const iconMap = { user: 'person_add', sync: 'sync', security: 'lock', org: 'corporate_fare' };
                    const colorMap = { user: 'var(--primary)', sync: 'var(--amber)', security: 'var(--red)', org: 'var(--green)' };
                    const bgMap = { user: 'var(--primary-lt)', sync: 'var(--amber-bg)', security: 'var(--red-bg)', org: 'var(--green-bg)' };
                    return (
                      <div key={n.id} className={`notif-item ${!n.read ? 'unread' : ''}`}>
                        <div className="notif-icon-wrap" style={{background: bgMap[n.type] || 'var(--primary-lt)'}}>
                          <span className="material-symbols-outlined" style={{color: colorMap[n.type] || 'var(--primary)', fontSize: '16px'}}>{iconMap[n.type] || 'info'}</span>
                        </div>
                        <div>
                          <div className="notif-title">{n.title}</div>
                          <div className="notif-sub">{n.sub}</div>
                          <div className="notif-time">{n.time}</div>
                        </div>
                        {!n.read && <div style={{width: '6px', height: '6px', borderRadius: '50%', background: 'var(--primary)', marginTop: '4px', flexShrink: 0}}></div>}
                      </div>
                    );
                  })}
                </div>
                <div className="popover-foot"><a onClick={() => showToast('All notifications view — coming soon', 'info')}>View all notifications</a></div>
              </div>
            </div>
            
            <div style={{position: 'relative'}}>
              <button className="tb-icon-btn" onClick={() => { setAppsOpen(!appsOpen); setNotifOpen(false); }} title="Quick links">
                <span className="material-symbols-outlined">apps</span>
              </button>
              <div className={`popover ${appsOpen ? 'show' : ''}`} style={{right: 0, top: '38px', width: '220px'}}>
                <div className="popover-head"><span className="popover-title">Quick Links</span></div>
                <div className="quick-link-grid">
                  <div className="ql-item" onClick={() => { navigate('/platform-admin/analytics'); setAppsOpen(false); }}>
                    <div className="ql-icon" style={{background: '#EFF6FF'}}><span className="material-symbols-outlined" style={{color: '#2563EB'}}>insights</span></div>
                    <span className="ql-label">Analytics</span>
                  </div>
                  <div className="ql-item" onClick={() => { navigate('/platform-admin/audit'); setAppsOpen(false); }}>
                    <div className="ql-icon" style={{background: 'var(--primary-lt)'}}><span className="material-symbols-outlined" style={{color: 'var(--primary)'}}>history_edu</span></div>
                    <span className="ql-label">Audit Logs</span>
                  </div>
                  <div className="ql-item" onClick={() => { navigate('/platform-admin/features'); setAppsOpen(false); }}>
                    <div className="ql-icon" style={{background: '#ECFDF5'}}><span className="material-symbols-outlined" style={{color: '#059669'}}>flag</span></div>
                    <span className="ql-label">Features</span>
                  </div>
                  <div className="ql-item" onClick={() => { navigate('/platform-admin/settings'); setAppsOpen(false); }}>
                    <div className="ql-icon" style={{background: '#FFFBEB'}}><span className="material-symbols-outlined" style={{color: '#D97706'}}>settings</span></div>
                    <span className="ql-label">Settings</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="tb-user" onClick={() => showToast('Profile settings — coming soon', 'info')}>
              <div className="tb-avatar">{session?.user?.name?.[0] || 'G'}</div>
              <div className="tb-user-info">
                <div className="tb-user-name">{session?.user?.name || 'Global Admin'}</div>
                <div className="tb-user-role">Platform Admin</div>
              </div>
            </div>
          </div>
        </header>

        <Routes>
          <Route index element={<OverviewTab searchQuery={searchQuery} />} />
          <Route path="organizations" element={<OrganizationsTab searchQuery={searchQuery} showConfirm={showConfirm} onOpenCreateOrg={() => setCreateOrgOpen(true)} onViewOrg={(org) => setViewOrgData(org)} />} />
          <Route path="admins" element={<AdminControlTab searchQuery={searchQuery} showConfirm={showConfirm} onOpenInvite={() => setInviteAdminOpen(true)} />} />
          <Route path="analytics" element={<AnalyticsTab searchQuery={searchQuery} />} />
          <Route path="audit" element={<AuditLogsTab searchQuery={searchQuery} />} />
          <Route path="features" element={<FeatureFlagsTab />} />
          <Route path="settings" element={<SettingsTab />} />
          <Route path="moodle-sync" element={<MoodleSyncTab searchQuery={searchQuery} />} />
          <Route path="help" element={<HelpTab onOpenOrgModal={() => setCreateOrgOpen(true)} onOpenInviteModal={() => setInviteAdminOpen(true)} onNavigate={(page) => navigate(`/platform-admin/${page}`)} />} />
          <Route path="*" element={<div className="page" style={{display:'block'}}><div style={{textAlign:'center', marginTop:'100px', color:'var(--tx3)'}}>This module is currently being updated. Please check back later.</div></div>} />
        </Routes>
      </div>
      
      {/* FAB - Global Add Button */}
      <div id="fab">
        <div className={`fab-sub ${fabOpen ? 'show' : ''}`}>
          <div className="fab-action">
            <div className="fab-action-btn" onClick={() => { setCreateOrgOpen(true); setFabOpen(false); navigate('/platform-admin/organizations'); }}>
              <span className="material-symbols-outlined" style={{fontSize: '15px'}}>business</span> New Organization
            </div>
          </div>
          <div className="fab-action">
            <div className="fab-action-btn" onClick={() => { setInviteAdminOpen(true); setFabOpen(false); navigate('/platform-admin/admins'); }}>
              <span className="material-symbols-outlined" style={{fontSize: '15px'}}>person_add</span> Send Invitation
            </div>
          </div>
          <div className="fab-action">
            <div className="fab-action-btn" onClick={() => { navigate('/platform-admin/moodle-sync'); triggerGlobalSync(); setFabOpen(false); }}>
              <span className="material-symbols-outlined" style={{fontSize: '15px'}}>sync</span> Sync Moodle
            </div>
          </div>
        </div>
        <button className="fab-main" onClick={() => setFabOpen(!fabOpen)}>
          <span className="material-symbols-outlined" style={{fontSize: '22px'}}>add</span>
        </button>
      </div>

      <CreateOrganizationModal open={createOrgOpen} onClose={() => setCreateOrgOpen(false)} />
        <InviteAdminModal
          open={inviteAdminOpen}
          onClose={() => setInviteAdminOpen(false)}
          onInvited={loadAdmins}
        />
        <ViewOrganizationModal org={viewOrgData} onClose={() => setViewOrgData(null)} />

      {/* Confirmation Dialog */}
      {confirmDialog && createPortal(
        <div className="overlay" style={{zIndex: 250}} onClick={handleCancel}>
          <div className="modal modal-sm" onClick={e => e.stopPropagation()} style={{maxWidth: '400px'}}>
            <div className="modal-head">
              <div>
                <div className="modal-title">{confirmDialog.title}</div>
                <div className="modal-sub">{confirmDialog.description}</div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={handleCancel}>Cancel</button>
              <button className={`btn ${confirmDialog.variant === 'destructive' ? 'btn-danger' : 'btn-primary'}`} onClick={handleConfirm}>
                {confirmDialog.confirmLabel || 'Confirm'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      <div id="toast-wrap"></div>
    </div>
  );
}

// ═══════════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════════
function OverviewTab({ searchQuery }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { isSyncing, syncProgress, lastSync, triggerSync, organizations } = useAdminStore();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const handleSync = async () => {
    await triggerSync();
    showToast('Moodle sync completed — 99.8% success rate', 'success');
  };

  useEffect(() => {
    platformApi.getAnalyticsOverview()
      .then(res => setData(res.data))
      .catch(() => showToast("Failed to load overview", "error"))
      .finally(() => setLoading(false));
  }, [showToast]);

  const stats = data || { total_orgs: 2, total_colleges: 1, total_companies: 1, total_users: 46, total_super_admins: 1 };

  return (
    <div className="page" style={{display: 'block'}}>
      <div className="page-header">
        <div>
          <div className="page-title">Platform Overview</div>
          <div className="page-sub">Global control center for all organizations</div>
        </div>
        <div style={{display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r)', fontSize: '12px', color: 'var(--tx2)'}}>
          <span className="material-symbols-outlined" style={{fontSize: '15px'}}>calendar_today</span>
          May 18, 2026
        </div>
      </div>

      <div className="status-bar">
        <div style={{display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '12px'}}>
          <div className="status-pill green"><span className="pulse"></span> All Systems Operational</div>
          <div className="status-info"><span className="material-symbols-outlined" style={{fontSize: '15px', color: 'var(--tx3)'}}>hub</span> Moodle Gateway: <strong>API Connected · 142ms</strong></div>
          <div className="status-info"><span className="material-symbols-outlined" style={{fontSize: '15px', color: 'var(--tx3)'}}>people</span> <strong>2.4k</strong>&nbsp;Active Sessions</div>
        </div>
        <div className="status-info" style={{fontSize: '11px'}}><span className="material-symbols-outlined" style={{fontSize: '14px'}}>update</span> Last check: 1m ago</div>
      </div>

      <div className="metric-grid">
        <div className="metric-card">
          <div className="mc-top">
            <div className="mc-icon" style={{background: 'var(--primary-lt)'}}><span className="material-symbols-outlined" style={{color: 'var(--primary)'}}>corporate_fare</span></div>
            <span className="mc-badge badge-indigo">+12.5%</span>
          </div>
          <div className="mc-num">{stats.total_orgs}</div>
          <div className="mc-label">Total Orgs</div>
        </div>
        <div className="metric-card">
          <div className="mc-top">
            <div className="mc-icon" style={{background: 'var(--primary-lt)'}}><span className="material-symbols-outlined" style={{color: 'var(--primary)'}}>account_balance</span></div>
            <span className="mc-badge badge-indigo">+4.2%</span>
          </div>
          <div className="mc-num">{stats.total_colleges}</div>
          <div className="mc-label">Colleges</div>
        </div>
        <div className="metric-card">
          <div className="mc-top">
            <div className="mc-icon" style={{background: 'var(--primary-lt)'}}><span className="material-symbols-outlined" style={{color: 'var(--primary)'}}>business_center</span></div>
            <span className="mc-badge badge-indigo">+8.1%</span>
          </div>
          <div className="mc-num">{stats.total_companies}</div>
          <div className="mc-label">Companies</div>
        </div>
        <div className="metric-card">
          <div className="mc-top">
            <div className="mc-icon" style={{background: 'var(--primary-lt)'}}><span className="material-symbols-outlined" style={{color: 'var(--primary)'}}>groups</span></div>
            <span className="mc-badge badge-indigo">+24%</span>
          </div>
          <div className="mc-num">{stats.total_users}</div>
          <div className="mc-label">Total Users</div>
        </div>
      </div>

      <div className="dash-grid">
        <div className="dash-panel">
          <div className="dash-panel-head">
            <span className="dash-panel-title">Recent Organizations</span>
            <span style={{fontSize: '12px', color: 'var(--primary)', fontWeight: 600, cursor: 'pointer'}} onClick={() => navigate('/platform-admin/organizations')}>View All</span>
          </div>
          <table>
            <thead><tr>
              <th>Organization</th><th>Type</th><th>Users</th><th>Status</th><th></th>
            </tr></thead>
            <tbody>
              {organizations.slice(0, 3).map(o => (
                <tr key={o.id}>
                  <td>
                    <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                      <div className="avatar" style={{background: o.type?.toLowerCase() === 'college' ? 'var(--primary-lt)' : '#ECFDF5', color: o.type?.toLowerCase() === 'college' ? 'var(--primary)' : '#059669', fontSize: '12px'}}>
                        {(o.name || 'O').substring(0,2).toUpperCase()}
                      </div>
                      <span style={{fontWeight: 600, fontSize: '13px'}}>{o.name}</span>
                    </div>
                  </td>
                  <td><span className={`badge ${o.type?.toLowerCase() === 'college' ? 'badge-indigo' : 'badge-gray'}`}>{o.type?.toUpperCase()}</span></td>
                  <td style={{fontFamily: 'var(--fm)'}}>{o.user_count || 1}</td>
                  <td><span className={`status-dot ${o.status?.toLowerCase() === 'active' ? 'active' : 'suspended'}`}>{o.status === 'active' ? 'Active' : 'Suspended'}</span></td>
                  <td><button className="btn btn-sm btn-secondary" onClick={() => navigate('/platform-admin/organizations')}>View</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="dash-panel">
          <div className="dash-panel-head">
            <span className="dash-panel-title">Live Activity</span>
            <div className="live-badge"><span className="live-dot"></span>Live</div>
          </div>
          <div style={{padding: '0 16px'}}>
            <div className="activity-list">
              <div className="act-item">
                <div className="act-icon" style={{background: 'var(--primary-lt)'}}><span className="material-symbols-outlined" style={{color: 'var(--primary)', fontSize: '16px'}}>person_add</span></div>
                <div><div className="act-title">New User Registered</div><div className="act-sub">John Doe → Telite University</div><div className="act-time">2 minutes ago</div></div>
              </div>
              <div className="act-item">
                <div className="act-icon" style={{background: 'var(--amber-bg)'}}><span className="material-symbols-outlined" style={{color: 'var(--amber)', fontSize: '16px'}}>sync</span></div>
                <div><div className="act-title">Moodle Sync Started</div><div className="act-sub">Auto-sync for Oxford Academy</div><div className="act-time">15 minutes ago</div></div>
              </div>
              <div className="act-item">
                <div className="act-icon" style={{background: 'var(--red-bg)'}}><span className="material-symbols-outlined" style={{color: 'var(--red)', fontSize: '16px'}}>lock</span></div>
                <div><div className="act-title">Security Alert</div><div className="act-sub">Failed login on Admin Console</div><div className="act-time">45 minutes ago</div></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="sync-strip">
        <div className="sync-icon"><span className="material-symbols-outlined" style={{color: '#fff', fontSize: '20px'}}>sync_alt</span></div>
        <div className="sync-info">
          <div className="sync-title">Moodle Global Sync Status</div>
          <div className="sync-sub" id="syncSubText">Last complete sync: {lastSync} (99.8% Success Rate)</div>
        </div>
        <div className="sync-progress">
          <div className="sync-next">Next Sync: 12:00 PM</div>
          <div className="sync-bar-wrap"><div className="sync-bar" id="syncBar" style={{width: `${syncProgress}%`}}></div></div>
        </div>
        <button className="btn btn-secondary" disabled={isSyncing} onClick={handleSync}>
          {isSyncing ? (
            <><span className="material-symbols-outlined" style={{fontSize: '14px', animation: 'spin 1s linear infinite'}}>sync</span> Syncing…</>
          ) : 'Sync Now'}
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════
// ORGANIZATIONS
// ═══════════════════════════════════════════════
function OrganizationsTab({ searchQuery, showConfirm, onOpenCreateOrg, onViewOrg }) {
  const { organizations: orgs, updateOrgStatus, loadOrganizations } = useAdminStore();
  const { showToast } = useToast();
  const [activeFilter, setActiveFilter] = useState('all');
  const [filterPopoverOpen, setFilterPopoverOpen] = useState(false);
  const [filterState, setFilterState] = useState({ status: 'all', type: 'all' });

  const filteredOrgs = useMemo(() => {
    let result = orgs;
    if (activeFilter === 'college') result = result.filter(o => o.type?.toLowerCase() === 'college');
    else if (activeFilter === 'company') result = result.filter(o => o.type?.toLowerCase() === 'company');
    else if (activeFilter === 'inactive') result = result.filter(o => o.status?.toLowerCase() === 'inactive' || o.status?.toLowerCase() === 'suspended');
    
    // Apply advanced filter
    if (filterState.status !== 'all') result = result.filter(o => o.status?.toLowerCase() === filterState.status);
    if (filterState.type !== 'all') result = result.filter(o => o.type?.toLowerCase() === filterState.type);
    
    if (searchQuery && searchQuery.length >= 2) {
      const lowerQ = searchQuery.toLowerCase();
      result = result.filter(o => o.name?.toLowerCase().includes(lowerQ) || o.domain?.toLowerCase().includes(lowerQ));
    }
    return result;
  }, [orgs, activeFilter, searchQuery, filterState]);

  const handleToggleStatus = async (org) => {
    const isSuspending = org.status === 'active';
    const confirmed = await showConfirm({
      title: isSuspending ? 'Suspend Organization?' : 'Restore Organization?',
      description: isSuspending
        ? `This will prevent all users at ${org.name} from logging in.`
        : `This will restore access for all users at ${org.name}.`,
      confirmLabel: isSuspending ? 'Suspend' : 'Restore',
      variant: isSuspending ? 'destructive' : 'default',
    });
    if (!confirmed) return;
    const newStatus = isSuspending ? 'suspended' : 'active';
    try {
      await updateOrgStatus(org.id, newStatus);
      showToast(`${org.name} ${newStatus}`, 'success');
    } catch (err) {
      showToast('Failed to update status', 'error');
    }
  };

  const exportOrgsCSV = () => {
    const headers = ['ID', 'Name', 'Type', 'Domain', 'Status', 'User Count'];
    const rows = filteredOrgs.map(o => [o.id, o.name, o.type, o.domain, o.status, o.user_count || 0]);
    downloadCSV(rows, headers, `organizations-${Date.now()}.csv`);
    showToast('CSV exported successfully', 'success');
  };

  return (
    <div className="page" style={{display: 'block'}}>
      <div className="page-header">
        <div>
          <div className="page-title">Organizations</div>
          <div className="page-sub">Manage educational institutions and corporate partners.</div>
        </div>
        <button className="btn btn-primary" onClick={onOpenCreateOrg}>
          <span className="material-symbols-outlined" style={{fontSize: '16px'}}>add</span> New Organization
        </button>
      </div>

      <div className="filter-row">
        <div className="filter-pills">
          <div className={`fp ${activeFilter === 'all' ? 'active' : ''}`} onClick={() => setActiveFilter('all')}>All</div>
          <div className={`fp ${activeFilter === 'college' ? 'active' : ''}`} onClick={() => setActiveFilter('college')}>Colleges</div>
          <div className={`fp ${activeFilter === 'company' ? 'active' : ''}`} onClick={() => setActiveFilter('company')}>Companies</div>
          <div className={`fp ${activeFilter === 'inactive' ? 'active' : ''}`} onClick={() => setActiveFilter('inactive')}>Inactive</div>
        </div>
        <div className="filter-actions">
          <div style={{position: 'relative'}}>
            <button className="btn btn-secondary btn-sm" onClick={() => setFilterPopoverOpen(!filterPopoverOpen)}>
              <span className="material-symbols-outlined" style={{fontSize: '14px'}}>filter_list</span> Filter
            </button>
            {filterPopoverOpen && (
              <div className="popover show" style={{right: 0, top: '36px', width: '240px', padding: '12px'}}>
                <div style={{marginBottom: '10px'}}>
                  <label style={{fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', display: 'block', marginBottom: '4px'}}>Status</label>
                  <select className="field-select" value={filterState.status} onChange={e => setFilterState(s => ({...s, status: e.target.value}))}>
                    <option value="all">All statuses</option>
                    <option value="active">Active</option>
                    <option value="suspended">Suspended</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
                <div style={{marginBottom: '10px'}}>
                  <label style={{fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', display: 'block', marginBottom: '4px'}}>Type</label>
                  <select className="field-select" value={filterState.type} onChange={e => setFilterState(s => ({...s, type: e.target.value}))}>
                    <option value="all">All types</option>
                    <option value="college">College</option>
                    <option value="company">Company</option>
                  </select>
                </div>
                <div style={{display: 'flex', gap: '6px'}}>
                  <button className="btn btn-secondary btn-sm" style={{flex: 1}} onClick={() => { setFilterState({status:'all',type:'all'}); setFilterPopoverOpen(false); }}>Clear</button>
                  <button className="btn btn-primary btn-sm" style={{flex: 1}} onClick={() => setFilterPopoverOpen(false)}>Apply</button>
                </div>
              </div>
            )}
          </div>
          <button className="btn btn-secondary btn-sm" onClick={exportOrgsCSV}>
            <span className="material-symbols-outlined" style={{fontSize: '14px'}}>download</span> Export CSV
          </button>
        </div>
      </div>

      <div style={{display: 'grid', gridTemplateColumns: '2.5fr 1fr 1.2fr 1.5fr .8fr .8fr', padding: '8px 18px', marginBottom: '4px'}}>
        <span style={{fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em'}}>Organization</span>
        <span style={{fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em'}}>Type</span>
        <span style={{fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em'}}>Domain</span>
        <span style={{fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em'}}>Super Admin</span>
        <span style={{fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em'}}>Status</span>
        <span style={{fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em'}}>Actions</span>
      </div>

      <div>
        {orgs.length === 0 ? (
          <div style={{textAlign: 'center', padding: '40px', color: 'var(--tx3)', fontSize: '13px'}}>Loading organizations...</div>
        ) : filteredOrgs.length ? (
          filteredOrgs.map(o => {
            const isCollege = o.type?.toLowerCase() === 'college';
            const isActive = o.status === 'active';
            const isSuspended = o.status === 'suspended' || o.status === 'inactive';
            
            return (
              <div key={o.id} className="org-row org-grid">
                <div style={{display: 'flex', alignItems: 'center', gap: '12px'}}>
                  <div className="org-icon">
                    <span className="material-symbols-outlined" style={{color: 'var(--primary)', fontSize: '18px'}}>
                      {isCollege ? 'account_balance' : 'business'}
                    </span>
                  </div>
                  <div>
                    <div className="org-name">{o.name}</div>
                    <div className="org-id">ID: {o.id}</div>
                  </div>
                </div>
                <div><span className={`badge ${isCollege ? 'badge-indigo' : 'badge-gray'}`}>{o.type?.toUpperCase()}</span></div>
                <div className="org-domain">{o.domain}</div>
                <div className="admin-chip">
                  <div className="admin-avatar">AD</div>
                  <span style={{fontSize: '12px', color: 'var(--tx2)'}}>Admin Users ({o.user_count || 1})</span>
                </div>
                <div>
                  <span className={`status-dot ${o.status?.toLowerCase()}`}>{isActive ? 'Active' : 'Suspended'}</span>
                </div>
                <div style={{display: 'flex', gap: '6px'}}>
                  <button className="btn-icon btn" title="View organization" onClick={() => onViewOrg(o)}>
                    <span className="material-symbols-outlined" style={{fontSize: '15px'}}>visibility</span>
                  </button>
                  <button 
                    className={`btn-icon btn ${isSuspended ? 'success' : 'warn'}`} 
                    title={isSuspended ? 'Restore' : 'Suspend'} 
                    onClick={() => handleToggleStatus(o)}
                  >
                    <span className="material-symbols-outlined" style={{fontSize: '15px'}}>{isSuspended ? 'check_circle' : 'block'}</span>
                  </button>
                </div>
              </div>
            );
          })
        ) : (
          <div style={{textAlign: 'center', padding: '40px', color: 'var(--tx3)', fontSize: '13px'}}>No organizations match this filter.</div>
        )}
      </div>

      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', fontSize: '12px', color: 'var(--tx3)', padding: '0 4px'}}>
        <span>Showing {filteredOrgs.length} organizations</span>
        <div className="page-btns">
          <div className="pg-btn">‹</div>
          <div className="pg-btn active">1</div>
          <div className="pg-btn">›</div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════
// ADMIN CONTROL
// ═══════════════════════════════════════════════
function AdminControlTab({ searchQuery, showConfirm, onOpenInvite }) {
  const {
    admins,
    pendingInvitations,
    updateAdminStatus,
    deleteAdmin,
    loadAdmins,
    resendInvitation,
    revokeInvitation,
  } = useAdminStore();
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState('super_admins');
  const [adminFilterOpen, setAdminFilterOpen] = useState(false);
  const [adminFilter, setAdminFilter] = useState({ role: 'all', status: 'all' });
  const adminRows = Array.isArray(admins) ? admins : [];
  const inviteRows = Array.isArray(pendingInvitations) ? pendingInvitations : [];

  const displayedAdmins = useMemo(() => {
    let result = [];
    if (activeTab === 'super_admins') result = adminRows.filter(a => a.role === 'super_admin');
    else if (activeTab === 'all_admins') result = adminRows;
    else if (activeTab === 'pending') result = inviteRows;

    // Apply advanced filter
    if (adminFilter.role !== 'all') result = result.filter(a => a.role === adminFilter.role);
    if (adminFilter.status !== 'all') result = result.filter(a => a.status === adminFilter.status);

    if (searchQuery && searchQuery.length >= 2) {
      const lowerQ = searchQuery.toLowerCase();
      result = result.filter(a => 
        (a.full_name || a.name || '').toLowerCase().includes(lowerQ) || 
        (a.email || '').toLowerCase().includes(lowerQ)
      );
    }
    return result;
  }, [adminRows, inviteRows, activeTab, searchQuery, adminFilter]);

  const adminTabs = [
    { key: 'super_admins', label: 'Super Admins', count: adminRows.filter(a => a.role === 'super_admin').length },
    { key: 'all_admins',   label: 'All Org Admins', count: adminRows.length },
    { key: 'pending',      label: 'Pending Invitations', count: inviteRows.length },
  ];
  const activeAdminCount = adminRows.filter(a => a.status === 'active').length;
  const suspendedAdminCount = adminRows.filter(a => a.status === 'suspended').length;

  const getInviteDeliveryBadge = (invite) => {
    switch (invite.delivery_status) {
      case 'delivered':
        return { className: 'badge badge-green', label: 'Delivered' };
      case 'failed':
        return { className: 'badge badge-red', label: 'Delivery Failed' };
      default:
        return { className: 'badge badge-amber', label: 'Pending' };
    }
  };

  const formatInviteTimestamp = (invite) => {
    const value = invite.last_sent_at || invite.delivery_attempted_at || invite.created_at;
    if (!value) return '—';
    return value.replace('T', ' ').slice(0, 16);
  };

  const handleToggleAdminStatus = async (admin) => {
    const isSuspending = admin.status === 'active';
    const confirmed = await showConfirm({
      title: isSuspending ? 'Suspend Admin?' : 'Restore Admin?',
      description: isSuspending
        ? `This will revoke access for ${admin.full_name || admin.email}.`
        : `This will restore access for ${admin.full_name || admin.email}.`,
      confirmLabel: isSuspending ? 'Suspend' : 'Restore',
      variant: isSuspending ? 'destructive' : 'default',
    });
    if (!confirmed) return;
    const nextStatus = isSuspending ? 'suspended' : 'active';
    try {
      await updateAdminStatus(admin.id, nextStatus);
      showToast(`Admin ${nextStatus}`, 'success');
    } catch (err) {
      showToast('Failed to update admin status', 'error');
    }
  };

  const handleDeleteAdmin = async (admin) => {
    const confirmed = await showConfirm({
      title: 'Delete Admin?',
      description: `This will permanently remove ${admin.full_name || admin.email}. This action cannot be undone.`,
      confirmLabel: 'Delete',
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await deleteAdmin(admin.id);
      showToast(`${admin.full_name || admin.email} deleted`, 'success');
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to delete admin', 'error');
    }
  };

  const handleRevokeInvite = async (invite) => {
    const confirmed = await showConfirm({
      title: 'Revoke Invitation?',
      description: `This will cancel the pending invitation to ${invite.email}.`,
      confirmLabel: 'Revoke',
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await revokeInvitation(invite.id);
      showToast(`Invitation to ${invite.email} revoked`, 'success');
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to revoke invitation', 'error');
    }
  };

  const handleResendInvite = async (invite) => {
    try {
      const updatedInvite = await resendInvitation(invite.id);
      const status = updatedInvite?.delivery_status;
      if (status === 'delivered') {
        showToast(`Invitation resent to ${invite.email}`, 'success');
        return;
      }
      showToast(
        updatedInvite?.delivery_error || 'Invitation resend was recorded, but email delivery failed.',
        'error'
      );
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to resend invitation', 'error');
    }
  };

  const handlePasswordReset = async (admin) => {
    const confirmed = await showConfirm({
      title: 'Reset Password?',
      description: `This will send a password reset email to ${admin.email}.`,
      confirmLabel: 'Reset Password',
    });
    if (!confirmed) return;
    try {
      await platformApi.resetAdminPassword(admin.id);
      showToast(`Password reset sent to ${admin.email}`, 'success');
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to send password reset', 'error');
    }
  };

  const exportAdminsCSV = () => {
    const headers = ['Name', 'Email', 'Organization', 'Role', 'Status'];
    const rows = displayedAdmins.map(a => [a.full_name || a.name || '', a.email || '', a.org_name || '', a.role || '', a.status || '']);
    downloadCSV(rows, headers, `admins-${activeTab}-${Date.now()}.csv`);
    showToast('CSV exported successfully', 'success');
  };

  const colors = ['#4648D4','#059669','#D97706','#DC2626','#7C3AED'];

  return (
    <div className="page" style={{display: 'block'}}>
      <div className="page-header">
        <div>
          <div className="page-title">Admin Control</div>
          <div className="page-sub">Manage organization-level access and system-wide configurations.</div>
        </div>
        <button className="btn btn-primary" onClick={onOpenInvite}>
          <span className="material-symbols-outlined" style={{fontSize: '16px'}}>person_add</span> Send Invitation
        </button>
      </div>

      <div className="metric-grid" style={{gridTemplateColumns: 'repeat(4, 1fr)'}}>
        <div className="metric-card">
          <div className="mc-top">
            <div className="mc-icon" style={{background: 'var(--primary-lt)'}}><span className="material-symbols-outlined" style={{color: 'var(--primary)'}}>shield_person</span></div>
            <span className="mc-badge badge-indigo">+12%</span>
          </div>
          <div className="mc-num">{adminTabs[0].count}</div>
          <div className="mc-label">Total Super Admins</div>
        </div>
        <div className="metric-card">
          <div className="mc-top">
            <div className="mc-icon" style={{background: 'var(--green-bg)'}}><span className="material-symbols-outlined" style={{color: 'var(--green)'}}>fiber_manual_record</span></div>
            <span className="mc-badge badge-green">+4 today</span>
          </div>
          <div className="mc-num">{activeAdminCount}</div>
          <div className="mc-label">Active Admins</div>
        </div>
        <div className="metric-card">
          <div className="mc-top">
            <div className="mc-icon" style={{background: 'var(--red-bg)'}}><span className="material-symbols-outlined" style={{color: 'var(--red)'}}>block</span></div>
            <span className="mc-badge badge-red">-2%</span>
          </div>
          <div className="mc-num">{suspendedAdminCount}</div>
          <div className="mc-label">Suspended Accounts</div>
        </div>
        <div className="metric-card">
          <div className="mc-top">
            <div className="mc-icon" style={{background: '#FFFBEB'}}><span className="material-symbols-outlined" style={{color: 'var(--amber)'}}>hourglass_empty</span></div>
            <span className="mc-badge badge-amber">Waiting</span>
          </div>
          <div className="mc-num">{adminTabs[2].count}</div>
          <div className="mc-label">Pending Invites</div>
        </div>
      </div>

      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 0}}>
        <div className="tabs" style={{marginBottom: 0, flex: 1}}>
          {adminTabs.map(tab => (
            <div key={tab.key} className={`tab ${activeTab === tab.key ? 'active' : ''}`} onClick={() => setActiveTab(tab.key)}>
              {tab.label} <span className="tab-count">{tab.count}</span>
            </div>
          ))}
        </div>
        <div style={{display: 'flex', gap: '6px', paddingBottom: '4px', position: 'relative'}}>
          <button className="btn-icon btn" title="Send invite" onClick={onOpenInvite}>
            <span className="material-symbols-outlined" style={{fontSize: '16px'}}>person_add</span>
          </button>
          <div style={{position: 'relative'}}>
            <button className="btn-icon btn" title="Filter" onClick={() => setAdminFilterOpen(!adminFilterOpen)}>
              <span className="material-symbols-outlined" style={{fontSize: '16px'}}>filter_list</span>
            </button>
            {adminFilterOpen && (
              <div className="popover show" style={{right: 0, top: '36px', width: '240px', padding: '12px'}}>
                <div style={{marginBottom: '10px'}}>
                  <label style={{fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', display: 'block', marginBottom: '4px'}}>Role</label>
                  <select className="field-select" value={adminFilter.role} onChange={e => setAdminFilter(s => ({...s, role: e.target.value}))}>
                    <option value="all">All roles</option>
                    <option value="super_admin">Super Admin</option>
                    <option value="category_admin">Category Admin</option>
                  </select>
                </div>
                <div style={{marginBottom: '10px'}}>
                  <label style={{fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', display: 'block', marginBottom: '4px'}}>Status</label>
                  <select className="field-select" value={adminFilter.status} onChange={e => setAdminFilter(s => ({...s, status: e.target.value}))}>
                    <option value="all">All statuses</option>
                    <option value="active">Active</option>
                    <option value="suspended">Suspended</option>
                  </select>
                </div>
                <div style={{display: 'flex', gap: '6px'}}>
                  <button className="btn btn-secondary btn-sm" style={{flex: 1}} onClick={() => { setAdminFilter({role:'all',status:'all'}); setAdminFilterOpen(false); }}>Clear</button>
                  <button className="btn btn-primary btn-sm" style={{flex: 1}} onClick={() => setAdminFilterOpen(false)}>Apply</button>
                </div>
              </div>
            )}
          </div>
          <button className="btn-icon btn" title="Download CSV" onClick={exportAdminsCSV}>
            <span className="material-symbols-outlined" style={{fontSize: '16px'}}>download</span>
          </button>
        </div>
      </div>

      <div className="data-table" style={{marginTop: '12px'}}>
        <div className="table-wrap">
          <table>
            <thead><tr>
              <th>Name</th><th>Organization</th><th>Role</th><th>Last Login</th><th>Status</th><th></th>
            </tr></thead>
            <tbody>
              {admins.length === 0 && pendingInvitations.length === 0 ? (
                <tr><td colSpan="6" style={{textAlign: 'center', padding: '32px', color: 'var(--tx3)', fontSize: '13px'}}>Loading administrators...</td></tr>
              ) : displayedAdmins.length ? (
                displayedAdmins.map((a, i) => {
                  const isPending = activeTab === 'pending';
                  const isSuspended = a.status === 'suspended';
                  const inviteDeliveryBadge = isPending ? getInviteDeliveryBadge(a) : null;
                  const roleBadge = a.role === 'super_admin' ?
                    <span className="badge badge-indigo">super admin</span> :
                    <span className="badge badge-gray">{a.role?.replace('_', ' ')}</span>;

                  return (
                    <tr key={a.id || a.email || i} className="group">
                      <td>
                        <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                          <div className="avatar" style={{background: `${colors[i%colors.length]}22`, color: colors[i%colors.length]}}>
                            {(a.full_name || a.email || 'U').substring(0,2).toUpperCase()}
                          </div>
                          <div>
                            <div style={{fontWeight: 600, fontSize: '13px'}}>{a.full_name || a.name || a.email}</div>
                            <div style={{fontSize: '11px', color: 'var(--tx3)'}}>{a.email}</div>
                            {isPending && a.delivery_error ? (
                              <div style={{fontSize: '11px', color: 'var(--red)', marginTop: '2px'}}>
                                {a.delivery_error}
                              </div>
                            ) : null}
                          </div>
                        </div>
                      </td>
                      <td>
                        <div style={{fontSize: '13px', fontWeight: 500}}>{a.org_name || 'Telite System'}</div>
                        <span className="badge badge-gray" style={{fontSize: '10px', marginTop: '2px'}}>Enterprise</span>
                      </td>
                      <td>{roleBadge}</td>
                      <td style={{fontFamily: 'var(--fm)', fontSize: '12px', color: 'var(--tx2)'}}>
                        {isPending ? formatInviteTimestamp(a) : '2024-05-21 09:12'}
                      </td>
                      <td>
                        {isPending ? (
                          <span className={inviteDeliveryBadge.className}>{inviteDeliveryBadge.label}</span>
                        ) : (
                          <span className={`status-dot ${a.status}`}>{a.status === 'active' ? 'Active' : 'Suspended'}</span>
                        )}
                      </td>
                      <td>
                        <div className="row-actions">
                          {isPending ? (
                            <>
                              <button className="btn-icon btn" title="Resend invite" onClick={() => handleResendInvite(a)}><span className="material-symbols-outlined" style={{fontSize: '15px'}}>mail</span></button>
                              <button className="btn-icon btn danger" title="Revoke invite" onClick={() => handleRevokeInvite(a)}><span className="material-symbols-outlined" style={{fontSize: '15px'}}>close</span></button>
                            </>
                          ) : isSuspended ? (
                            <>
                              <button className="btn-icon btn success" title="Restore admin" onClick={() => handleToggleAdminStatus(a)}><span className="material-symbols-outlined" style={{fontSize: '15px'}}>settings_backup_restore</span></button>
                              <button className="btn-icon btn danger" title="Delete admin" onClick={() => handleDeleteAdmin(a)}><span className="material-symbols-outlined" style={{fontSize: '15px'}}>delete</span></button>
                            </>
                          ) : (
                            <>
                              <button className="btn-icon btn" title="Reset password" onClick={() => handlePasswordReset(a)}><span className="material-symbols-outlined" style={{fontSize: '15px'}}>key</span></button>
                              <button className="btn-icon btn warn" title="Suspend" onClick={() => handleToggleAdminStatus(a)}><span className="material-symbols-outlined" style={{fontSize: '15px'}}>block</span></button>
                              <button className="btn-icon btn danger" title="Delete" onClick={() => handleDeleteAdmin(a)}><span className="material-symbols-outlined" style={{fontSize: '15px'}}>delete</span></button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })
              ) : (
                <tr><td colSpan="6" style={{textAlign: 'center', padding: '32px', color: 'var(--tx3)', fontSize: '13px'}}>No records found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="pagination">
          <span>Showing {displayedAdmins.length} administrators</span>
          <div className="page-btns">
            <div className="pg-btn">‹</div>
            <div className="pg-btn active">1</div>
            <div className="pg-btn">›</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════
// MODALS
// ═══════════════════════════════════════════════

export function CreateOrganizationModal({ open, onClose, onCreated }) {
  const { showToast } = useToast();
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ name: "", type: "college", domain: "", slug: "", super_admin_email: "", moodle_setup: "manual" });

  if (!open) return null;

  const canNext = (step === 1 && form.name.trim() && form.domain.trim()) || step === 2 || step === 3;

  return createPortal(
    <div className="overlay" onClick={onClose} style={{zIndex: 200}}>
      <div className="modal modal-lg" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div className="modal-title">Create New Organization</div>
            <div className="modal-sub">Set up a new educational or corporate partner.</div>
          </div>
          <button className="modal-close" onClick={onClose}><span className="material-symbols-outlined">close</span></button>
        </div>
        
        <div className="modal-body">
          <div className="stepper">
            <div className={`step ${step > 1 ? 'done' : step === 1 ? 'active' : 'pending'}`}>
              <div className="step-num">1</div><div className="step-label">Basic Info</div><div className="step-line"></div>
            </div>
            <div className={`step ${step > 2 ? 'done' : step === 2 ? 'active' : 'pending'}`}>
              <div className="step-num">2</div><div className="step-label">Admin Setup</div><div className="step-line"></div>
            </div>
            <div className={`step ${step === 3 ? 'active' : 'pending'}`}>
              <div className="step-num">3</div><div className="step-label">Review</div>
            </div>
          </div>

          {step === 1 && (
            <div>
              <div className="field-group">
                <label className="field-label">Organization Name <span style={{color: 'var(--red)'}}>*</span></label>
                <input value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="field-input" placeholder="e.g. Stanford University" type="text" />
              </div>
              <div className="field-row">
                <div className="field-group">
                  <label className="field-label">Organization Type <span style={{color: 'var(--red)'}}>*</span></label>
                  <select value={form.type} onChange={e => setForm({...form, type: e.target.value})} className="field-select">
                    <option value="college">College</option>
                    <option value="company">Company</option>
                  </select>
                </div>
                <div className="field-group">
                  <label className="field-label">Custom Domain <span style={{color: 'var(--red)'}}>*</span></label>
                  <input value={form.domain} onChange={e => setForm({...form, domain: e.target.value})} className="field-input" placeholder="e.g. stanford.edu" type="text" />
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <div className="invite-hint">
                <span className="material-symbols-outlined" style={{fontSize: '15px', verticalAlign: 'middle'}}>info</span>
                If provided, an invitation link will be emailed to onboard via /set-password.
              </div>
              <div className="field-group">
                <label className="field-label">Super Admin Email (Optional)</label>
                <input value={form.super_admin_email} onChange={e => setForm({...form, super_admin_email: e.target.value})} className="field-input" placeholder="admin@example.edu" type="email" />
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <div className="field-group">
                <label className="field-label">Moodle Setup Mode</label>
                <select value={form.moodle_setup} onChange={e => setForm({...form, moodle_setup: e.target.value})} className="field-select">
                  <option value="manual">Manual Configuration</option>
                  <option value="auto">Automatic (Create Moodle Category)</option>
                </select>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          {step > 1 && <button onClick={() => setStep(s=>s-1)} disabled={submitting} className="btn btn-secondary">Back</button>}
          <button onClick={onClose} disabled={submitting} className="btn btn-secondary">Cancel</button>
          
          {step < 3 ? (
            <button onClick={() => setStep(s=>s+1)} disabled={!canNext} className="btn btn-primary">Next Step</button>
          ) : (
            <button 
              disabled={submitting || !form.name.trim() || !form.domain.trim()} 
              onClick={async () => {
                setSubmitting(true);
                try {
                  await platformApi.createOrganization({
                    name: form.name.trim(), type: form.type, domain: form.domain.trim(),
                    slug: form.slug.trim() || null, super_admin_email: form.super_admin_email.trim() || null,
                    moodle_setup: form.moodle_setup,
                  });
                  showToast("Organization created", "success");
                  onCreated?.();
                  onClose();
                } catch (err) {
                  showToast(err.response?.data?.detail || "Failed to create organization", "error");
                } finally {
                  setSubmitting(false);
                }
              }}
              className="btn btn-primary"
            >
              {submitting ? 'Creating...' : 'Create Organization'}
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}

export function InviteAdminModal({ open, onClose, onInvited }) {
  const { showToast } = useToast();
  const [orgs, setOrgs] = useState([]);
  const [loadingOrgs, setLoadingOrgs] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ org_id: "", email: "", role: "super_admin", name: "" });

  useEffect(() => {
    if (!open) return;
    setSubmitting(false);
    setForm({ org_id: "", email: "", role: "super_admin", name: "" });
    setLoadingOrgs(true);
    platformApi.listOrganizations({ limit: 100 })
      .then(res => setOrgs(res.data.orgs))
      .catch(() => showToast("Failed to load organizations", "error"))
      .finally(() => setLoadingOrgs(false));
  }, [open, showToast]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.email.trim()) return showToast("Email is required", "error");

    setSubmitting(true);
    try {
      await platformApi.inviteAdmin({
        email: form.email.trim(),
        role: form.role,
        org_id: form.org_id || null
      });
      showToast(`Invitation sent to ${form.email}`, "success");
      onInvited?.();
      onClose();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to send invitation", "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;
  return createPortal(
    <div className="overlay" onClick={onClose} style={{zIndex: 200}}>
      <div className="modal modal-sm" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div className="modal-title">Send Invitation</div>
            <div className="modal-sub">Invite a new admin to manage an organization.</div>
          </div>
          <button className="modal-close" onClick={onClose}><span className="material-symbols-outlined">close</span></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="field-group">
              <label className="field-label">Email address <span style={{color:'var(--red)'}}>*</span></label>
              <input className="field-input" type="email" required value={form.email} onChange={e => setForm({...form, email: e.target.value})} placeholder="admin@university.edu" />
            </div>
            <div className="field-group">
              <label className="field-label">Full Name <span style={{color:'var(--red)'}}>*</span></label>
              <input className="field-input" required value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="Dr. Priya Sharma" />
            </div>
            <div className="field-group">
              <label className="field-label">Role</label>
              <select className="field-select" value={form.role} onChange={e => setForm({...form, role: e.target.value})}>
                <option value="super_admin">Platform Super Admin</option>
                <option value="org_admin">Organization Admin</option>
              </select>
            </div>
            {form.role === 'org_admin' && (
              <div className="field-group">
                <label className="field-label">Organization <span style={{color:'var(--red)'}}>*</span></label>
                <select className="field-select" required value={form.org_id} onChange={e => setForm({...form, org_id: e.target.value})}>
                  <option value="">Select Organization</option>
                  {orgs.map(o => (
                    <option key={o.id} value={o.id}>{o.name}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" disabled={submitting || (form.role === 'org_admin' && !form.org_id)} className="btn btn-primary">
              <span className="material-symbols-outlined" style={{fontSize: '15px'}}>send</span> {submitting ? 'Sending...' : 'Send Invitation'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}

export function ViewOrganizationModal({ org, onClose }) {
  if (!org) return null;
  const isCollege = org.type?.toLowerCase() === 'college';
  const isActive = org.status === 'active';
  
  return createPortal(
    <div className="overlay" onClick={onClose} style={{zIndex: 200}}>
      <div className="modal modal-md" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <div style={{display: 'flex', alignItems: 'center', gap: '12px'}}>
            <div className="org-icon" style={{width: '40px', height: '40px', background: isCollege ? 'var(--primary-lt)' : '#ECFDF5', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
              <span className="material-symbols-outlined" style={{color: isCollege ? 'var(--primary)' : '#059669', fontSize: '24px'}}>
                {isCollege ? 'account_balance' : 'business'}
              </span>
            </div>
            <div>
              <div className="modal-title">{org.name}</div>
              <div className="modal-sub">ID: {org.id} &bull; <a href={`https://${org.domain}`} target="_blank" rel="noreferrer" style={{color: 'var(--primary)'}}>{org.domain}</a></div>
            </div>
          </div>
          <button className="modal-close" onClick={onClose}><span className="material-symbols-outlined">close</span></button>
        </div>
        
        <div className="modal-body" style={{padding: '20px'}}>
          <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px'}}>
            <div className="info-block">
              <div style={{fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', textTransform: 'uppercase', marginBottom: '4px'}}>Status</div>
              <div><span className={`status-dot ${org.status?.toLowerCase()}`}>{isActive ? 'Active' : 'Suspended'}</span></div>
            </div>
            <div className="info-block">
              <div style={{fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', textTransform: 'uppercase', marginBottom: '4px'}}>Type</div>
              <div><span className={`badge ${isCollege ? 'badge-indigo' : 'badge-gray'}`}>{org.type?.toUpperCase()}</span></div>
            </div>
            <div className="info-block">
              <div style={{fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', textTransform: 'uppercase', marginBottom: '4px'}}>Total Users</div>
              <div style={{fontSize: '14px', fontWeight: 600, fontFamily: 'var(--fm)'}}>{org.user_count || 0}</div>
            </div>
            <div className="info-block">
              <div style={{fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', textTransform: 'uppercase', marginBottom: '4px'}}>Registered On</div>
              <div style={{fontSize: '14px'}}>{org.created_at ? org.created_at.split('T')[0] : 'N/A'}</div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>,
    document.body
  );
}

// ═══════════════════════════════════════════════
// ANALYTICS
// ═══════════════════════════════════════════════
export function AnalyticsTab({ searchQuery }) {
  const { showToast } = useToast();
  const [chartPeriod, setChartPeriod] = useState("monthly");
  const [liveMonitorActive, setLiveMonitorActive] = useState(false);
  const [healthFilter, setHealthFilter] = useState("all");
  const [filterPopoverOpen, setFilterPopoverOpen] = useState(false);
  const [alertOrg, setAlertOrg] = useState(null);
  
  // Bar Chart Data state
  const [barChartData, setBarChartData] = useState([
    { label: 'JAN', val: 32 }, { label: 'FEB', val: 41 }, { label: 'MAR', val: 58 },
    { label: 'APR', val: 50 }, { label: 'MAY', val: 74 }, { label: 'JUN', val: 89 }
  ]);

  const monthlyData = [
    { label: 'JAN', val: 32 }, { label: 'FEB', val: 41 }, { label: 'MAR', val: 58 },
    { label: 'APR', val: 50 }, { label: 'MAY', val: 74 }, { label: 'JUN', val: 89 }
  ];
  const weeklyData = [
    { label: 'W1', val: 18 }, { label: 'W2', val: 25 }, { label: 'W3', val: 22 },
    { label: 'W4', val: 31 }, { label: 'W5', val: 28 }, { label: 'W6', val: 35 }
  ];

  useEffect(() => {
    if (!liveMonitorActive) {
      setBarChartData(chartPeriod === 'weekly' ? weeklyData : monthlyData);
    }
  }, [chartPeriod, liveMonitorActive]);

  // Live Monitor loop — pauses when tab is hidden to save CPU
  useEffect(() => {
    if (!liveMonitorActive) {
      return undefined;
    }

    showToast('Live monitor activated — updating every 2s', 'success');

    const interval = setInterval(() => {
      if (document.hidden) {
        return;
      }
      setBarChartData((current) => current.map((item) => {
        const delta = Math.floor(Math.random() * 20 - 10);
        const newVal = Math.max(10, Math.min(120, item.val + delta));
        return { ...item, val: newVal };
      }));
    }, 2000);

    return () => clearInterval(interval);
  }, [liveMonitorActive, showToast]);

  const handlePeriodChange = (e) => {
    setChartPeriod(e.target.value);
  };

  const toggleLiveMonitor = () => {
    setLiveMonitorActive(prev => {
      if (prev) showToast('Live monitor stopped', 'info');
      return !prev;
    });
  };

  // Donut Chart Segment Highlighting
  const [donutSegment, setDonutSegment] = useState({ label: "CORP", pct: "64%" });
  const highlightSegment = (type, pct) => {
    setDonutSegment({ label: type.toUpperCase(), pct });
  };

  // Usage Table Orgs list
  const initialAnalyticsOrgs = [
    { id: 'NV', name: 'Nexus Ventures', plan: 'Premium Plan', users: 2450, storageUsed: 750, storageTotal: 1000, health: 'Excellent', color: '#4F46E5' },
    { id: 'AU', name: 'Apex University', plan: 'Edu Enterprise', users: 4812, storageUsed: 2200, storageTotal: 5000, health: 'Stable', color: '#2563EB' },
    { id: 'SL', name: 'Skyline Logistics', plan: 'Standard Plan', users: 890, storageUsed: 460, storageTotal: 500, health: 'Warning', color: '#D97706' },
    { id: 'TU', name: 'Telite University', plan: 'Enterprise', users: 46, storageUsed: 12, storageTotal: 100, health: 'Excellent', color: '#4648D4' },
    { id: 'TS', name: 'Telite Systems', plan: 'Enterprise', users: 0, storageUsed: 2, storageTotal: 100, health: 'Stable', color: '#059669' },
  ];

  const filteredOrgs = useMemo(() => {
    let result = initialAnalyticsOrgs;
    if (healthFilter !== 'all') {
      result = result.filter(o => o.health.toLowerCase() === healthFilter.toLowerCase());
    }
    if (searchQuery && searchQuery.length >= 2) {
      const q = searchQuery.toLowerCase();
      result = result.filter(o => o.name.toLowerCase().includes(q) || o.plan.toLowerCase().includes(q));
    }
    return result;
  }, [healthFilter, searchQuery]);

  // Dynamic dropdown popup menu on row click
  const [activeMenuId, setActiveMenuId] = useState(null);
  const toggleRowMenu = (orgId) => {
    setActiveMenuId(prev => prev === orgId ? null : orgId);
  };

  const handleExportCSV = (org = null) => {
    showToast(org ? `Generating CSV report for ${org.name}…` : 'Generating CSV report…', 'info');
    setTimeout(() => {
      const headers = ['Organization', 'Plan', 'Active Users', 'Storage Used', 'Health'];
      const orgsToExport = org ? [org] : initialAnalyticsOrgs;
      const rows = orgsToExport.map(o => [o.name, o.plan, o.users, `${o.storageUsed}GB/${o.storageTotal}GB`, o.health]);
      downloadCSV(rows, headers, org ? `analytics-${org.id.toLowerCase()}.csv` : 'platform-analytics.csv');
      showToast('Analytics report downloaded successfully', 'success');
    }, 1200);
  };

  const maxVal = Math.max(...barChartData.map(d => d.val), 1);

  return (
    <div className="page" style={{ display: 'block' }}>
      <div className="page-header">
        <div>
          <div className="page-title">Platform Analytics</div>
          <div className="page-sub">Monitor real-time user growth, organizational distribution, and detailed engagement metrics.</div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={() => handleExportCSV()}>
            <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>download</span> Export CSV
          </button>
          <button 
            className="btn" 
            style={{ 
              backgroundColor: liveMonitorActive ? 'var(--green)' : 'var(--primary)',
              color: '#fff'
            }} 
            onClick={toggleLiveMonitor}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '15px', animation: liveMonitorActive ? 'spin 1.5s linear infinite' : 'none' }}>
              {liveMonitorActive ? 'sync' : 'monitor_heart'}
            </span> 
            {liveMonitorActive ? 'Live: ON' : 'Live Monitor'}
          </button>
        </div>
      </div>

      {/* KPI Strip */}
      <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: '20px', overflow: 'hidden' }}>
        <div style={{ padding: '20px 24px', borderRight: '1px solid var(--border)' }}>
          <div style={{ fontSize: '12px', color: 'var(--tx2)', fontWeight: 500, marginBottom: '6px' }}>Total Active Users</div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: 'var(--primary)', fontFamily: 'var(--fm)', letterSpacing: '-.5px' }}>12,482</div>
          <div style={{ fontSize: '11px', color: 'var(--green)', fontWeight: 600, marginTop: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}>
            <span className="material-symbols-outlined" style={{ fontSize: '13px' }}>trending_up</span>+14%
          </div>
        </div>
        <div style={{ padding: '20px 24px', borderRight: '1px solid var(--border)' }}>
          <div style={{ fontSize: '12px', color: 'var(--tx2)', fontWeight: 500, marginBottom: '6px' }}>Daily Completion Rate</div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: 'var(--primary)', fontFamily: 'var(--fm)', letterSpacing: '-.5px' }}>78.4%</div>
          <div style={{ fontSize: '11px', color: 'var(--green)', fontWeight: 600, marginTop: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}>
            <span className="material-symbols-outlined" style={{ fontSize: '13px' }}>trending_up</span>+2%
          </div>
        </div>
        <div style={{ padding: '20px 24px', borderRight: '1px solid var(--border)' }}>
          <div style={{ fontSize: '12px', color: 'var(--tx2)', fontWeight: 500, marginBottom: '6px' }}>Avg. Session Time</div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: 'var(--tx1)', fontFamily: 'var(--fm)', letterSpacing: '-.5px' }}>42m</div>
          <div style={{ fontSize: '11px', color: 'var(--red)', fontWeight: 600, marginTop: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}>
            <span className="material-symbols-outlined" style={{ fontSize: '13px' }}>trending_down</span>-5%
          </div>
        </div>
        <div style={{ padding: '20px 24px' }}>
          <div style={{ fontSize: '12px', color: 'var(--tx2)', fontWeight: 500, marginBottom: '6px' }}>New Organizations</div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: 'var(--primary)', fontFamily: 'var(--fm)', letterSpacing: '-.5px' }}>24</div>
          <div style={{ fontSize: '11px', color: 'var(--primary)', fontWeight: 600, marginTop: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}>
            <span className="material-symbols-outlined" style={{ fontSize: '13px' }}>calendar_today</span>This Month
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '16px', marginBottom: '20px' }}>
        {/* Bar Chart */}
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '20px' }}>
          <div style={{ display: 'flex', justifycontent: 'space-between', alignitems: 'flex-start', marginBottom: '16px', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--tx1)' }}>User Growth Trend</div>
              <div style={{ fontSize: '12px', color: 'var(--tx2)', marginTop: '2px' }}>Last 6 months performance</div>
            </div>
            <select className="field-select" style={{ width: '110px', height: '30px', fontSize: '12px' }} value={chartPeriod} onChange={handlePeriodChange}>
              <option value="monthly">Monthly</option>
              <option value="weekly">Weekly</option>
            </select>
          </div>
          {/* Flex columns growth chart */}
          <div style={{ position: 'relative', height: '200px', display: 'flex', alignItems: 'flex-end', gap: '10px', padding: '0 8px' }}>
            {barChartData.map((d, i) => (
              <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignitems: 'center', gap: '4px', cursor: 'pointer', textAlign: 'center' }} onClick={() => showToast(`${d.label}: ${d.val} users`, 'info')}>
                <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--tx2)' }}>{d.val}</div>
                <div className="bar-col" style={{ width: '100%', height: `${Math.round((d.val / maxVal) * 150)}px`, background: 'var(--primary)', borderRadius: '5px 5px 0 0' }}></div>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: '10px', padding: '0 8px', marginTop: '6px' }}>
            {barChartData.map((d, i) => (
              <div key={i} style={{ flex: 1, textAlign: 'center', fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', letterSpacing: '.06em' }}>{d.label}</div>
            ))}
          </div>
        </div>

        {/* Donut Chart */}
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '20px' }}>
          <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--tx1)', marginBottom: '4px' }}>Org Distribution</div>
          <div style={{ fontSize: '12px', color: 'var(--tx2)', marginBottom: '16px' }}>Market segment breakdown</div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div style={{ position: 'relative', width: '140px', height: '140px', marginBottom: '16px' }}>
              <svg viewBox="0 0 140 140" style={{ transform: 'rotate(-90deg)' }}>
                {/* Background segment */}
                <circle cx="70" cy="70" r="50" fill="none" stroke="#E5E7EB" strokeWidth="22" />
                {/* Corporate 64% */}
                <circle cx="70" cy="70" r="50" fill="none" stroke="#4648D4" strokeWidth="22" strokeDasharray="201 314" strokeLinecap="round" />
                {/* Higher Ed 22% */}
                <circle cx="70" cy="70" r="50" fill="none" stroke="#A5B4FC" strokeWidth="22" strokeDasharray="69 314" strokeDashoffset="-201" />
                {/* Government 14% */}
                <circle cx="70" cy="70" r="50" fill="none" stroke="#E0E7FF" strokeWidth="22" strokeDasharray="44 314" strokeDashoffset="-270" />
              </svg>
              <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', textAlign: 'center' }}>
                <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--tx1)', fontFamily: 'var(--fm)' }}>{donutSegment.pct}</div>
                <div style={{ fontSize: '10px', color: 'var(--tx2)', fontWeight: 600, letterSpacing: '.05em' }}>{donutSegment.label}</div>
              </div>
            </div>
            <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div className="donut-legend-item" onClick={() => highlightSegment('corp', '64%')} style={{ cursor: 'pointer' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#4648D4', flexShrink: 0 }}></span>
                <span style={{ fontSize: '12px', color: 'var(--tx1)', flex: 1 }}>Corporate</span>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--tx2)', fontFamily: 'var(--fm)' }}>64%</span>
              </div>
              <div className="donut-legend-item" onClick={() => highlightSegment('ed', '22%')} style={{ cursor: 'pointer' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#A5B4FC', flexShrink: 0 }}></span>
                <span style={{ fontSize: '12px', color: 'var(--tx1)', flex: 1 }}>Higher Ed</span>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--tx2)', fontFamily: 'var(--fm)' }}>22%</span>
              </div>
              <div className="donut-legend-item" onClick={() => highlightSegment('gov', '14%')} style={{ cursor: 'pointer' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#C7D2FE', flexShrink: 0 }}></span>
                <span style={{ fontSize: '12px', color: 'var(--tx1)', flex: 1 }}>Government</span>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--tx2)', fontFamily: 'var(--fm)' }}>14%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Usage per Org Table */}
      <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'visible' }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--tx1)' }}>Usage per Organization</div>
          <div style={{ position: 'relative' }}>
            <button className="btn btn-secondary btn-sm" onClick={() => setFilterPopoverOpen(!filterPopoverOpen)}>
              <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>filter_list</span> Health Score
            </button>
            {filterPopoverOpen && (
              <div className="popover show" style={{ right: 0, top: '36px', minWidth: '200px', padding: '12px' }}>
                <div className="fp-body">
                  <div className="fp-field">
                    <label className="fp-label" style={{ fontSize: '10px', fontWeight: 700, color: 'var(--tx3)' }}>Health Score</label>
                    <select className="field-select" value={healthFilter} onChange={e => setHealthFilter(e.target.value)} style={{ height: '32px', fontSize: '12px' }}>
                      <option value="all">All</option>
                      <option value="Excellent">Excellent</option>
                      <option value="Stable">Stable</option>
                      <option value="Warning">Warning</option>
                    </select>
                  </div>
                </div>
                <div className="fp-footer" style={{ display: 'flex', gap: '6px', marginTop: '10px' }}>
                  <button className="btn btn-secondary btn-sm" style={{ flex: 1 }} onClick={() => { setHealthFilter("all"); setFilterPopoverOpen(false); }}>Clear</button>
                  <button className="btn btn-primary btn-sm" style={{ flex: 1 }} onClick={() => setFilterPopoverOpen(false)}>Apply</button>
                </div>
              </div>
            )}
          </div>
        </div>
        
        <div className="table-wrap">
          <table style={{ width: '100%' }}>
            <thead>
              <tr style={{ background: 'var(--page)' }}>
                <th style={{ padding: '9px 18px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Organization</th>
                <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Active Users</th>
                <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Storage Used</th>
                <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Health Score</th>
                <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrgs.map(o => {
                const pct = Math.round((o.storageUsed / o.storageTotal) * 100);
                const barColor = pct > 85 ? 'var(--red)' : pct > 60 ? 'var(--amber)' : 'var(--primary)';
                const hBadge = {
                  'Excellent': <span className="badge" style={{ background: '#ECFDF5', color: '#065F46' }}>Excellent</span>,
                  'Stable': <span className="badge" style={{ background: '#EFF6FF', color: '#1D4ED8' }}>Stable</span>,
                  'Warning': <span className="badge" style={{ background: '#FFFBEB', color: '#92400E' }}>Warning</span>,
                }[o.health];
                return (
                  <tr key={o.id} style={{ position: 'relative' }}>
                    <td style={{ padding: '12px 18px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ width: '34px', height: '34px', borderRadius: '8px', background: `${o.color}22`, color: o.color, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', fontWeight: 700, flexShrink: 0 }}>{o.id}</div>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--tx1)' }}>{o.name}</div>
                          <div style={{ fontSize: '11px', color: 'var(--tx2)' }}>{o.plan}</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '12px 14px', fontFamily: 'var(--fm)', fontSize: '13px' }}>{o.users.toLocaleString()}</td>
                    <td style={{ padding: '12px 14px' }}>
                      <div style={{ width: '120px', height: '4px', background: 'var(--border2)', borderRadius: '4px', overflow: 'hidden', marginBottom: '4px' }}>
                        <div style={{ width: `${pct}%`, height: '100%', background: barColor }}></div>
                      </div>
                      <div style={{ fontSize: '11px', color: pct > 85 ? 'var(--red)' : 'var(--tx2)' }}>{o.storageUsed}GB / {o.storageTotal >= 1000 ? `${o.storageTotal/1000}TB` : `${o.storageTotal}GB`}</div>
                    </td>
                    <td style={{ padding: '12px 14px' }}>{hBadge}</td>
                    <td style={{ padding: '12px 14px', position: 'relative' }}>
                      <button className="btn-icon btn" onClick={() => toggleRowMenu(o.id)}>
                        <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>more_vert</span>
                      </button>
                      {activeMenuId === o.id && (
                        <div className="popover show" style={{ position: 'absolute', right: '40px', bottom: '10px', minWidth: '160px', zIndex: 100 }}>
                          <div className="notif-item" style={{ padding: '8px 12px' }} onClick={() => { showToast(`Viewing details for ${o.name}`, 'info'); setActiveMenuId(null); }}>
                            <span className="material-symbols-outlined" style={{ fontSize: '16px', color: 'var(--primary)' }}>visibility</span>
                            <span style={{ fontSize: '13px' }}>View Details</span>
                          </div>
                          <div className="notif-item" style={{ padding: '8px 12px' }} onClick={() => { setActiveMenuId(null); handleExportCSV(o); }}>
                            <span className="material-symbols-outlined" style={{ fontSize: '16px', color: 'var(--tx2)' }}>download</span>
                            <span style={{ fontSize: '13px' }}>Export Report</span>
                          </div>
                          <div className="notif-item" style={{ padding: '8px 12px' }} onClick={() => { setActiveMenuId(null); setAlertOrg(o); }}>
                            <span className="material-symbols-outlined" style={{ fontSize: '16px', color: 'var(--amber)' }}>notifications_active</span>
                            <span style={{ fontSize: '13px' }}>Set Alert</span>
                          </div>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Set Alert Modal */}
      {alertOrg && createPortal(
        <div className="overlay" onClick={() => setAlertOrg(null)} style={{zIndex: 200}}>
          <div className="modal modal-sm" onClick={e => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <div className="modal-title">Set Alert</div>
                <div className="modal-sub">Threshold for {alertOrg.name}</div>
              </div>
              <button className="modal-close" onClick={() => setAlertOrg(null)}><span className="material-symbols-outlined">close</span></button>
            </div>
            <div className="modal-body">
              <div className="field-group">
                <label className="field-label">Alert Metric</label>
                <select className="field-select">
                  <option>Storage Usage</option>
                  <option>Active Users</option>
                  <option>Health Score Drop</option>
                </select>
              </div>
              <div className="field-group">
                <label className="field-label">Threshold Value</label>
                <input className="field-input" type="text" placeholder="e.g. > 80% capacity" />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setAlertOrg(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={() => { showToast(`Alert configured for ${alertOrg.name}`, 'success'); setAlertOrg(null); }}>Save Alert</button>
            </div>
          </div>
        </div>,
        document.body
      )}

    </div>
  );
}

// ═══════════════════════════════════════════════
// AUDIT LOGS
// ═══════════════════════════════════════════════
export function AuditLogsTab({ searchQuery }) {
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
  }, [orgFilter, severityFilter, searchTarget, searchQuery]);

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

      {/* Live Filters */}
      <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '14px 18px', marginBottom: '16px', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
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

      {/* Expandable Data Table */}
      <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden', marginBottom: '16px' }}>
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

      {/* Mission Control metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' }}>
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px', borderLeft: '4px solid var(--red)' }}>
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
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px', borderLeft: '4px solid var(--primary)' }}>
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
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px', borderLeft: '4px solid var(--green)' }}>
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

// ═══════════════════════════════════════════════
// FEATURE FLAGS MATRIX
// ═══════════════════════════════════════════════
export function FeatureFlagsTab() {
  const { showToast } = useToast();
  const [resyncing, setResyncing] = useState(false);
  
  const featureColumns = [
    { key: 'analytics', label: 'Analytics', icon: 'insights' },
    { key: 'ats', label: 'ATS Integration', icon: 'manage_history' },
    { key: 'cloud', label: 'Cloud Modules', icon: 'cloud' },
    { key: 'devops', label: 'Devops Courses', icon: 'terminal' },
    { key: 'moodle', label: 'Moodle Access', icon: 'school' },
    { key: 'pal', label: 'PAL Tracking', icon: 'track_changes' },
  ];

  const [featureFlags, setFeatureFlags] = useState({
    'Telite University': { analytics: true, ats: false, cloud: false, devops: false, moodle: true, pal: true },
    'Telite Systems': { analytics: true, ats: false, cloud: false, devops: false, moodle: true, pal: true },
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

      {/* Feature Matrix Table */}
      <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden', marginBottom: '20px' }}>
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

      {/* Legend */}
      <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '20px' }}>
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
              <div style={{ fontSize: '12px', color: 'var(--tx2)', lineHeight: '1.55' }}>Disables the module. Users will see a 'Coming Soon' placeholder or the entry point hidden.</div>
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

// ═══════════════════════════════════════════════
// SETTINGS
// ═══════════════════════════════════════════════
export function SettingsTab() {
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
        {/* General Settings */}
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'var(--primary-lt)', display: 'flex', alignItems: 'center', justifycontent: 'center', justifyContent: 'center' }}>
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

        {/* Security Settings */}
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: '#EFF6FF', display: 'flex', alignItems: 'center', justifycontent: 'center', justifyContent: 'center' }}>
              <span className="material-symbols-outlined" style={{ color: '#2563EB', fontSize: '18px' }}>security</span>
            </div>
            <div style={{ fontSize: '17px', fontWeight: 700, color: 'var(--tx1)' }}>Security</div>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {Object.entries(settingsState.security).map(([key, s]) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', justifycontent: 'space-between', padding: '14px', background: 'var(--page)', borderRadius: 'var(--r-lg)', justifyContent: 'space-between' }}>
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

      {/* Notifications settings */}
      <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'var(--amber-bg)', display: 'flex', alignItems: 'center', justifycontent: 'center', justifyContent: 'center' }}>
            <span className="material-symbols-outlined" style={{ color: 'var(--amber)', fontSize: '18px' }}>notifications</span>
          </div>
          <div style={{ fontSize: '17px', fontWeight: 700, color: 'var(--tx1)' }}>Notifications</div>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' }}>
          {Object.entries(settingsState.notifications).map(([key, n]) => (
            <div key={key} style={{ padding: '16px', background: 'var(--page)', borderRadius: 'var(--r-lg)', display: 'flex', alignItems: 'center', justifycontent: 'space-between', justifyContent: 'space-between' }}>
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

// ═══════════════════════════════════════════════
// MOODLE SYNC PAGE
// ═══════════════════════════════════════════════
export function MoodleSyncTab({ searchQuery }) {
  const { showToast } = useToast();
  
  const { 
    syncTenants, 
    currentSyncCat, 
    setCurrentSyncCat, 
    syncRow, 
    triggerGlobalSync, 
    isSyncing 
  } = useAdminStore();

  const [activeSyncTab, setActiveSyncTab] = useState("control");
  
  // Date, Cat, Status Filters for Sync Logs tab
  const [logDateFilter, setLogDateFilter] = useState("");
  const [logCatFilter, setLogCatFilter] = useState("");
  const [logStatusFilter, setLogStatusFilter] = useState("");
  const [logSearch, setLogSearch] = useState("");

  const syncLogsPerCat = {
    'CAT-001': [
      { time: '14:02:11', msg: 'Successfully synced 12 new course enrollments from Moodle.', type: 'success' },
      { time: '14:00:05', msg: 'Handshake initiated with /webservice/rest/server.php', type: 'info' },
      { time: '13:45:22', msg: 'Automatic backup of tenant mapping database completed.', type: 'info' },
      { time: '13:30:00', msg: 'Scheduled sync started (auto-trigger).', type: 'info' },
    ],
    'CAT-002': [
      { time: '13:58:45', msg: 'FAILED: Connection timeout after 30s — endpoint unreachable.', type: 'error' },
      { time: '13:55:00', msg: 'Retrying connection attempt (3 of 3)…', type: 'warn' },
      { time: '13:50:00', msg: 'Handshake initiated with /webservice/rest/server.php', type: 'info' },
    ],
    'CAT-005': [
      { time: 'Now', msg: 'Sync in progress — fetching course roster from Moodle…', type: 'warn' },
      { time: '14:01:00', msg: 'Handshake completed. Pulling data from 3 subcategories.', type: 'info' },
    ],
    'CAT-008': [
      { time: '09:15:00', msg: 'Successfully synced 8 course enrollments.', type: 'success' },
      { time: '09:13:00', msg: 'Handshake initiated with /webservice/rest/server.php', type: 'info' },
      { time: '09:10:00', msg: 'Scheduled sync started.', type: 'info' },
    ],
    'CAT-012': [
      { time: '—', msg: 'No sync has been performed yet. Click Start to initiate.', type: 'info' },
    ],
  };

  const healthPerCat = {
    'CAT-001': 98.2, 'CAT-002': 71.4, 'CAT-005': 94.8, 'CAT-008': 99.1, 'CAT-012': 0
  };

  const syncLogHistory = [
    { ts: '2026-05-26 14:02:11', catId: 'CAT-001', tenant: 'Main Campus', event: 'sync.complete', status: 'completed', duration: '1.2s' },
    { ts: '2026-05-26 14:00:05', catId: 'CAT-001', tenant: 'Main Campus', event: 'handshake.ok', status: 'completed', duration: '0.3s' },
    { ts: '2026-05-26 13:58:45', catId: 'CAT-002', tenant: 'Medical Annex', event: 'sync.fail', status: 'failed', duration: '30.0s' },
    { ts: '2026-05-26 13:55:00', catId: 'CAT-002', tenant: 'Medical Annex', event: 'sync.retry', status: 'failed', duration: '30.0s' },
    { ts: '2026-05-26 13:45:22', catId: 'CAT-001', tenant: 'Main Campus', event: 'backup.complete', status: 'completed', duration: '2.1s' },
    { ts: '2026-05-26 13:30:00', catId: 'CAT-001', tenant: 'Main Campus', event: 'sync.start', status: 'completed', duration: '0.1s' },
    { ts: '2026-05-25 09:15:00', catId: 'CAT-008', tenant: 'North Campus', event: 'sync.complete', status: 'completed', duration: '0.9s' },
    { ts: '2026-05-25 09:14:00', catId: 'CAT-008', tenant: 'North Campus', event: 'enroll.import', status: 'completed', duration: '0.4s' },
    { ts: '2026-05-24 16:20:00', catId: 'CAT-005', tenant: 'Corporate Hub', event: 'sync.start', status: 'in_progress', duration: '—' },
    { ts: '2026-05-23 11:00:00', catId: 'CAT-001', tenant: 'Main Campus', event: 'course.pull', status: 'completed', duration: '1.8s' },
  ];

  const handleRowSync = async (e, catId) => {
    e.stopPropagation();
    showToast(`Sync started for ${catId}…`, 'info');
    await syncRow(catId);
    showToast(`Sync complete for ${catId}`, 'success');
  };

  const handleGlobalSyncTrigger = async () => {
    showToast('Global sync triggered for all mapped tenants', 'info');
    await triggerGlobalSync();
    showToast('Global Moodle sync completed — 99.8% success', 'success');
  };

  const filteredLogs = useMemo(() => {
    let result = syncLogHistory;
    if (logCatFilter) result = result.filter(l => l.catId === logCatFilter);
    if (logStatusFilter) result = result.filter(l => l.status === logStatusFilter);
    const q = (logSearch || searchQuery || "").toLowerCase();
    if (q && q.length >= 2) {
      result = result.filter(l => l.tenant.toLowerCase().includes(q) || l.event.toLowerCase().includes(q));
    }
    return result;
  }, [logCatFilter, logStatusFilter, logSearch, searchQuery]);

  const handleExportSyncCSV = () => {
    const headers = ['Timestamp', 'Category ID', 'Tenant', 'Event', 'Status', 'Duration'];
    const rows = filteredLogs.map(l => [l.ts, l.catId, l.tenant, l.event, l.status, l.duration]);
    downloadCSV(rows, headers, 'moodle-sync-history.csv');
    showToast('Sync logs exported successfully', 'success');
  };

  return (
    <div className="page" style={{ display: 'block' }}>
      <div className="page-header">
        <div>
          <div className="page-title">Moodle Sync Control</div>
          <div className="page-sub">Manage API connections and synchronisation between Telite LMS and Moodle.</div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={handleExportSyncCSV}>
            <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>download</span> Export Report
          </button>
          <button className="btn btn-primary" onClick={handleGlobalSyncTrigger} disabled={isSyncing}>
            <span className="material-symbols-outlined" style={{ fontSize: '15px', animation: isSyncing ? 'spin 1.5s linear infinite' : 'none' }}>sync</span> 
            {isSyncing ? 'Syncing All…' : 'Sync All'}
          </button>
        </div>
      </div>

      {/* Gateway Status Bar */}
      <div id="gatewayBar" style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '14px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', gap: '16px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ position: 'relative', flexShrink: 0 }}>
            <div id="gatewayDot" style={{ width: '10px', height: '10px', borderRadius: '50%', background: isSyncing ? 'var(--amber)' : 'var(--green)', boxShadow: '0 0 0 0 rgba(5,150,105,.4)', animation: 'gatewayPulse 2s infinite' }}></div>
          </div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--tx1)' }}>Moodle LMS Gateway</div>
            <div style={{ fontSize: '12px', color: 'var(--tx2)', fontFamily: 'var(--fm)', marginTop: '1px' }}>https://moodle.telite-edu.com/api/v2</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
          <span className={`badge ${isSyncing ? 'badge-amber' : 'badge-green'}`} style={{ fontSize: '11px', padding: '4px 12px' }}>
            {isSyncing ? 'SYNCING…' : 'CONNECTED'}
          </span>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.1em' }}>Latency</div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--primary)', fontFamily: 'var(--fm)' }} id="gatewayLatency">24ms</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.1em' }}>Uptime</div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--green)', fontFamily: 'var(--fm)' }}>99.9%</div>
          </div>
        </div>
      </div>

      {/* Tab Navigations */}
      <div className="tabs" id="syncTabs">
        <div className={`tab ${activeSyncTab === 'control' ? 'active' : ''}`} onClick={() => setActiveSyncTab('control')}>Sync Control</div>
        <div className={`tab ${activeSyncTab === 'logs' ? 'active' : ''}`} onClick={() => setActiveSyncTab('logs')}>Sync Logs</div>
        <div className={`tab ${activeSyncTab === 'reports' ? 'active' : ''}`} onClick={() => setActiveSyncTab('reports')}>Reports</div>
      </div>

      {/* Sync Control tab panel */}
      {activeSyncTab === 'control' && (
        <div className="sync-tab-panel" style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '16px' }}>
          {/* Tenant Mapping Table */}
          <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--tx1)' }}>Tenant Mapping</div>
            </div>
            <table style={{ width: '100%' }}>
              <thead>
                <tr style={{ background: 'var(--page)' }}>
                  <th style={{ padding: '9px 16px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Moodle Category</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>LMS Tenant</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Status</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Last Sync</th>
                  <th style={{ padding: '9px 14px', textAlign: 'right', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {syncTenants.map(t => {
                  const isSelected = currentSyncCat === t.catId;
                  const isRowSyncing = t.status === 'syncing';
                  const rowLeftBorder = {
                    successful: '3px solid transparent',
                    failed: '3px solid var(--red)',
                    syncing: '3px solid var(--amber)',
                    pending: '3px solid var(--border)'
                  }[t.status];
                  const statusColors = {
                    successful: 'var(--green)',
                    failed: 'var(--red)',
                    syncing: 'var(--amber)',
                    pending: 'var(--tx3)'
                  }[t.status];
                  const rowBg = t.status === 'failed' ? '#FEF9F9' : '';
                  return (
                    <tr 
                      key={t.catId}
                      onClick={() => setCurrentSyncCat(t.catId)}
                      style={{ 
                        cursor: 'pointer', 
                        borderLeft: isSelected ? '3px solid var(--primary)' : rowLeftBorder,
                        background: isSelected ? 'var(--primary-lt)' : rowBg 
                      }}
                      className={isSelected ? 'sync-selected' : ''}
                    >
                      <td style={{ padding: '11px 16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <div style={{ width: '28px', height: '28px', borderRadius: '6px', background: 'var(--primary-lt)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <span className="material-symbols-outlined" style={{ color: 'var(--primary)', fontSize: '15px' }}>folder_open</span>
                          </div>
                          <div>
                            <span style={{ fontWeight: 600, fontSize: '13px' }}>{t.catId}</span>
                            <div style={{ fontSize: '11px', color: 'var(--tx2)', marginTop: '2px' }}>{t.catName}</div>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '11px 14px', fontSize: '13px', fontWeight: 500 }}>{t.tenant}</td>
                      <td style={{ padding: '11px 14px' }}>
                        <span className="status-dot" style={{ textTransform: 'uppercase', color: statusColors }}>
                          <span className="material-symbols-outlined" style={{ fontSize: '14px', marginRight: '4px', animation: isRowSyncing ? 'spin 1.5s linear infinite' : 'none' }}>
                            {isRowSyncing ? 'sync' : t.status === 'successful' ? 'done_all' : t.status === 'failed' ? 'error_outline' : 'schedule'}
                          </span>
                          {t.status.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ padding: '11px 14px', fontFamily: 'var(--fm)', fontSize: '12px', color: 'var(--tx2)' }}>{t.lastSync}</td>
                      <td style={{ padding: '11px 14px', textAlign: 'right' }}>
                        <button 
                          className="btn btn-secondary btn-sm" 
                          disabled={isRowSyncing}
                          onClick={(e) => handleRowSync(e, t.catId)}
                        >
                          {t.status === 'failed' ? 'Retry' : t.status === 'pending' ? 'Start' : 'Refresh'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Timeline Logs Sidebar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--tx1)' }}>Sync Logs</div>
                <span className="badge badge-indigo" style={{ fontSize: '10px' }}>{currentSyncCat}</span>
              </div>
              <div className="sync-timeline">
                {(syncLogsPerCat[currentSyncCat] || []).map((log, index) => {
                  const dotColor = {
                    success: 'var(--primary)',
                    error: 'var(--red)',
                    warn: 'var(--amber)',
                    info: 'var(--border)'
                  }[log.type] || 'var(--border)';
                  return (
                    <div key={index} className="sync-tl-item">
                      <div className="sync-tl-dot" style={{ background: dotColor }}></div>
                      <div className="sync-tl-time">{log.time}</div>
                      <div className="sync-tl-msg">{log.msg}</div>
                    </div>
                  );
                })}
              </div>
              <button 
                style={{ width: '100%', marginTop: '14px', padding: '7px', border: '1px solid var(--primary-lt)', borderRadius: 'var(--r)', background: 'none', color: 'var(--primary)', fontSize: '12px', fontWeight: '600', cursor: 'pointer' }}
                onClick={() => showToast('Full log view — coming soon', 'info')}
              >
                View Detailed Log
              </button>
            </div>
            <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '16px' }}>
              <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.12em', marginBottom: '8px' }}>Health Metric</div>
              <div style={{ fontSize: '32px', fontWeight: '700', color: 'var(--primary)', fontFamily: 'var(--fm)', lineHeight: 1 }}>
                <span>{healthPerCat[currentSyncCat]}</span>
                <span style={{ fontSize: '16px' }}>%</span>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--tx2)', margin: '8px 0 10px', lineHeight: '1.5' }}>Average sync success rate across category tunnel over 30 days.</div>
              <div style={{ height: '5px', background: 'var(--border2)', borderRadius: '5px', overflow: 'hidden' }}>
                <div style={{ height: '100%', background: 'var(--primary)', borderRadius: '5px', width: `${healthPerCat[currentSyncCat]}%` }}></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sync Logs tab panel */}
      {activeSyncTab === 'logs' && (
        <div className="sync-tab-panel" style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', marginBottom: '16px' }}>
          <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border2)', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
            <div>
              <label className="field-label" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--tx3)' }}>Date Range</label>
              <select className="field-select" style={{ height: '32px', fontSize: '12px' }} value={logDateFilter} onChange={e => setLogDateFilter(e.target.value)}>
                <option value="">Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
              </select>
            </div>
            <div>
              <label className="field-label" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--tx3)' }}>Category</label>
              <select className="field-select" style={{ height: '32px', fontSize: '12px' }} value={logCatFilter} onChange={e => setLogCatFilter(e.target.value)}>
                <option value="">All Categories</option>
                <option value="CAT-001">CAT-001</option>
                <option value="CAT-002">CAT-002</option>
                <option value="CAT-005">CAT-005</option>
                <option value="CAT-008">CAT-008</option>
              </select>
            </div>
            <div>
              <label className="field-label" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--tx3)' }}>Status</label>
              <select className="field-select" style={{ height: '32px', fontSize: '12px' }} value={logStatusFilter} onChange={e => setLogStatusFilter(e.target.value)}>
                <option value="">All</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="in_progress">In Progress</option>
              </select>
            </div>
            <div>
              <label className="field-label" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--tx3)' }}>Search</label>
              <input className="field-input" style={{ height: '32px', fontSize: '12px' }} value={logSearch} onChange={e => setLogSearch(e.target.value)} placeholder="Tenant or event…" />
            </div>
          </div>
          
          <div className="table-wrap">
            <table style={{ width: '100%' }}>
              <thead>
                <tr style={{ background: 'var(--page)' }}>
                  <th style={{ padding: '9px 16px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Timestamp</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Category</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Tenant</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Event</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Status</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Duration</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((l, idx) => (
                  <tr key={idx} style={{ borderTop: '1px solid var(--border2)' }}>
                    <td style={{ padding: '11px 16px', fontFamily: 'var(--fm)', fontSize: '12px' }}>{l.ts}</td>
                    <td style={{ padding: '11px 14px', fontSize: '13px', fontWeight: 600 }}>{l.catId}</td>
                    <td style={{ padding: '11px 14px', fontSize: '13px' }}>{l.tenant}</td>
                    <td style={{ padding: '11px 14px', fontFamily: 'var(--fm)', fontSize: '12px' }}>{l.event}</td>
                    <td style={{ padding: '11px 14px' }}>
                      <span className={`badge ${l.status === 'completed' ? 'badge-green' : l.status === 'failed' ? 'badge-red' : 'badge-amber'}`}>{l.status.toUpperCase()}</span>
                    </td>
                    <td style={{ padding: '11px 14px', fontFamily: 'var(--fm)', fontSize: '12px' }}>{l.duration}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ padding: '10px 16px', borderTop: '1px solid var(--border2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', color: 'var(--tx2)' }}>Showing {filteredLogs.length} events</span>
            <button className="btn btn-secondary btn-sm" onClick={handleExportSyncCSV}>
              <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>download</span> Export CSV
            </button>
          </div>
        </div>
      )}

      {/* Reports tab panel */}
      {activeSyncTab === 'reports' && (
        <div className="sync-tab-panel">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px', marginBottom: '20px' }}>
            <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px' }}>
              <div style={{ fontSize: '12px', color: 'var(--tx2)', fontWeight: 500, marginBottom: '6px' }}>Total Syncs (30 days)</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px' }}>
                <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--primary)', fontFamily: 'var(--fm)' }}>284</div>
                <span className="badge badge-indigo" style={{ fontSize: '10px' }}>+12%</span>
              </div>
            </div>
            <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px' }}>
              <div style={{ fontSize: '12px', color: 'var(--tx2)', fontWeight: 500, marginBottom: '6px' }}>Avg Sync Time</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px' }}>
                <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--tx1)', fontFamily: 'var(--fm)' }}>1.4s</div>
                <span className="badge badge-gray" style={{ fontSize: '10px' }}>Stable</span>
              </div>
            </div>
            <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px' }}>
              <div style={{ fontSize: '12px', color: 'var(--tx2)', fontWeight: 500, marginBottom: '6px' }}>Failed Syncs</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px' }}>
                <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--tx1)', fontFamily: 'var(--fm)' }}>6</div>
                <span className="badge badge-green" style={{ fontSize: '10px' }}>-3% ↓</span>
              </div>
            </div>
          </div>

          {/* Bar Success percentage Chart */}
          <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '20px', marginBottom: '16px' }}>
            <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--tx1)', marginBottom: '4px' }}>Sync Success Rate — Last 14 Days</div>
            <div style={{ fontSize: '12px', color: 'var(--tx2)', marginBottom: '20px' }}>Daily sync completion percentage</div>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-end', gap: '6px', height: '120px', padding: '0 4px' }}>
              {[98, 97, 99, 100, 94, 98, 99, 100, 97, 96, 99, 100, 98, 99].map((val, idx) => (
                <div key={idx} style={{ flex: 1, height: `${val}%`, background: 'var(--primary)', borderRadius: '3px 3px 0 0', position: 'relative', cursor: 'pointer' }} title={`Day ${idx+1}: ${val}% success`}></div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: '6px', padding: '0 4px', marginTop: '6px', justifyContent: 'space-between', fontSize: '10px', color: 'var(--tx3)' }}>
              <span>May 13</span>
              <span>May 20</span>
              <span>Today</span>
            </div>
          </div>

          {/* Category Health Table */}
          <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border2)', fontSize: '14px', fontWeight: '700', color: 'var(--tx1)' }}>Category Health Summary</div>
            <table style={{ width: '100%' }}>
              <thead>
                <tr style={{ background: 'var(--page)' }}>
                  <th style={{ padding: '9px 16px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Category</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Tenant</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Success Rate</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Total Syncs</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Avg Duration</th>
                  <th style={{ padding: '9px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Trend</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderTop: '1px solid var(--border2)' }}>
                  <td style={{ padding: '11px 16px' }}>
                    <div style={{ fontSize: '13px', fontWeight: '600' }}>CAT-001</div>
                    <div style={{ fontSize: '11px', color: 'var(--tx2)' }}>Computer Science</div>
                  </td>
                  <td style={{ padding: '11px 14px', fontSize: '13px', color: 'var(--tx2)' }}>Main Campus</td>
                  <td style={{ padding: '11px 14px' }}><span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--green)', fontFamily: 'var(--fm)' }}>98.2%</span></td>
                  <td style={{ padding: '11px 14px', fontFamily: 'var(--fm)', fontSize: '13px' }}>142</td>
                  <td style={{ padding: '11px 14px', fontFamily: 'var(--fm)', fontSize: '13px', color: 'var(--tx2)' }}>1.2s</td>
                  <td style={{ padding: '11px 14px', color: 'var(--green)', fontSize: '13px', fontWeight: 'bold' }}>↑ +1.2%</td>
                </tr>
                <tr style={{ borderTop: '1px solid var(--border2)' }}>
                  <td style={{ padding: '11px 16px' }}>
                    <div style={{ fontSize: '13px', fontWeight: '600' }}>CAT-002</div>
                    <div style={{ fontSize: '11px', color: 'var(--tx2)' }}>Health Sciences</div>
                  </td>
                  <td style={{ padding: '11px 14px', fontSize: '13px', color: 'var(--tx2)' }}>Medical Annex</td>
                  <td style={{ padding: '11px 14px' }}><span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--red)', fontFamily: 'var(--fm)' }}>71.4%</span></td>
                  <td style={{ padding: '11px 14px', fontFamily: 'var(--fm)', fontSize: '13px' }}>88</td>
                  <td style={{ padding: '11px 14px', fontFamily: 'var(--fm)', fontSize: '13px', color: 'var(--tx2)' }}>2.4s</td>
                  <td style={{ padding: '11px 14px', color: 'var(--red)', fontSize: '13px', fontWeight: 'bold' }}>↓ -4.5%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════
// HELP & SUPPORT
// ═══════════════════════════════════════════════
export function HelpTab({ onOpenOrgModal, onOpenInviteModal, onNavigate }) {
  const { showToast } = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  
  const [guides, setGuides] = useState([
    { title: "Organization Creation & Onboarding", open: true, content: ["Navigate to the Organizations panel and select \"New Organization\".", "Define the organizational domain, type (College / Company), and metadata.", "Assign the primary Administrator and send an invite email.", "Configure feature flags per organization tier in the Feature Flags Matrix.", "Verify Moodle sync mapping in Sync Control > Tenant Mapping."] },
    { title: "Moodle Sync Resolution Workflows", open: false, content: ["FAILED status → check endpoint URL in gateway settings → click Retry.", "PENDING status → verify Moodle API token has not expired.", "Timeout errors → increase request timeout in Settings > General.", "If CAT mapping is missing, re-map from Sync Control > Tenant Mapping."] },
    { title: "Audit Log Export for Compliance", open: false, content: ["Navigate to Audit Logs from the System Section.", "Set Date Range, Organization, and Severity filters as needed.", "Use the Search Target field to isolate specific actor IDs or IP addresses.", "Click \"Export CSV\" to download the filtered results."] },
  ]);

  const shortcuts = [
    { action: "Quick Search", shortcut: "⌘ K", scope: "Global" },
    { action: "New Organization", shortcut: "⌥ N", scope: "Organizations" },
    { action: "Send Invitation", shortcut: "⌥ I", scope: "Admin Control" },
    { action: "Export Audit Log", shortcut: "⇧ E", scope: "Audit Logs" },
    { action: "Toggle Sidebar", shortcut: "⌘ \\", scope: "Global" },
    { action: "Trigger Moodle Sync", shortcut: "⌘ ⇧ S", scope: "Moodle Sync" },
    { action: "Save Settings", shortcut: "⌘ S", scope: "Settings" },
  ];

  const bentoCards = [
    { title: "Organizations", sub: "Multi-tenant Management", icon: "corporate_fare", page: "organizations", bg: "var(--primary-lt)", color: "var(--primary)" },
    { title: "Admin Control", sub: "Permissions & Roles", icon: "admin_panel_settings", page: "admins", bg: "#EFF6FF", color: "#2563EB" },
    { title: "Moodle Sync", sub: "Integration Hub", icon: "sync", page: "moodle-sync", bg: "#FFFBEB", color: "var(--amber)" },
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

      {/* Hero Search Box */}
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

      {/* Quick Access Bento Grid */}
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

      {/* Two-Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '16px' }}>
        {/* Left Column: Knowledge Base */}
        <div>
          {/* Guides accordion */}
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

          {/* Shortcuts Table */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <span className="material-symbols-outlined" style={{ color: 'var(--primary)' }}>keyboard</span>
            <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--tx1)' }}>Global Keyboard Shortcuts</span>
          </div>
          <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden' }}>
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

        {/* Right Column: Contact + Status + Quick Links */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Contact Support */}
          <div id="helpContactCard" style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px' }}>
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

          {/* System Status pulsing monitors */}
          <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px' }}>
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
                <span>Moodle API Bridge</span>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 0 0 rgba(5,150,105,.4)', animation: 'gatewayPulse 2.3s infinite' }}></div>
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

          {/* Quick links card */}
          <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px' }}>
            <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--tx3)', textTransform: 'uppercase', letterSpacing: '.12em', marginBottom: '10px' }}>Admin Quick Links</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div onClick={() => onNavigate("dashboard")} className="help-ql-row">Overview Dashboard <span className="material-symbols-outlined help-ql-arrow">arrow_forward</span></div>
              <div onClick={() => { onNavigate("organizations"); onOpenOrgModal(); }} className="help-ql-row">New Org Wizard <span className="material-symbols-outlined help-ql-arrow">arrow_forward</span></div>
              <div onClick={() => onNavigate("moodle-sync")} className="help-ql-row">Global Sync Status <span className="material-symbols-outlined help-ql-arrow">arrow_forward</span></div>
            </div>
          </div>
        </div>
      </div>

      {/* Changelog Footer Strip */}
      <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '14px 20px', display: 'flex', alignItems: 'center', gap: '16px', marginTop: '20px', flexWrap: 'wrap' }}>
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
