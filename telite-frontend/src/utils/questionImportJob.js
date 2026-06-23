export const QUESTION_IMPORT_STATUSES = ["UPLOADED", "VALIDATED", "COMMITTED", "FAILED"];

export function getImportFileKey({ fileName, fileKey }) {
  const trimmedKey = String(fileKey || "").trim();
  if (trimmedKey) {
    return trimmedKey;
  }

  const trimmedName = String(fileName || "").trim();
  if (!trimmedName) {
    return "";
  }

  return `imports/${trimmedName}`;
}

export function buildQuestionImportPayload({ fileName, fileKey, categoryId, tagIds }) {
  const resolvedFileKey = getImportFileKey({ fileName, fileKey });
  const normalizedTags = Array.from(
    new Set((tagIds || []).map((tagId) => Number(tagId)).filter((tagId) => Number.isInteger(tagId)))
  ).sort((a, b) => a - b);

  return {
    file_key: resolvedFileKey,
    category_id: categoryId ? Number(categoryId) : null,
    tag_ids: normalizedTags,
  };
}

export function getImportStatusTone(status) {
  const normalized = String(status || "").toUpperCase();
  if (normalized === "COMMITTED" || normalized === "VALIDATED") return "success";
  if (normalized === "FAILED") return "danger";
  return "neutral";
}
