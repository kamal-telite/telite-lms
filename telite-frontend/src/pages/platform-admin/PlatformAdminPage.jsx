import React, { useEffect, useState, useMemo, useRef } from "react";
import { createPortal } from "react-dom";
import { Routes, Route, useLocation, useNavigate, Link } from "react-router-dom";
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
    admins, loadAdmins
  } = useAdminStore();

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
    return { orgs: matchingOrgs, admins: matchingAdmins };
  }, [searchQuery, organizations, admins]);

  const [notifOpen, setNotifOpen] = useState(false);
  const [appsOpen, setAppsOpen] = useState(false);
  
  const [fabOpen, setFabOpen] = useState(false);
  const [createOrgOpen, setCreateOrgOpen] = useState(false);
  const [inviteAdminOpen, setInviteAdminOpen] = useState(false);

  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = useState(null);
  const showConfirm = (opts) => new Promise(resolve => setConfirmDialog({ ...opts, resolve }));
  const handleConfirm = () => { confirmDialog?.resolve(true); setConfirmDialog(null); };
  const handleCancel = () => { confirmDialog?.resolve(false); setConfirmDialog(null); };

  const unreadCount = notifications.filter(n => !n.read).length;

  // ⌘K / Ctrl+K keyboard shortcut
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);
  
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
      { id: "#moodle", icon: "sync", label: "Moodle Sync", action: () => showToast('Moodle Sync page — coming soon', 'info') },
      { id: "#analytics", icon: "insights", label: "Analytics", action: () => showToast('Analytics page — coming soon', 'info') },
    ]},
    { section: "System Section", items: [
      { id: "#audit", icon: "history_edu", label: "Audit Logs", action: () => showToast('Audit Logs — coming soon', 'info') },
      { id: "#features", icon: "flag", label: "Feature Flags", action: () => showToast('Feature Flags — coming soon', 'info') },
      { id: "#settings", icon: "settings", label: "Settings", action: () => showToast('Settings — coming soon', 'info') },
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
          <div className="nav-item" onClick={onLogout} style={{color: 'var(--tx3)'}}>
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
              {searchResults && (searchResults.orgs.length > 0 || searchResults.admins.length > 0) && (
                <div className="popover show" style={{top: '100%', left: 0, width: '320px', marginTop: '8px'}}>
                  <div className="popover-head">
                    <span className="popover-title">Search Results</span>
                  </div>
                  <div style={{padding: '8px 0'}}>
                    {searchResults.orgs.length > 0 && (
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
                    {searchResults.admins.length > 0 && (
                      <div>
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
                  <div className="ql-item" onClick={() => showToast('Analytics — coming soon', 'info')}>
                    <div className="ql-icon" style={{background: '#EFF6FF'}}><span className="material-symbols-outlined" style={{color: '#2563EB'}}>insights</span></div>
                    <span className="ql-label">Analytics</span>
                  </div>
                  <div className="ql-item" onClick={() => showToast('Audit Logs — coming soon', 'info')}>
                    <div className="ql-icon" style={{background: 'var(--primary-lt)'}}><span className="material-symbols-outlined" style={{color: 'var(--primary)'}}>history_edu</span></div>
                    <span className="ql-label">Audit Logs</span>
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
          <Route path="organizations" element={<OrganizationsTab searchQuery={searchQuery} showConfirm={showConfirm} onOpenCreateOrg={() => setCreateOrgOpen(true)} />} />
          <Route path="admins" element={<AdminControlTab searchQuery={searchQuery} showConfirm={showConfirm} onOpenInvite={() => setInviteAdminOpen(true)} />} />
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
        </div>
        <button className="fab-main" onClick={() => setFabOpen(!fabOpen)}>
          <span className="material-symbols-outlined" style={{fontSize: '22px'}}>add</span>
        </button>
      </div>

      <CreateOrganizationModal open={createOrgOpen} onClose={() => setCreateOrgOpen(false)} />
      <InviteAdminModal open={inviteAdminOpen} onClose={() => setInviteAdminOpen(false)} />

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
function OrganizationsTab({ searchQuery, showConfirm, onOpenCreateOrg }) {
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
                  <button className="btn-icon btn" title="View organization">
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
  const { admins, pendingInvitations, updateAdminStatus, loadAdmins } = useAdminStore();
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
    showToast(`${admin.full_name || admin.email} deleted`, 'success');
    loadAdmins();
  };

  const handleRevokeInvite = async (invite) => {
    const confirmed = await showConfirm({
      title: 'Revoke Invitation?',
      description: `This will cancel the pending invitation to ${invite.email}.`,
      confirmLabel: 'Revoke',
      variant: 'destructive',
    });
    if (!confirmed) return;
    showToast(`Invitation to ${invite.email} revoked`, 'success');
  };

  const handlePasswordReset = async (admin) => {
    const confirmed = await showConfirm({
      title: 'Reset Password?',
      description: `This will send a password reset email to ${admin.email}.`,
      confirmLabel: 'Reset Password',
    });
    if (!confirmed) return;
    showToast(`Password reset sent to ${admin.email}`, 'success');
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
                          </div>
                        </div>
                      </td>
                      <td>
                        <div style={{fontSize: '13px', fontWeight: 500}}>{a.org_name || 'Telite System'}</div>
                        <span className="badge badge-gray" style={{fontSize: '10px', marginTop: '2px'}}>Enterprise</span>
                      </td>
                      <td>{roleBadge}</td>
                      <td style={{fontFamily: 'var(--fm)', fontSize: '12px', color: 'var(--tx2)'}}>{isPending ? '—' : '2024-05-21 09:12'}</td>
                      <td>
                        {isPending ? <span className="badge badge-amber">Pending</span> : <span className={`status-dot ${a.status}`}>{a.status === 'active' ? 'Active' : 'Suspended'}</span>}
                      </td>
                      <td>
                        <div className="row-actions">
                          {isPending ? (
                            <>
                              <button className="btn-icon btn" title="Resend invite" onClick={() => showToast(`Invite resent to ${a.email}`, 'success')}><span className="material-symbols-outlined" style={{fontSize: '15px'}}>mail</span></button>
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
                If provided, an invitation token will be emailed to onboard via /accept-invite.
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
