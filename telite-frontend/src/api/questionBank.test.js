import test from "node:test";
import assert from "node:assert/strict";

import { getQuestionBankErrorMessage } from "./questionBankErrors.js";
import { buildQuestionQueryParams } from "./questionBankQuery.js";

test("question query params use frozen V1.1 field names", () => {
  assert.deepEqual(
    buildQuestionQueryParams({
      bankId: 42,
      search: "  physics  ",
      versionState: "PUBLISHED",
      page: 2,
      pageSize: 25,
      sortBy: "question_text",
      sortOrder: "asc",
    }),
    {
      bank_id: 42,
      search: "physics",
      version_state: "PUBLISHED",
      page: 2,
      page_size: 25,
      sort_by: "question_text",
      sort_order: "asc",
    }
  );
});

test("question query params omit deprecated status alias", () => {
  const params = buildQuestionQueryParams({ versionState: "DRAFT" });

  assert.equal(params.version_state, "DRAFT");
  assert.equal(Object.hasOwn(params, "status"), false);
});

test("question query params compose taxonomy and type filters", () => {
  assert.deepEqual(
    buildQuestionQueryParams({
      search: "force",
      categoryId: 7,
      tagId: 9,
      questionType: "multiple_choice",
      versionState: "PUBLISHED",
    }),
    {
      search: "force",
      category_id: 7,
      tag_id: 9,
      question_type: "multiple_choice",
      version_state: "PUBLISHED",
      page: 1,
      page_size: 50,
      sort_by: "updated_at",
      sort_order: "desc",
    }
  );
});

test("question bank errors surface protected taxonomy conflicts", () => {
  assert.equal(
    getQuestionBankErrorMessage({
      response: {
        status: 409,
        data: { detail: "Category is in use by questions or child categories and cannot be deleted" },
      },
    }),
    "Category is in use by questions or child categories and cannot be deleted"
  );
});
