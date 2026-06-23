# Question Bank API Contract V1.1

Status: Frozen for frontend consumption  
Version: 1.1  
Scope: Question Bank Manager, Question Picker, taxonomy UI, import wizard  
Base prefix: `/api/v1`

## Contract Rules

- All endpoints are tenant-scoped by authenticated user `org_id`.
- Tags are ID-only. Do not submit free-form tag strings in question payloads.
- Question filtering is server-side. Frontend must not fetch all questions and filter locally.
- Filter parameters compose with AND semantics.
- Category hierarchy is unlimited in the database. UI should display up to 3 levels unless later revised.
- Category/tag deletion is protected. Referenced taxonomy returns `409 Conflict`.
- Learner runtime does not query Question Bank tables. Published course snapshots carry hydrated question payloads.

## Shared Question Item

```json
{
  "id": 39,
  "bank_id": 42,
  "category_id": 7,
  "tag_ids": [6, 9],
  "current_draft_version_id": null,
  "current_published_version_id": 45,
  "question_type": "multiple_choice",
  "question_text": "Photosynthesis converts light into chemical energy.",
  "points": 2,
  "status": "PUBLISHED",
  "version_state": "PUBLISHED",
  "options_json": [
    { "id": "a", "text": "True" },
    { "id": "b", "text": "False" }
  ],
  "correct_answer_json": ["a"],
  "active_version_id": 45,
  "version_number": 1
}
```

## Question Banks

### `GET /question-banks`

Returns the question banks visible to the current tenant.

Response:

```json
[
  { "id": 42, "name": "Biology Bank" }
]
```

### `POST /question-banks`

Request:

```json
{ "name": "Biology Bank" }
```

Response:

```json
{ "id": 42, "name": "Biology Bank" }
```

### `GET /question-banks/{bank_id}`

Response:

```json
{ "id": 42, "name": "Biology Bank" }
```

Errors:

```json
{ "detail": "Question bank not found" }
```

Status: `404`

## Questions

### `GET /question-banks/questions`

Global server-side search endpoint for Question Picker and cross-bank authoring views.

Query parameters:

```text
bank_id?: int
category_id?: int
tag_id?: int
question_type?: string
search?: string
version_state?: DRAFT | PUBLISHED | ARCHIVED
page?: int, default 1
page_size?: int, default 50, max 100
sort_by?: updated_at | created_at | question_text | version_number | id, default updated_at
sort_order?: asc | desc, default desc
```

Notes:

- `version_state` targets `QuestionVersion.status`.
- `status` is a deprecated compatibility alias for `version_state`; frontend code must use `version_state`.
- All filters compose as AND.
- Sorting is server-side and stable for paginated views.

Example:

```text
GET /api/v1/question-banks/questions?search=physics&category_id=7&tag_id=6&version_state=PUBLISHED&page=1&page_size=50&sort_by=updated_at&sort_order=desc
```

Response:

```json
{
  "items": [
    {
      "id": 39,
      "bank_id": 42,
      "category_id": 7,
      "tag_ids": [6],
      "current_draft_version_id": null,
      "current_published_version_id": 45,
      "question_type": "multiple_choice",
      "question_text": "Physics question text",
      "points": 2,
      "status": "PUBLISHED",
      "version_state": "PUBLISHED",
      "options_json": [],
      "correct_answer_json": [],
      "active_version_id": 45,
      "version_number": 1
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 1,
  "total_pages": 1
}
```

### `GET /question-banks/{bank_id}/questions`

Same response and filters as global question search, scoped to one bank.

Example:

```text
GET /api/v1/question-banks/42/questions?category_id=7&tag_id=6&version_state=PUBLISHED&search=photosynthesis
```

### `POST /question-banks/{bank_id}/questions`

Creates a question and its initial DRAFT version.

Request:

```json
{
  "category_id": 7,
  "tag_ids": [6, 9],
  "question_type": "multiple_choice",
  "question_text": "What is 2 + 2?",
  "points": 10,
  "options_json": [
    { "id": "a", "text": "3" },
    { "id": "b", "text": "4" }
  ],
  "correct_answer_json": ["b"]
}
```

Response:

```json
{
  "id": 39,
  "current_draft_version_id": 45,
  "category_id": 7,
  "tag_ids": [6, 9]
}
```

Errors:

```json
{ "detail": "Category not found or belongs to another tenant" }
```

Status: `400`

```json
{ "detail": "One or more tags were not found or belong to another tenant" }
```

Status: `400`

### `PUT /question-banks/{bank_id}/questions/{question_id}/draft`

Updates the current DRAFT version. Fails if no draft exists.

Request:

```json
{
  "category_id": 8,
  "tag_ids": [9],
  "question_text": "Updated draft text",
  "points": 5
}
```

Response:

```json
{
  "id": 39,
  "draft_version_id": 46,
  "status": "updated",
  "category_id": 8,
  "tag_ids": [9]
}
```

Errors:

```json
{ "detail": "No active draft exists. Create a new draft from the published version first." }
```

Status: `400`

