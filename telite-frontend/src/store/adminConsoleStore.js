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

  // Notifications
  notifications: SEED_NOTIFICATIONS,
  markAllRead: () => set((state) => ({
    notifications: state.notifications.map(n => ({ ...n, read: true }))
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

  // UI
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
}));
