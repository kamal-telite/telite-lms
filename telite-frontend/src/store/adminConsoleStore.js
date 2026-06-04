import { create } from 'zustand';
import { platformApi } from '../services/platform';

const SEED_NOTIFICATIONS = [
  { id: 1, type: 'user', title: 'New User Registered', sub: 'John Doe joined Telite University', time: '2m ago', read: false },
  { id: 2, type: 'sync', title: 'Moodle Sync Started', sub: 'Auto-sync for Oxford Academy', time: '15m ago', read: false },
  { id: 3, type: 'security', title: 'Security Alert', sub: 'Failed login on Admin Console', time: '45m ago', read: false },
  { id: 4, type: 'org', title: 'Organization Created', sub: 'Telite Systems onboarded successfully', time: '2h ago', read: true },
];

export const useAdminStore = create((set, get) => ({
  // Search
  searchQuery: '',
  setSearchQuery: (q) => set({ searchQuery: q }),

  // Organizations
  organizations: [],
  loadOrganizations: async () => {
    try {
      const res = await platformApi.listOrganizations({ limit: 100 });
      set({ organizations: res.data.orgs });
    } catch (err) {
      console.error("Failed to load organizations:", err);
    }
  },
  updateOrgStatus: async (id, status) => {
    await platformApi.updateOrgStatus(id, status);
    // Optimistic update
    set((state) => ({
      organizations: state.organizations.map((org) =>
        org.id === id ? { ...org, status } : org
      ),
    }));
  },

  // Admins
  admins: [],
  pendingInvitations: [],
  loadAdmins: async () => {
    try {
      const res = await platformApi.listAdmins();
      set({ admins: res.data.admins, pendingInvitations: res.data.pending_invitations });
    } catch (err) {
      console.error("Failed to load admins:", err);
    }
  },
  updateAdminStatus: async (id, status) => {
    await platformApi.updateAdminStatus(id, status);
    // Optimistic update
    set((state) => ({
      admins: state.admins.map((admin) =>
        admin.id === id ? { ...admin, status } : admin
      ),
    }));
  },
  deleteAdmin: async (id) => {
    await platformApi.deleteAdmin(id);
    set((state) => ({
      admins: state.admins.filter((admin) => admin.id !== id),
    }));
  },
  resendInvitation: async (invitationId) => {
    const res = await platformApi.resendAdminInvitation(invitationId);
    const updatedInvitation = res.data.invitation;
    set((state) => ({
      pendingInvitations: state.pendingInvitations.map((invite) =>
        invite.id === invitationId ? { ...invite, ...updatedInvitation } : invite
      ),
    }));
    return updatedInvitation;
  },
  revokeInvitation: async (invitationId) => {
    await platformApi.revokeAdminInvitation(invitationId);
    set((state) => ({
      pendingInvitations: state.pendingInvitations.filter((invite) => invite.id !== invitationId),
    }));
  },

  // Notifications
  notifications: SEED_NOTIFICATIONS,
  markAllRead: () => set((state) => ({
    notifications: state.notifications.map(n => ({ ...n, read: true }))
  })),
  addNotification: (notif) => set((state) => ({
    notifications: [notif, ...state.notifications]
  })),

  // Sync
  isSyncing: false,
  lastSync: 'Today, 04:30 AM',
  syncProgress: 75,
  triggerSync: async () => {
    set({ isSyncing: true, syncProgress: 0 });
    // simulate progress
    setTimeout(() => set({ syncProgress: 100 }), 50);
    await new Promise(r => setTimeout(r, 3000));
    set({ isSyncing: false, lastSync: 'Just now' });
  },

  // Moodle Sync Control Page States
  syncTenants: [
    { catId: 'CAT-001', catName: 'Computer Science', tenant: 'Main Campus', status: 'successful', lastSync: '2023-11-24 14:02:11' },
    { catId: 'CAT-002', catName: 'Health Sciences', tenant: 'Medical Annex', status: 'failed', lastSync: '2023-11-24 13:58:45' },
    { catId: 'CAT-005', catName: 'Business Admin', tenant: 'Corporate Hub', status: 'syncing', lastSync: 'Ongoing' },
    { catId: 'CAT-008', catName: 'Engineering', tenant: 'North Campus', status: 'successful', lastSync: '2023-11-23 09:15:00' },
    { catId: 'CAT-012', catName: 'Arts & Design', tenant: 'Creative Studio', status: 'pending', lastSync: 'Never' },
  ],
  currentSyncCat: 'CAT-001',
  setCurrentSyncCat: (catId) => set({ currentSyncCat: catId }),
  
  syncRow: async (catId) => {
    // 1. Set row status to 'syncing'
    set((state) => ({
      syncTenants: state.syncTenants.map(t => t.catId === catId ? { ...t, status: 'syncing', lastSync: 'Ongoing' } : t)
    }));

    // 2. Simulate sync duration
    await new Promise(r => setTimeout(r, 1800));

    // 3. Set row status to 'successful'
    let targetTenant = null;
    set((state) => {
      const updated = state.syncTenants.map(t => {
        if (t.catId === catId) {
          targetTenant = t;
          return { ...t, status: 'successful', lastSync: 'Just now' };
        }
        return t;
      });
      return { syncTenants: updated };
    });

    // 4. Add unread notification to bell
    if (targetTenant) {
      const newNotif = {
        id: Date.now(),
        type: 'sync',
        title: `Sync Complete — ${catId}`,
        sub: `${targetTenant.catName} (${targetTenant.tenant}) synced successfully.`,
        time: 'Just now',
        read: false
      };
      get().addNotification(newNotif);
    }
  },

  triggerGlobalSync: async () => {
    set({ isSyncing: true });
    
    // Cycle all non-syncing rows sequentially with 600ms stagger
    const tenants = get().syncTenants;
    for (let i = 0; i < tenants.length; i++) {
      const tenant = tenants[i];
      if (tenant.status !== 'syncing') {
        get().syncRow(tenant.catId);
        await new Promise(r => setTimeout(r, 600));
      }
    }
    
    set({ isSyncing: false });
  },

  // Settings Page States
  settingsState: {
    platformName: "Telite LMS",
    supportEmail: "support@telite.io",
    timezone: "IST",
    language: "en",
    security: {
      twoFactor: true,
      sessionTimeout: true,
      loginLockout: true,
    },
    notifications: {
      emailAlerts: true,
      securityAlerts: true,
      syncReports: false,
    }
  },
  
  updateSetting: (section, key, value) => set((state) => ({
    settingsState: {
      ...state.settingsState,
      [section]: {
        ...state.settingsState[section],
        [key]: value
      }
    }
  })),

  updateGeneralSetting: (key, value) => set((state) => ({
    settingsState: {
      ...state.settingsState,
      [key]: value
    }
  })),

  // UI
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
}));
