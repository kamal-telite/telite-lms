import axios from "axios";
import { clearSession, getSession, mergeAuthPayload, persistSession } from "../context/session";

// Use relative URLs so Vite proxy handles the routing
const API_BASE_URL = "";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const session = getSession();
  if (session?.accessToken) {
    config.headers.Authorization = `Bearer ${session.accessToken}`;
  }
  // Distributed tracing — attach a unique trace ID per request
  config.headers["X-Request-ID"] =
    config.headers["X-Request-ID"] || Math.random().toString(36).slice(2, 14);
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {};
    const session = getSession();
    const shouldRefresh =
      error.response?.status === 401 &&
      !original._retry &&
      !String(original.url || "").includes("/auth/login") &&
      !String(original.url || "").includes("/auth/refresh") &&
      session?.refreshToken;

    if (shouldRefresh) {
      original._retry = true;
      try {
        const refreshResponse = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: session.refreshToken,
        });
        const mergedSession = mergeAuthPayload(session, refreshResponse.data);
        persistSession(mergedSession);
        original.headers = original.headers || {};
        original.headers.Authorization = `Bearer ${mergedSession.accessToken}`;
        return api(original);
      } catch {
        clearSession();
        if (window.location.pathname !== "/login") {
          window.location.assign("/login");
        }
      }
    }

    return Promise.reject(error);
  }
);

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

export async function loginRequest(username, password) {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);
  const response = await api.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return response.data;
}

export async function logoutRequest(refreshToken) {
  return unwrap(await api.post("/auth/logout", { refresh_token: refreshToken }));
}

export async function fetchMe() {
  return unwrap(await api.get("/auth/me"));
}

export async function fetchHealth() {
  return unwrap(await api.get("/health"));
}

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
  return unwrap(await api.post("/enrol/requests/approve-batch", { request_ids: requestIds }));
}

export async function fetchTasks(categorySlug) {
  return unwrap(await api.get("/tasks", { params: categorySlug ? { category_slug: categorySlug } : {} }));
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

export async function fetchPalUser(userId) {
  return unwrap(await api.get(`/pal/users/${userId}`));
}

export async function fetchPalLeaderboard(slug) {
  return unwrap(await api.get(`/pal/leaderboard/${slug}`));
}

export async function fetchPalDistribution(slug) {
  return unwrap(await api.get(`/pal/distribution/${slug}`));
}

export async function fetchNotifications() {
  return unwrap(await api.get("/notifications"));
}

export async function fetchSettings() {
  return unwrap(await api.get("/settings/system"));
}

// ── Signup & Verification API ───────────────────────────────────────────────

export async function fetchOrganizations(type) {
  return unwrap(await api.get("/signup/organizations", { params: type ? { type } : {} }));
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
  return unwrap(await api.post(`/admin/verifications/${id}/reject`, { reason }));
}

export async function bulkUploadVerifications(file) {
  const formData = new FormData();
  formData.append("file", file);
  return unwrap(await api.post("/admin/verifications/bulk-upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  }));
}

export async function fetchVerificationStats() {
  return unwrap(await api.get("/admin/verifications/stats"));
}
