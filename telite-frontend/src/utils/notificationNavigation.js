const SUPPORTED_NOTIFICATION_ROUTE_PREFIXES = [
  "/learner",
  "/categories/",
  "/platform-admin",
  "/super-admin",
];

const UNSUPPORTED_NOTIFICATION_ROUTE_PREFIXES = [
  "/api/",
  "/authoring/courses/",
  "/courses/",
];

export function getNotificationRoute(notification) {
  const route = notification?.metadata_json?.route;
  if (typeof route !== "string" || !route.trim()) return "";
  return route.trim();
}

export function isSupportedNotificationRoute(route) {
  if (!route) return false;
  if (UNSUPPORTED_NOTIFICATION_ROUTE_PREFIXES.some((prefix) => route.startsWith(prefix))) {
    return false;
  }
  return SUPPORTED_NOTIFICATION_ROUTE_PREFIXES.some(
    (prefix) => route === prefix.replace(/\/$/, "") || route.startsWith(prefix)
  );
}

export function getNavigableNotificationRoute(notification) {
  const route = getNotificationRoute(notification);
  return isSupportedNotificationRoute(route) ? route : "";
}
