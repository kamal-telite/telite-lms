import React, { useEffect, useState, useMemo, useRef } from "react";
import { Routes, Route, useLocation, useNavigate } from "react-router-dom";
import { useToast } from "../../components/common/ui";
import { platformApi } from "../../services/platform";
import { downloadCSV } from "../../utils/csvExport";
import { useAdminStore } from "../../store/adminConsoleStore";
import { useKeyboardShortcuts } from "../../hooks/useKeyboardShortcuts";
import AdminSidebar from "../../components/platform-admin/AdminSidebar";
import AdminSearch from "../../components/platform-admin/AdminSearch";
import AdminTopbar from "../../components/platform-admin/AdminTopbar";
import AdminFab from "../../components/platform-admin/AdminFab";
import ConfirmDialog from "../../components/platform-admin/ConfirmDialog";
import OverviewTab from "../../components/platform-admin/OverviewTab";
import OrganizationsTab from "../../components/platform-admin/OrganizationsTab";
import AdminControlTab from "../../components/platform-admin/AdminControlTab";
import AnalyticsTab from "../../components/platform-admin/AnalyticsTab";
import AuditLogsTab from "../../components/platform-admin/AuditLogsTab";
import FeatureFlagsTab from "../../components/platform-admin/FeatureFlagsTab";
import SettingsTab from "../../components/platform-admin/SettingsTab";
import HelpTab from "../../components/platform-admin/HelpTab";
import CreateOrganizationModal from "../../components/platform-admin/CreateOrganizationModal";
import InviteAdminModal from "../../components/platform-admin/InviteAdminModal";
import ViewOrganizationModal from "../../components/platform-admin/ViewOrganizationModal";
import "../../styles/platform-admin.css";

export default function PlatformAdminPage({ session, onLogout }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const searchRef = useRef(null);

  const {
    sidebarCollapsed, toggleSidebar,
    searchQuery, setSearchQuery,
    notifications, markAllRead,
    organizations: storeOrganizations, loadOrganizations,
    admins: storeAdmins, loadAdmins,
    syncTenants: storeSyncTenants, triggerGlobalSync, settingsState
  } = useAdminStore();
  const organizations = useMemo(() => Array.isArray(storeOrganizations) ? storeOrganizations : [], [storeOrganizations]);
  const admins = useMemo(() => Array.isArray(storeAdmins) ? storeAdmins : [], [storeAdmins]);
  const syncTenants = useMemo(() => Array.isArray(storeSyncTenants) ? storeSyncTenants : [], [storeSyncTenants]);

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

  const handleExportAudit = () => {
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
  };

  useKeyboardShortcuts({
    searchRef,
    toggleSidebar,
    triggerGlobalSync,
    pathname,
    settingsState,
    showToast,
    onCreateOrg: () => setCreateOrgOpen(true),
    onInviteAdmin: () => setInviteAdminOpen(true),
    onExportAudit: handleExportAudit
  });
  
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

  const searchComponent = (
    <AdminSearch 
      query={searchQuery} 
      onQueryChange={setSearchQuery} 
      results={searchResults} 
    />
  );

  return (
    <div className="platform-admin-root">
      <AdminSidebar 
        collapsed={sidebarCollapsed} 
        onToggle={toggleSidebar} 
        onLogout={onLogout} 
      />

      <div id="main-wrap">
        <AdminTopbar 
          searchComponent={searchComponent}
          notifOpen={notifOpen}
          setNotifOpen={setNotifOpen}
          appsOpen={appsOpen}
          setAppsOpen={setAppsOpen}
          notifications={notifications}
          unreadCount={unreadCount}
          markAllRead={markAllRead}
        />

        <Routes>
          <Route index element={<OverviewTab searchQuery={searchQuery} />} />
          <Route path="organizations" element={<OrganizationsTab searchQuery={searchQuery} showConfirm={showConfirm} onOpenCreateOrg={() => setCreateOrgOpen(true)} onViewOrg={(org) => setViewOrgData(org)} />} />
          <Route path="admins" element={<AdminControlTab searchQuery={searchQuery} showConfirm={showConfirm} onOpenInvite={() => setInviteAdminOpen(true)} />} />
          <Route path="analytics" element={<AnalyticsTab searchQuery={searchQuery} />} />
          <Route path="audit" element={<AuditLogsTab searchQuery={searchQuery} />} />
          <Route path="features" element={<FeatureFlagsTab />} />
          <Route path="settings" element={<SettingsTab />} />
          
          <Route path="help" element={<HelpTab onOpenOrgModal={() => setCreateOrgOpen(true)} onOpenInviteModal={() => setInviteAdminOpen(true)} onNavigate={(page) => navigate(`/platform-admin/${page}`)} />} />
          <Route path="*" element={<div className="page" style={{display:'block'}}><div style={{textAlign:'center', marginTop:'100px', color:'var(--tx3)'}}>This module is currently being updated. Please check back later.</div></div>} />
        </Routes>
      </div>
      
      <AdminFab 
        open={fabOpen}
        onToggle={setFabOpen}
        onCreateOrg={() => { setCreateOrgOpen(true); navigate('/platform-admin/organizations'); }}
        onInviteAdmin={() => { setInviteAdminOpen(true); navigate('/platform-admin/admins'); }}
      />

      <CreateOrganizationModal open={createOrgOpen} onClose={() => setCreateOrgOpen(false)} />
      <InviteAdminModal
        open={inviteAdminOpen}
        onClose={() => setInviteAdminOpen(false)}
        onInvited={loadAdmins}
      />
      <ViewOrganizationModal org={viewOrgData} onClose={() => setViewOrgData(null)} />

      <ConfirmDialog
        open={!!confirmDialog}
        title={confirmDialog?.title}
        description={confirmDialog?.description}
        confirmLabel={confirmDialog?.confirmLabel}
        variant={confirmDialog?.variant}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />

      <div id="toast-wrap"></div>
    </div>
  );
}

