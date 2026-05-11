import { create } from 'zustand';
import { 
  fetchAdminDashboard, 
  fetchVerifications, 
  fetchSuperAdminDashboard, 
  fetchUsers, 
  fetchSettings, 
  fetchOrganizations 
} from '../services/client';

export const useDashboardStore = create((set) => ({
  dashboard: null,
  verifications: [],
  learners: [],
  dashboardLoading: true,
  dashboardError: null,
  verifLoading: true,
  verifError: null,

  fetchDashboardData: async (slug) => {
    set({ dashboardLoading: true, dashboardError: null });
    try {
      const data = await fetchAdminDashboard(slug);
      set({
        dashboard: data,
        learners: data.learners || [],
        dashboardLoading: false,
      });
    } catch (err) {
      set({ dashboardError: err.message, dashboardLoading: false });
    }
  },

  fetchVerificationsData: async (slug) => {
    set({ verifLoading: true, verifError: null });
    try {
      const data = await fetchVerifications(slug);
      set({
        verifications: data.verifications || [],
        verifLoading: false,
      });
    } catch (err) {
      set({ verifError: err.message, verifLoading: false });
    }
  },
  
  updateTaskState: (taskId, newStatus) => set((state) => {
    if (!state.dashboard) return state;
    const updatedTasks = (state.dashboard.tasks || []).map(t => 
      t.id === taskId ? { ...t, status: newStatus } : t
    );
    return {
      dashboard: {
        ...state.dashboard,
        tasks: updatedTasks
      }
    };
  }),

  removeTaskState: (taskId) => set((state) => {
    if (!state.dashboard) return state;
    const updatedTasks = (state.dashboard.tasks || []).filter(t => t.id !== taskId);
    return {
      dashboard: {
        ...state.dashboard,
        tasks: updatedTasks
      }
    };
  })
}));

export const useSuperAdminStore = create((set) => ({
  dashboard: null,
  users: [],
  settings: null,
  verifications: [],
  organizations: [],
  loading: true,
  error: null,

  fetchData: async () => {
    set({ loading: true, error: null });
    try {
      const [dashboardPayload, userPayload, settingsPayload, verifPayload, orgPayload] = await Promise.all([
        fetchSuperAdminDashboard(),
        fetchUsers({ page: 1, page_size: 100, source: "moodle" }),
        fetchSettings(),
        fetchVerifications({ status: "pending" }),
        fetchOrganizations(),
      ]);
      set({
        dashboard: dashboardPayload,
        users: userPayload.users || [],
        settings: settingsPayload,
        verifications: verifPayload.verifications || [],
        organizations: orgPayload || [],
        loading: false
      });
    } catch (err) {
      set({ error: err.message, loading: false });
    }
  },

  updateTaskState: (taskId, newStatus) => set((state) => {
    if (!state.dashboard) return state;
    const updatedTasks = (state.dashboard.tasks || []).map(t => 
      t.id === taskId ? { ...t, status: newStatus } : t
    );
    return {
      dashboard: {
        ...state.dashboard,
        tasks: updatedTasks
      }
    };
  })
}));