### `POST /question-banks/{bank_id}/questions/{question_id}/publish`

Publishes the current draft version.

Response:

```json
{
  "id": 39,
  "published_version_id": 46,
  "status": "published"
}
```

### `POST /question-banks/{bank_id}/questions/{question_id}/drafts`

Creates a new DRAFT version from the current PUBLISHED version.

Response:

```json
{
  "id": 39,
  "draft_version_id": 47,
  "status": "draft_created"
}
```

### `DELETE /question-banks/{bank_id}/questions/{question_id}/draft`

Archives the current draft. Does not archive the active published version.

Response:

```json
{ "status": "archived" }
```

### `GET /question-banks/{bank_id}/questions/{question_id}/versions`

Response:

```json
[
  {
    "id": 46,
    "status": "PUBLISHED",
    "created_at": "2026-06-22T12:00:00+05:30",
    "question_type": "multiple_choice",
    "question_text": "What is 2 + 2?",
    "points": 10,
    "options_json": [
      { "id": "a", "text": "3" },
      { "id": "b", "text": "4" }
    ],
    "correct_answer_json": ["b"],
    "is_current_draft": false,
    "is_current_published": true
  }
]
```

## Categories

### `GET /question-banks/categories`

Query parameters:

```text
tree?: boolean, default true
```

Tree response:

```json
{
  "items": [
    {
      "id": 1,
      "name": "Science",
      "parent_id": null,
      "children": [
        {
          "id": 2,
          "name": "Physics",
          "parent_id": 1,
          "children": []
        }
      ]
    }
  ]
}
```

Flat response with `tree=false`:

```json
{
  "items": [
    { "id": 1, "name": "Science", "parent_id": null },
    { "id": 2, "name": "Physics", "parent_id": 1 }
  ]
}
```

### `POST /question-banks/categories`

Request:

```json
{
  "name": "Physics",
  "parent_id": 1
}
```

Response:

```json
{ "id": 2, "name": "Physics", "parent_id": 1 }
```

### `PUT /question-banks/categories/{category_id}`

Request:

```json
{
  "name": "Physical Science",
  "parent_id": 1
}
```

Response:

```json
{ "id": 2, "name": "Physical Science", "parent_id": 1 }
```

Errors:

```json
{ "detail": "Category cannot be its own parent" }
```

Status: `400`

```json
{ "detail": "Category parent would create a cycle" }
```

Status: `400`

### `DELETE /question-banks/categories/{category_id}`

Response:

```json
{ "success": true }
```

Errors:

```json
{ "detail": "Category is in use by questions or child categories and cannot be deleted" }
```

Status: `409`

## Tags

### `GET /question-banks/tags`

Response:

```json
{
  "items": [
    { "id": 6, "name": "board-exam" },
    { "id": 9, "name": "conceptual" }
  ]
}
```

### `POST /question-banks/tags`

Request:

```json
{ "name": "board-exam" }
```

Response:

```json
{ "id": 6, "name": "board-exam" }
```

### `PUT /question-banks/tags/{tag_id}`

Request:

```json
{ "name": "final-exam" }
```

Response:

```json
{ "id": 6, "name": "final-exam" }
```

### `DELETE /question-banks/tags/{tag_id}`

Response:

```json
{ "success": true }
```

Errors:

```json
{ "detail": "Tag is in use by questions and cannot be deleted" }
```

Status: `409`

## Import Jobs

### `POST /question-banks/imports`

Creates an import job and persists taxonomy selections for future import commit flow.

Request:

```json
{
  "file_key": "imports/questions.csv",
  "category_id": 1,
  "tag_ids": [6, 9]
}
```

Response:

```json
{
  "id": "2bb9944f491e4c91a8a1",
  "status": "UPLOADED",
  "metadata_json": {
    "file_key": "imports/questions.csv",
    "category_id": 1,
    "tag_ids": [6, 9]
  }
}
```

## Stale Version Check

### `POST /question-banks/check-stale`

Request:

```json
{
  "items": [
    { "question_id": 39, "version_id": 45 }
  ]
}
```

Response:

```json
{
  "39": {
    "is_stale": true,
    "latest_version_id": 46
  }
}
```

## Deprecated Compatibility

The `status` query parameter remains accepted as a compatibility alias for `version_state`, but new frontend work must not use it. This avoids duplicate frontend concepts for the same `QuestionVersion.status` filter.

## Verified Backend Gates

The V1 contract is backed by these scripts:

```powershell
python verify_question_bank_taxonomy_e2e.py
python verify_question_bank_e2e.py
```

Verified behaviors:

- Category CRUD
- Tag CRUD
- Category hierarchy response
- Category/tag tenant validation
- Delete protection for referenced taxonomy
- Server-side search
- Server-side pagination
- Category filter
- Tag filter
- Question type filter
- `QuestionVersion.status` filter
- Cross-filter AND composition
- Import taxonomy metadata persistence
- Cross-tenant isolation
- Question Bank publish-time hydration
- Immutable published snapshots
- Stale reference detection
- Learner quiz runtime against hydrated snapshots

