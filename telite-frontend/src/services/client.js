/**
 * Axios API client for Telite LMS.
 *
 * PHASE 2 SECURITY HARDENING:
 * - withCredentials: true — sends HttpOnly cookies on every request
 * - CSRF token read from telite_csrf_token cookie, sent as X-CSRF-Token header
 * - No JWT tokens read from or written to localStorage
 * - Token refresh uses the HttpOnly refresh cookie (no body token needed)
 * - Automatic redirect to /login on 401 after failed refresh
 */

import axios from "axios";
import {
  buildSessionFromAuth,
  clearSession,
  getCsrfToken,
  getSession,
  mergeAuthPayload,
  persistSession,
} from "../context/session";

const API_BASE_URL = "";

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
        clearSession();
        if (typeof window !== "undefined" && window.location.pathname !== "/login") {
          window.location.assign("/login");
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

export async function fetchLearnerDashboard() {
  return unwrap(await api.get("/dashboard/learner"));
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
  return unwrap(await api.post("/enrol/manual", payload));
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

export async function fetchNotifications() {
  return unwrap(await api.get("/notifications"));
}

export async function fetchSettings() {
  return unwrap(await api.get("/settings/system"));
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
  return unwrap(await api.get("/admin/verifications", { params }));
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
