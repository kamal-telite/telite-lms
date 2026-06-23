import test from "node:test";
import assert from "node:assert/strict";

import { buildBankReferenceItems } from "./questionBankReferences.js";

test("bank reference imports contain only IDs and version IDs", () => {
  const references = buildBankReferenceItems([
    { id: 1, active_version_id: 45, question_text: "Do not embed me" },
    { id: 2, current_published_version_id: 61, options_json: [{ text: "Nope" }] },
    { id: 3, active_version_id: 72, correct_answer_json: ["a"] },
  ]);

  assert.deepEqual(references, [
    { id: "bank-ref-1-45", type: "bank_reference", question_id: 1, version_id: 45 },
    { id: "bank-ref-2-61", type: "bank_reference", question_id: 2, version_id: 61 },
    { id: "bank-ref-3-72", type: "bank_reference", question_id: 3, version_id: 72 },
  ]);
  assert.equal(JSON.stringify(references).includes("Do not embed me"), false);
  assert.equal(JSON.stringify(references).includes("options_json"), false);
  assert.equal(JSON.stringify(references).includes("correct_answer_json"), false);
});
