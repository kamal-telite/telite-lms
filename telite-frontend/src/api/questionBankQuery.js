export const QUESTION_BANK_SORT_FIELDS = [
  "updated_at",
  "created_at",
  "question_text",
  "version_number",
  "id",
];

export const QUESTION_BANK_VERSION_STATES = ["DRAFT", "PUBLISHED", "ARCHIVED"];

export function buildQuestionQueryParams({
  bankId,
  search,
  versionState,
  categoryId,
  tagId,
  questionType,
  page = 1,
  pageSize = 50,
  sortBy = "updated_at",
  sortOrder = "desc",
} = {}) {
  const params = {};

  if (bankId) params.bank_id = bankId;
  if (search?.trim()) params.search = search.trim();
  if (versionState) params.version_state = versionState;
  if (categoryId) params.category_id = categoryId;
  if (tagId) params.tag_id = tagId;
  if (questionType) params.question_type = questionType;

  params.page = page;
  params.page_size = pageSize;
  params.sort_by = sortBy;
  params.sort_order = sortOrder;

  return params;
}
