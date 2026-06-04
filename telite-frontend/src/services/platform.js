import { api } from "./client";

export const platformApi = {
  // Organizations
  listOrganizations: (params) => api.get("/api/platform/organizations", { params }),
  getOrganization: (orgId) => api.get(`/api/platform/organizations/${orgId}`),
  createOrganization: (payload) => api.post("/api/platform/organizations", payload),
  updateOrganization: (orgId, payload) => api.patch(`/api/platform/organizations/${orgId}`, payload),
  updateOrgStatus: (orgId, status) => api.patch(`/api/platform/organizations/${orgId}/status`, { status }),

  // Admins
  listAdmins: () => api.get("/api/platform/admins"),
  inviteAdmin: (payload) => api.post("/api/platform/admins/invite", payload),
  resendAdminInvitation: (invitationId) => api.post(`/api/platform/admins/invitations/${invitationId}/resend`),
  revokeAdminInvitation: (invitationId) => api.delete(`/api/platform/admins/invitations/${invitationId}`),
  updateAdminStatus: (userId, status) => api.patch(`/api/platform/admins/${userId}/status`, { status }),
  deleteAdmin: (userId) => api.delete(`/api/platform/admins/${userId}`),
  resetAdminPassword: (userId) => api.post(`/api/platform/admins/${userId}/reset-password`),

  // Analytics
  getAnalyticsOverview: () => api.get("/api/platform/analytics/overview"),
  getOrgAnalytics: (orgId) => api.get(`/api/platform/analytics/org/${orgId}`),

  // Moodle
  listMoodleTenants: () => api.get("/api/platform/moodle/tenants"),
  listMoodleSyncLogs: (params) => api.get("/api/platform/moodle/logs", { params }),
  getMoodleSyncReportSummary: (params) => api.get("/api/platform/moodle/reports/summary", { params }),
  syncOrgMoodle: (orgId) => api.post(`/api/platform/moodle/sync/${orgId}`),
  syncAllMoodle: () => api.post("/api/platform/moodle/sync-all"),

  // Feature Flags
  listFeatureFlags: () => api.get("/api/platform/features"),
  toggleFeatureFlag: (orgId, featureKey, isEnabled) =>
    api.patch(`/api/platform/features/${orgId}`, { feature_key: featureKey, is_enabled: isEnabled }),

  // Audit
  listAuditLogs: (params) => api.get("/api/platform/audit", { params }),

  // Invitations
  validateInvitation: (token) => api.get(`/api/invitations/${token}/validate`),
  acceptInvitation: (payload) => api.post("/api/platform/invitations/accept", payload),
};
