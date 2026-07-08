/**
 * Axios API client for Telite LMS.
 *
 * PHASE 2 SECURITY HARDENING:
 * - withCredentials: true — sends HttpOnly cookies on every request
 * - CSRF token read from telite_csrf_token cookie, sent as X-CSRF-Token header
 * - No JWT tokens read from or written to localStorage
 * - Token refresh uses the HttpOnly refresh cookie (no body token needed)
 * - Emits telite:auth-expired on 401 after failed refresh so the router owns navigation
 */

import axios from "axios";
import {
  buildSessionFromAuth,
  clearClientSessionState,
  getCsrfToken,
  getSession,
  mergeAuthPayload,
  persistSession,
} from "../context/session";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // send HttpOnly cookies on every request
});

// ── Request interceptor ───────────────────────────────────────────────────────

api.interceptors.request.use((config) => {
  // Attach CSRF token for all mutating methods
  const method = (config.method || "get").toLowerCase();
  if (!["get", "head", "options"].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) {
      config.headers["X-CSRF-Token"] = csrf;
    }
  }

  // Distributed tracing
  config.headers["X-Request-ID"] =
    config.headers["X-Request-ID"] || Math.random().toString(36).slice(2, 14);

  return config;
});

// ── Response interceptor — auto-refresh on 401 ───────────────────────────────

let _refreshing = false;
let _refreshQueue = [];

function _processQueue(error) {
  _refreshQueue.forEach((cb) => (error ? cb.reject(error) : cb.resolve()));
  _refreshQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {};
    const isAuthEndpoint =
      String(original.url || "").includes("/auth/login") ||
      String(original.url || "").includes("/auth/refresh");

    if (error.response?.status === 401 && !original._retry && !isAuthEndpoint) {
      if (_refreshing) {
        // Queue this request until the refresh completes
        return new Promise((resolve, reject) => {
          _refreshQueue.push({ resolve, reject });
        }).then(() => api(original));
      }

      original._retry = true;
      _refreshing = true;

      try {
        // Refresh using the HttpOnly refresh cookie — no body token needed
        const refreshResp = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        );

        // Update sessionStorage user profile
        const session = getSession();
        const merged = mergeAuthPayload(session || {}, refreshResp.data);
        persistSession(merged);

        _processQueue(null);
        return api(original);
      } catch (refreshError) {
        _processQueue(refreshError);
        clearClientSessionState();
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("telite:auth-expired"));
        }
        return Promise.reject(refreshError);
      } finally {
        _refreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ── Utilities ─────────────────────────────────────────────────────────────────

function unwrap(response) {
  return response.data;
}

export function getErrorMessage(error, fallback = "Something went wrong.") {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    fallback
  );
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function loginRequest(username, password) {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);
  // Backend sets HttpOnly cookies in the response — we only read the body for user profile
  const response = await api.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return response.data;
}

export async function logoutRequest() {
  // Backend clears HttpOnly cookies; we clear sessionStorage
  return unwrap(await api.post("/auth/logout", {}));
}

export async function fetchMe() {
  return unwrap(await api.get("/auth/me"));
}

export async function updateThemePreference(themePreference) {
  return unwrap(
    await api.patch("/auth/preferences/theme", {
      theme_preference: themePreference,
    })
  );
}

export async function forgotPassword(email) {
  return unwrap(await api.post("/auth/forgot-password", { email }));
}

export async function resetPassword(token, password) {
  return unwrap(await api.post("/auth/reset-password", { token, password }));
}

export async function fetchActiveSessions() {
  return unwrap(await api.get("/auth/sessions/"));
}

export async function revokeSession(sessionId) {
  return unwrap(await api.delete(`/auth/sessions/${sessionId}`));
}

export async function revokeAllSessions() {
  return unwrap(await api.delete("/auth/sessions/"));
}

export async function switchOrgContext(targetOrgId) {
  const response = await api.post("/auth/sessions/switch-org", {
    target_org_id: targetOrgId,
  });
  const session = mergeAuthPayload(getSession() || {}, response.data);
  persistSession(session);
  return response.data;
}

export async function switchAccountRequest(targetUserId) {
  const response = await api.post("/auth/sessions/switch-account", {
    target_user_id: targetUserId,
  });
  const session = buildSessionFromAuth(response.data);
  persistSession(session);
  return response.data;
}

export async function addAccountRequest(username, password) {
  const response = await api.post("/auth/sessions/add-account", {
    username,
    password,
  });
  const session = buildSessionFromAuth(response.data);
  persistSession(session);
  return response.data;
}

