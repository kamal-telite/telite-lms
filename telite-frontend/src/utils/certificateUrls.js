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

function parseContentDispositionFilename(contentDisposition = "") {
  const match = /filename\*?=(?:UTF-8''|"?)([^";]+)(?:"|$)/i.exec(contentDisposition);
  if (!match) return null;
  return decodeURIComponent(match[1]);
}

export async function fetchCertificatePdf(courseId, options = {}) {
  const {
    inline = false,
    baseUrl = "",
  } = options;

  const url = buildCertificateDownloadUrl(courseId, { inline, baseUrl });
  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(text || `Certificate request failed with status ${response.status}`);
  }

  const contentType = response.headers.get("content-type") || "application/pdf";
  const blob = await response.blob();
  const fileName = parseContentDispositionFilename(response.headers.get("content-disposition")) || `certificate_${courseId}.pdf`;

  return {
    blob,
    contentType,
    fileName,
    url,
  };
}
