import test from "node:test";
import assert from "node:assert/strict";

import {
  buildQuestionImportPayload,
  getImportFileKey,
  getImportStatusTone,
} from "./questionImportJob.js";

test("question import payload stores taxonomy IDs only", () => {
  assert.deepEqual(
    buildQuestionImportPayload({
      fileName: "questions.csv",
      categoryId: "7",
      tagIds: ["9", 6, "9"],
    }),
    {
      file_key: "imports/questions.csv",
      category_id: 7,
      tag_ids: [6, 9],
    }
  );
});

test("question import payload allows explicit file keys", () => {
  assert.equal(
    getImportFileKey({ fileName: "ignored.csv", fileKey: "imports/physics/questions.csv" }),
    "imports/physics/questions.csv"
  );
});

test("question import status tones map failed jobs to danger", () => {
  assert.equal(getImportStatusTone("FAILED"), "danger");
  assert.equal(getImportStatusTone("UPLOADED"), "neutral");
});
