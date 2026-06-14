import { create } from 'zustand';
import { getSession } from '../context/session';
import { 
  fetchAdminDashboard, 
  fetchVerifications, 
  fetchSuperAdminDashboard, 
  fetchUsers, 
  fetchSettings, 
  fetchOrganizations 
} from '../services/client';

const emptySuperAdminDashboard = {
  kpis: {
    total_categories: 0,
    total_courses: 0,
    total_learners: 0,
    pending_approvals: 0,
    pending_verifications: 0,
    active_this_week: 0,
    total_completions: 0,
  },
  categories: [],
  admins: [],
  learners: { total: 0, rows: [] },
  leaderboard: [],
  audit_log: [],
  tasks: [],
  pal_performance: [],
  enrollments: [],
  enrollment_audit: { rows: [], visible_pending_ids: [] },
  analytics: {
    courses_per_category: [],
    avg_pal_per_category: [],
    user_status_distribution: [],
    learners_per_category: [],
  },
  notes: {},
};

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function normalizeSuperAdminDashboard(payload = {}, usersPayload = []) {
  const users = asArray(usersPayload);
  const categories = asArray(payload.categories);
  const learners = users.filter((user) => user.role === "learner");
  const admins = users.filter((user) => ["super_admin", "category_admin", "instructor"].includes(user.role));
  const enrollmentRows = asArray(payload.enrollment_audit?.rows || payload.enrollments);
  const visiblePendingIds = asArray(payload.enrollment_audit?.visible_pending_ids).length
    ? payload.enrollment_audit.visible_pending_ids
    : enrollmentRows.filter((row) => String(row.status || "").toLowerCase() === "pending").map((row) => row.request_id || row.id).filter(Boolean);

  return {
    ...emptySuperAdminDashboard,
    ...payload,
    kpis: {
      ...emptySuperAdminDashboard.kpis,
      ...(payload.kpis || {}),
    },
    categories,
    admins: asArray(payload.admins).length ? payload.admins : admins,
    learners: {
      total: payload.learners?.total ?? learners.length,
      rows: asArray(payload.learners?.rows).length ? payload.learners.rows : learners,
    },
    leaderboard: asArray(payload.leaderboard),
    audit_log: asArray(payload.audit_log),
    tasks: asArray(payload.tasks),
    pal_performance: asArray(payload.pal_performance).length ? payload.pal_performance : learners,
    enrollments: asArray(payload.enrollments),
    enrollment_audit: {
      ...(payload.enrollment_audit || {}),
      rows: enrollmentRows,
      visible_pending_ids: visiblePendingIds,
    },
    analytics: {
      ...emptySuperAdminDashboard.analytics,
      ...(payload.analytics || {}),
      courses_per_category: asArray(payload.analytics?.courses_per_category),
      avg_pal_per_category: asArray(payload.analytics?.avg_pal_per_category),
      user_status_distribution: asArray(payload.analytics?.user_status_distribution),
      learners_per_category: asArray(payload.analytics?.learners_per_category),
    },
    notes: payload.notes || {},
  };
}

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
      const session = getSession();
      const user = session?.user;

      let isolatedOrgs = orgPayload || [];
      if (user && !user.is_platform_admin && user.org_id) {
        isolatedOrgs = isolatedOrgs.filter(org => org.id === user.org_id);
      }

      const users = asArray(userPayload?.users);
      set({
        dashboard: normalizeSuperAdminDashboard(dashboardPayload, users),
        users,
        settings: settingsPayload || {},
        verifications: asArray(verifPayload?.verifications),
        organizations: isolatedOrgs,
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
