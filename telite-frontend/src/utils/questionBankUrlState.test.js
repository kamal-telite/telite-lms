import test from "node:test";
import assert from "node:assert/strict";

import {
  buildQuestionBankUrlParams,
  parseQuestionBankUrlState,
} from "./questionBankUrlState.js";

test("question bank URL state parses shareable manager filters", () => {
  const state = parseQuestionBankUrlState(
    "bank=1&category=7&tag=9&version_state=PUBLISHED&search=force&page=2&sort_by=created_at&sort_order=asc"
  );

  assert.deepEqual(state, {
    bankId: 1,
    query: {
      search: "force",
      categoryId: "7",
      tagId: "9",
      questionType: "",
      versionState: "PUBLISHED",
      page: 2,
      pageSize: 50,
      sortBy: "created_at",
      sortOrder: "asc",
    },
  });
});

test("question bank URL state supports legacy explicit ID params", () => {
  const state = parseQuestionBankUrlState("bank_id=4&category_id=8&tag_id=11&page_size=100");

  assert.equal(state.bankId, 4);
  assert.equal(state.query.categoryId, "8");
  assert.equal(state.query.tagId, "11");
  assert.equal(state.query.pageSize, 100);
});

test("question bank URL builder omits default values", () => {
  const params = buildQuestionBankUrlParams({
    bankId: 1,
    query: {
      search: " force ",
      categoryId: "7",
      tagId: "",
      questionType: "multiple_choice",
      versionState: "PUBLISHED",
      page: 1,
      pageSize: 50,
      sortBy: "updated_at",
      sortOrder: "desc",
    },
  });

  assert.equal(params.toString(), "bank=1&search=force&category=7&question_type=multiple_choice&version_state=PUBLISHED");
});
