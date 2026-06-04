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
  const hostname = window.location.hostname;
  const parts = hostname.split(".");
  
  const isPlatformHost =
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "telite.com" ||
    hostname.startsWith("platform.") ||
    (hostname.endsWith("telite.com") && parts.length === 2);

  if (!isPlatformHost && parts.length >= 2) {
    // If e.g. ktlearn.telite.com or ktlearn.localhost, 'ktlearn' is the subdomain
    return parts[0].toLowerCase().trim();
  }

  // 4. Logged-in Session Profile scope
  if (sessionUser?.category_scope) {
    return sessionUser.category_scope.toLowerCase().trim();
  }

  return null;
}
