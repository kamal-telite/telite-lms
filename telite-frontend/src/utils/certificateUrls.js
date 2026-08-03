function normalizeBaseUrl(baseUrl = "") {
  if (!baseUrl) return "";
  return baseUrl.replace(/\/$/, "");
}

export function buildApiUrl(path, baseUrl = "") {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const normalizedBaseUrl = normalizeBaseUrl(baseUrl);
  return normalizedBaseUrl ? `${normalizedBaseUrl}${normalizedPath}` : normalizedPath;
}

export function buildCertificateDownloadUrl(courseId, options = {}) {
  const {
    inline = false,
    baseUrl = "",
  } = options;

  const query = inline ? "?inline=true" : "";
  return buildApiUrl(`/api/certificates/${courseId}/download${query}`, baseUrl);
}
