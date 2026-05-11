import { create } from 'zustand';
import { fetchLearnerDashboard } from '../services/client';

export const useLearnerStore = create((set, get) => ({
  data: null,
  loading: true,
  error: null,
  
  // UI States
  sidebarCollapsed: false,
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  
  // Data Fetching
  fetchData: async () => {
    set({ loading: true, error: null });
    try {
      const payload = await fetchLearnerDashboard();
      set({ data: payload, loading: false });
    } catch (err) {
      set({ error: err.message, loading: false });
    }
  },

  // Actions
  updateTaskStatus: (taskId, status) => set((state) => {
    if (!state.data?.tasks) return state;
    return {
      data: {
        ...state.data,
        tasks: state.data.tasks.map(t => t.id === taskId ? { ...t, status } : t)
      }
    };
  }),
}));
