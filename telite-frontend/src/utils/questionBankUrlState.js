const SORT_FIELDS = ["updated_at", "created_at", "question_text", "version_number", "id"];
const SORT_ORDERS = ["asc", "desc"];
const VERSION_STATES = ["DRAFT", "PUBLISHED", "ARCHIVED"];
const PAGE_SIZES = [25, 50, 100];

export const DEFAULT_QUESTION_BANK_URL_QUERY = {
  search: "",
  categoryId: "",
  tagId: "",
  questionType: "",
  versionState: "",
  page: 1,
  pageSize: 50,
  sortBy: "updated_at",
  sortOrder: "desc",
};

function toPositiveInt(value, fallback) {
  const parsed = Number.parseInt(value, 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function normalizeEnum(value, allowed, fallback = "") {
  return allowed.includes(value) ? value : fallback;
}

export function parseQuestionBankUrlState(searchParams) {
  const params = searchParams instanceof URLSearchParams
    ? searchParams
    : new URLSearchParams(searchParams || "");
  const pageSize = toPositiveInt(params.get("page_size"), DEFAULT_QUESTION_BANK_URL_QUERY.pageSize);

  return {
    bankId: toPositiveInt(params.get("bank") || params.get("bank_id"), null),
    query: {
      search: params.get("search") || "",
      categoryId: params.get("category") || params.get("category_id") || "",
      tagId: params.get("tag") || params.get("tag_id") || "",
      questionType: params.get("question_type") || "",
      versionState: normalizeEnum(params.get("version_state"), VERSION_STATES),
      page: toPositiveInt(params.get("page"), DEFAULT_QUESTION_BANK_URL_QUERY.page),
      pageSize: PAGE_SIZES.includes(pageSize) ? pageSize : DEFAULT_QUESTION_BANK_URL_QUERY.pageSize,
      sortBy: normalizeEnum(params.get("sort_by"), SORT_FIELDS, DEFAULT_QUESTION_BANK_URL_QUERY.sortBy),
      sortOrder: normalizeEnum(params.get("sort_order"), SORT_ORDERS, DEFAULT_QUESTION_BANK_URL_QUERY.sortOrder),
    },
  };
}

export function buildQuestionBankUrlParams({ bankId, query }) {
  const next = new URLSearchParams();
  const mergedQuery = { ...DEFAULT_QUESTION_BANK_URL_QUERY, ...(query || {}) };

  if (bankId) next.set("bank", String(bankId));
  if (mergedQuery.search?.trim()) next.set("search", mergedQuery.search.trim());
  if (mergedQuery.categoryId) next.set("category", String(mergedQuery.categoryId));
  if (mergedQuery.tagId) next.set("tag", String(mergedQuery.tagId));
  if (mergedQuery.questionType) next.set("question_type", mergedQuery.questionType);
  if (mergedQuery.versionState) next.set("version_state", mergedQuery.versionState);
  if (mergedQuery.page > 1) next.set("page", String(mergedQuery.page));
  if (mergedQuery.pageSize !== DEFAULT_QUESTION_BANK_URL_QUERY.pageSize) {
    next.set("page_size", String(mergedQuery.pageSize));
  }
  if (mergedQuery.sortBy !== DEFAULT_QUESTION_BANK_URL_QUERY.sortBy) {
    next.set("sort_by", mergedQuery.sortBy);
  }
  if (mergedQuery.sortOrder !== DEFAULT_QUESTION_BANK_URL_QUERY.sortOrder) {
    next.set("sort_order", mergedQuery.sortOrder);
  }

  return next;
}
