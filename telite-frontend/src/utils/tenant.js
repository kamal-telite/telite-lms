/**
 * Resolves the tenant organization slug based on a tiered validation lookup:
 * 1. Query parameter `?tenant=slug` or `?org=slug`
 * 2. URL Path prefix `/categories/:slug/admin` or `/categories/:slug/...`
 * 3. Subdomain of hostname (excluding platform domain and localhost)
 * 4. Active user session profile `category_scope`
 *
 * @param {Object} sessionUser - The logged-in user profile from session storage.
 * @returns {string|null} The resolved tenant slug, or null if platform-wide/unknown.
 */
export function getTenantSlugFromUrl(sessionUser) {
  if (typeof window === "undefined") {
    return null;
  }

  // 1. Query parameters
  const urlParams = new URLSearchParams(window.location.search);
  const queryTenant = urlParams.get("tenant") || urlParams.get("org");
  if (queryTenant) {
    return queryTenant.toLowerCase().trim();
  }

  // 2. URL Path Prefix (/categories/:slug/admin or /categories/:slug/stats etc.)
  const pathParts = window.location.pathname.split("/");
  const categoriesIndex = pathParts.indexOf("categories");
  if (categoriesIndex !== -1 && pathParts[categoriesIndex + 1]) {
    const slug = pathParts[categoriesIndex + 1].trim();
    if (slug) {
      return slug.toLowerCase();
    }
  }

  // 3. Subdomain Hostname resolution
  const hostname = window.location.hostname.toLowerCase().trim();
  const parts = hostname.split(".");

  const isIpAddress = (value) => {
    return /^(?:\d{1,3}\.){3}\d{1,3}$/.test(value) || /^\[[0-9a-f:.]+\]$/.test(value);
  };

  const platformHosts = new Set(
    (import.meta.env.VITE_PLATFORM_DOMAINS || "localhost,127.0.0.1,telite.com,platform.telite.com")
      .split(",")
      .map((host) => host.trim().toLowerCase())
      .filter(Boolean)
  );

  if (isIpAddress(hostname) || platformHosts.has(hostname)) {
    return null;
  }

  if (parts.length < 3) {
    return null;
  }

  const tenantSlug = parts[0].toLowerCase().trim();
  if (tenantSlug) {
    return tenantSlug;
  }

  // 4. Logged-in Session Profile scope
  if (
    sessionUser?.category_scope &&
    ["learner", "category_admin"].includes(sessionUser?.role)
  ) {
    return sessionUser.category_scope.toLowerCase().trim();
  }

  return null;
}
