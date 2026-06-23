import test from "node:test";
import assert from "node:assert/strict";

import { flattenCategoryOptions, toggleTagId } from "./questionTaxonomy.js";

test("category options flatten hierarchical labels for editor forms", () => {
  const options = flattenCategoryOptions([
    {
      id: 1,
      name: "Science",
      parent_id: null,
      children: [
        {
          id: 2,
          name: "Physics",
          parent_id: 1,
          children: [{ id: 3, name: "Mechanics", parent_id: 2, children: [] }],
        },
      ],
    },
  ]);

  assert.deepEqual(
    options.map((option) => option.label),
    ["Science", "Science / Physics", "Science / Physics / Mechanics"]
  );
});

test("tag toggle stores sorted numeric IDs only", () => {
  assert.deepEqual(toggleTagId([9], "6"), [6, 9]);
  assert.deepEqual(toggleTagId([6, 9], 6), [9]);
});