export async function fetchHealth() {
  return unwrap(await api.get("/health"));
}

export async function fetchBranding(tenantSlug) {
  return unwrap(await api.get(`/api/public/branding/${tenantSlug}`));
}

export async function updateOrganizationBranding(orgId, payload) {
  return unwrap(await api.patch(`/api/admin/organizations/${orgId}/branding`, payload));
}

export async function fetchDraftBranding(orgId) {
  return unwrap(await api.get(`/api/admin/organizations/${orgId}/branding/draft`));
}

export async function saveDraftBranding(orgId, payload) {
  return unwrap(await api.post(`/api/admin/organizations/${orgId}/branding/draft`, payload));
}

export async function publishBranding(orgId) {
  return unwrap(await api.post(`/api/admin/organizations/${orgId}/branding/publish`));
}

export async function rollbackBranding(orgId, versionId) {
  return unwrap(await api.post(`/api/admin/organizations/${orgId}/branding/rollback/${versionId}`));
}

export async function fetchBrandingHistory(orgId) {
  return unwrap(await api.get(`/api/admin/organizations/${orgId}/branding/history`));
}

export async function uploadOrganizationAsset(orgId, assetType, file) {
  const formData = new FormData();
  formData.append("file", file);
  return unwrap(
    await api.post(`/api/admin/organizations/${orgId}/branding/upload/${assetType}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export async function fetchSuperAdminDashboard() {
  return unwrap(await api.get("/dashboard/super-admin"));
}

export async function fetchAdminDashboard(slug) {
  return unwrap(await api.get(`/dashboard/categories/${slug}/admin`));
}

export async function fetchStatsDashboard(slug) {
  return unwrap(await api.get(`/dashboard/categories/${slug}/stats`));
}

export async function fetchCategoryGradingAnalytics(slug) {
  return unwrap(await api.get(`/dashboard/categories/${slug}/grading-analytics`));
}

export async function fetchLearnerDashboard() {
  return unwrap(await api.get("/dashboard/learner"));
}

export async function fetchAssignmentVerifications(slug, params = {}) {
  return unwrap(await api.get(`/api/v1/admin/categories/${slug}/assignment-verifications`, { params }));
}

export async function approveAssignmentSubmission(submissionId, feedback = "") {
  return unwrap(await api.post(`/api/v1/admin/submissions/${submissionId}/approve`, { feedback }));
}

export async function rejectAssignmentSubmission(submissionId, feedback = "") {
  return unwrap(await api.post(`/api/v1/admin/submissions/${submissionId}/reject`, { feedback }));
}

function filenameFromContentDisposition(disposition) {
  if (!disposition) return null;
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1].replace(/"/g, ""));
  const asciiMatch = disposition.match(/filename="?([^";]+)"?/i);
  return asciiMatch?.[1] || null;
}

export async function downloadAssignmentSubmissionFile(submissionId, assetId = null) {
  const params = assetId ? { asset_id: assetId } : {};
  const response = await api.get(`/api/v1/submissions/${submissionId}/download`, {
    params,
    responseType: "blob",
  });
  return {
    blob: response.data,
    filename: filenameFromContentDisposition(response.headers["content-disposition"]) || `assignment-submission-${submissionId}`,
  };
}

export async function startLearningSession(payload) {
  return unwrap(await api.post("/api/v1/learner/learning-sessions/start", payload));
}

export async function heartbeatLearningSession(payload) {
  return unwrap(await api.post("/api/v1/learner/learning-sessions/heartbeat", payload));
}

export async function endLearningSession(payload) {
  return unwrap(await api.post("/api/v1/learner/learning-sessions/end", payload));
}

export async function fetchQuizStats(blockId) {
  return unwrap(await api.get(`/api/v1/learner/blocks/${blockId}/quiz/stats`));
}

export async function fetchCategoryQuizStatistics(slug) {
  return unwrap(await api.get(`/api/v1/learner/admin/categories/${slug}/quiz-statistics`));
}

// ── Categories ────────────────────────────────────────────────────────────────

export async function fetchCategories() {
  return unwrap(await api.get("/categories"));
}

export async function createCategory(payload) {
  return unwrap(await api.post("/categories", payload));
}

export async function updateCategory(categoryId, payload) {
  return unwrap(await api.patch(`/categories/${categoryId}`, payload));
}

export async function deleteCategory(categoryId) {
  return unwrap(await api.delete(`/categories/${categoryId}`));
}

// ── Admins ────────────────────────────────────────────────────────────────────

export async function fetchAdmins() {
  return unwrap(await api.get("/admins"));
}

export async function createAdmin(payload) {
  return unwrap(await api.post("/admins", payload));
}

export async function inviteAdmin(payload) {
  return unwrap(await api.post("/admins/invite", payload));
}

export async function updateAdmin(userId, payload) {
  return unwrap(await api.patch(`/admins/${userId}`, payload));
}

export async function deleteAdmin(userId) {
  return unwrap(await api.delete(`/admins/${userId}`));
}

// ── Users ─────────────────────────────────────────────────────────────────────

export async function fetchUsers(params = {}) {
  return unwrap(await api.get("/users", { params }));
}

export async function fetchUser(userId) {
  return unwrap(await api.get(`/users/${userId}`));
}

export async function fetchUserActivity(userId) {
  return unwrap(await api.get(`/users/${userId}/activity`));
}

export async function deleteUser(userId) {
  return unwrap(await api.delete(`/users/${userId}`));
}

// ── Courses ───────────────────────────────────────────────────────────────────

export async function fetchCategoryCourses(slug) {
  return unwrap(await api.get(`/categories/${slug}/courses`));
}

export async function createCourse(slug, payload) {
  return unwrap(await api.post(`/categories/${slug}/courses`, payload));
}

export async function updateCourse(slug, courseId, payload) {
  return unwrap(await api.patch(`/categories/${slug}/courses/${courseId}`, payload));
}

export async function deleteCourse(slug, courseId) {
  return unwrap(await api.delete(`/categories/${slug}/courses/${courseId}`));
}

export async function launchCourse(courseId) {
  return unwrap(await api.get(`/courses/${courseId}/launch`));
}

// ── Enrollments ───────────────────────────────────────────────────────────────

export async function fetchEnrollmentRequests(params = {}) {
  return unwrap(await api.get("/enrol/requests", { params }));
}

export async function manualEnroll(payload) {
  return unwrap(await api.post("/api/v1/enrol/manual", payload));
}

export async function selfEnroll(payload) {
  return unwrap(await api.post("/enrol/self", payload));
}

export async function approveEnrollmentRequest(requestId) {
  return unwrap(await api.post(`/enrol/requests/${requestId}/approve`));
}

export async function rejectEnrollmentRequest(requestId, reason = "") {
  return unwrap(await api.post(`/enrol/requests/${requestId}/reject`, { reason }));
}

export async function approveBatchEnrollments(requestIds) {
  return unwrap(
    await api.post("/enrol/requests/approve-batch", { request_ids: requestIds })
  );
}

// ── Tasks ─────────────────────────────────────────────────────────────────────

export async function fetchTasks(categorySlug) {
  return unwrap(
    await api.get("/tasks", {
      params: categorySlug ? { category_slug: categorySlug } : {},
    })
  );
}

export async function createTask(payload) {
  return unwrap(await api.post("/tasks", payload));
}

export async function updateTask(taskId, payload) {
  return unwrap(await api.patch(`/tasks/${taskId}`, payload));
}

export async function deleteTask(taskId) {
  return unwrap(await api.delete(`/tasks/${taskId}`));
}

export async function submitTask(taskId) {
  return unwrap(await api.post(`/tasks/${taskId}/submit`));
}

export async function startTask(taskId) {
  return unwrap(await api.post(`/tasks/${taskId}/start`));
}

export async function submitTaskWork(taskId, payload) {
  return unwrap(await api.post(`/tasks/${taskId}/submit-work`, payload));
}

export async function reviewTask(taskId, payload) {
  return unwrap(await api.post(`/tasks/${taskId}/review`, payload));
}

// ── PAL ───────────────────────────────────────────────────────────────────────

export async function fetchPalUser(userId) {
  return unwrap(await api.get(`/pal/users/${userId}`));
}

export async function fetchPalLeaderboard(slug) {
  return unwrap(await api.get(`/pal/leaderboard/${slug}`));
}

export async function fetchPalDistribution(slug) {
  return unwrap(await api.get(`/pal/distribution/${slug}`));
}

// ── Notifications & Settings ──────────────────────────────────────────────────

export async function fetchNotifications(params = {}) {
  return unwrap(await api.get("/api/v1/notifications", { params }));
}

export async function fetchUnreadNotificationCount() {
  return unwrap(await api.get("/api/v1/notifications/unread-count"));
}

export async function markNotificationRead(id) {
  return unwrap(await api.patch(`/api/v1/notifications/${id}/read`));
}

export async function markAllNotificationsRead() {
  return unwrap(await api.post("/api/v1/notifications/read-all"));
}

export async function fetchMyAnnouncements() {
  return unwrap(await api.get("/api/v1/announcements/my"));
}

export async function markAnnouncementRead(id) {
  return unwrap(await api.patch(`/api/v1/announcements/${id}/read`));
}

export async function fetchAnnouncements() {
  return unwrap(await api.get("/api/v1/announcements"));
}

export async function createAnnouncement(payload) {
  return unwrap(await api.post("/api/v1/announcements", payload));
}

export async function updateAnnouncement(id, payload) {
  return unwrap(await api.patch(`/api/v1/announcements/${id}`, payload));
}

export async function deleteAnnouncement(id) {
  return unwrap(await api.delete(`/api/v1/announcements/${id}`));
}

export async function fetchSettings() {
  return unwrap(await api.get("/settings/system"));
}

export async function addAllowedDomain(payload) {
  return unwrap(await api.post("/settings/domains", payload));
}

export async function removeAllowedDomain(domain) {
  return unwrap(await api.delete(`/settings/domains/${encodeURIComponent(domain)}`));
}

// ── Signup & Verification ─────────────────────────────────────────────────────

export async function fetchOrganizations(type) {
  return unwrap(
    await api.get("/signup/organizations", { params: type ? { type } : {} })
  );
}

export async function fetchSignupRoles(domainType) {
  return unwrap(await api.get(`/signup/roles/${domainType}`));
}

export async function submitSignupRequest(payload) {
  return unwrap(await api.post("/signup/register", payload));
}

export async function fetchVerifications(params = {}) {
  try {
    return unwrap(await api.get("/admin/verifications", { params }));
  } catch (error) {
    if (error?.response?.status === 404) {
      return { verifications: [] };
    }
    throw error;
  }
}

export async function fetchVerificationDetail(id) {
  return unwrap(await api.get(`/admin/verifications/${id}`));
}

export async function approveVerification(id) {
  return unwrap(await api.post(`/admin/verifications/${id}/approve`));
}

export async function rejectVerification(id, reason = "") {
  return unwrap(
    await api.post(`/admin/verifications/${id}/reject`, { reason })
  );
}

export async function bulkUploadVerifications(file) {
  const formData = new FormData();
  formData.append("file", file);
  return unwrap(
    await api.post("/admin/verifications/bulk-upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
  );
}

export async function fetchVerificationStats() {
  return unwrap(await api.get("/admin/verifications/stats"));
}

export async function previewBulkEnrollments(file) {
  const formData = new FormData();
  formData.append('file', file);
  return unwrap(
    await api.post('/api/v1/enrol/bulk/preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  );
}

export async function executeBulkEnrollments(rows) {
  return unwrap(
    await api.post('/api/v1/enrol/bulk/execute', { rows })
  );
}

// --- Question Banks ---

export async function getQuestionBanks(slug) {
  return unwrap(
    await api.get("/api/v1/question-banks", {
      params: slug ? { category_slug: slug } : {},
    })
  );
}

export async function createQuestionBank(slug, name) {
  return unwrap(
    await api.post(
      "/api/v1/question-banks",
      { name },
      { params: slug ? { category_slug: slug } : {} }
    )
  );
}

export async function getQuestions(bankId) {
  const data = unwrap(await api.get(`/api/v1/question-banks/${bankId}/questions`));
  return Array.isArray(data) ? data : data.items || [];
}

export async function createQuestion(bankId, payload) {
  return unwrap(await api.post(`/api/v1/question-banks/${bankId}/questions`, payload));
}

export async function updateDraftQuestion(bankId, questionId, payload) {
  return unwrap(
    await api.put(`/api/v1/question-banks/${bankId}/questions/${questionId}/draft`, payload)
  );
}

export async function publishQuestion(bankId, questionId) {
  return unwrap(await api.post(`/api/v1/question-banks/${bankId}/questions/${questionId}/publish`));
}

export async function createNewDraft(bankId, questionId) {
  return unwrap(await api.post(`/api/v1/question-banks/${bankId}/questions/${questionId}/drafts`));
}

export async function archiveDraftQuestion(bankId, questionId) {
  return unwrap(await api.delete(`/api/v1/question-banks/${bankId}/questions/${questionId}/draft`));
}

export async function getQuestionVersions(bankId, questionId) {
  return unwrap(await api.get(`/api/v1/question-banks/${bankId}/questions/${questionId}/versions`));
}

export async function checkStaleQuestions(items) {
  return unwrap(await api.post("/api/v1/question-banks/check-stale", { items }));
}
