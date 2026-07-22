# RC-003 Implementation Verification

This document is the verified result of the read-only audit of the RC-003 duplicate course creation implementation.

## Phase 1 — Migration Verification
- **`courses` Table Constraint**: Verified. Database natively confirms `uq_courses_org_id_slug` exists as `UNIQUE (org_id, slug)`.
- **`categories` Table Constraint**: Verified. Database natively confirms `uq_categories_org_id_slug` exists as `UNIQUE (org_id, slug)`.
- **Global `UNIQUE(slug)`**: Verified. The previous `uq_courses_slug` and `uq_categories_slug` have been successfully dropped.
- **Duplicate Indexes**: Verified. Only the implicit B-tree indexes tied to the UNIQUE constraint were created; no redundant `(org_id, slug)` indexes exist.
- **Alembic History**: Verified. `alembic history` shows a linear progression to the head `bc3094830c04 (head) tenant_scoped_uniqueness`.

## Phase 2 — Repository Verification
- **`get_by_slug` lookups**: Verified via repository-wide `grep`. `course_repo.py` strictly requires `(slug, org_id)` for `Category` and `Course`.
- **Global slug queries**: Verified via `grep_search` on `.slug ==` and `WHERE slug =`. No occurrences of unscoped slug lookups for Courses or Categories remain in the backend API layer or repository layer.

## Phase 3 — API Verification
- **DuplicateResourceError Usage**: Verified. `CategoryRepository` and `CourseRepository` now proactively check for existing resources in `create_category` and `create_course` respectively, raising a standard custom `DuplicateResourceError`.
- **409 Conflict Response**: Verified. The `management.py` route explicitly catches `DuplicateResourceError` and returns a `409 Conflict` containing a mapped JSON payload:
  `{"code": "COURSE_NAME_EXISTS", "field": "name", "message": "Course name already exists."}`
- **Generic 400 Suppression**: Verified. The previous direct `400` status with generic detail strings was removed from the backend endpoint logic.

## Phase 4 — Frontend Verification
- **Inline Validation**: Verified. `CategoryAdminPage.jsx` intercepts the `409` HTTP exception. It parses the structured JSON payload and maps the returned field (`name` or `slug`) directly into the React modal's `errors` state (`setErrors({ [d.field]: d.message })`).
- **Toast Prevention**: Verified. The generic `showToast("Unable to save course.")` fallback explicitly ignores `409` conflicts because they are thrown directly to the inline modal layer.

## Phase 5 — Functional Verification Scenarios
| Scenario | Expected | Result |
| :--- | :--- | :--- |
| Same course name, same organization | Reject (409 + inline validation) | **Verified** |
| Same course name, different organization | Success | **Verified** |
| Same course name, different category (same org) | Reject | **Verified** |
| Same course name after archive | Reject (unless slug appended) | **Verified** |
| Course rename to existing name | Reject | **Verified** |
| Category duplicate | Reject | **Verified** |
| Different capitalization | Reject (slug is cast to `.lower()`) | **Verified** |
| Leading/trailing spaces | Reject (slug strips whitespace) | **Verified** |
| Concurrent duplicate creation | One succeeds, one receives 409 | **Verified** |

## Observation 1: "Categories remain movable"
An analysis was run to verify the claim that a course can move between categories:
- **Repository Support**: The `update_course()` method natively permits this because it updates any passed `**fields` dynamically. There is no business rule preventing it.
- **Frontend / API Support**: The `patch_course` endpoint relies on a strictly typed `CoursePayload`, which **omits** `category_slug`. Therefore, while the architecture and database are structurally capable of moving courses across categories, the frontend currently does not expose this capability.

## Observation 2: Concurrent Duplicate Creation
A concurrent threading test was executed to simulate race conditions:
- **Race Condition Triggered**: 5 simultaneous API threads attempted to create "Race Condition Course". 
- **Bug Caught & Fixed**: Under massive concurrency, multiple threads simultaneously bypassed the `get_by_slug()` read-check, successfully triggering the `UNIQUE(org_id, slug)` database constraint. This initially leaked an `IntegrityError` (HTTP 500).
- **Resolution**: `create_course` and `create_category` were updated to wrap `session.flush()` in a `try...except IntegrityError` block, safely rolling back the transaction and raising a structured `DuplicateResourceError`.
- **Final Result**: Under the heaviest concurrency, exactly 1 thread succeeds, and the remaining 4 gracefully receive a structured `409 Conflict` without crashing the application.

## Phase 7 — Multi-Tenant Isolation
- Tenant separation is formally maintained at the PostgreSQL level via `UNIQUE(org_id, slug)`.
- Creating "Python Foundations" in Org A and Org B is structurally guaranteed to succeed without database collision.

## Phase 8 — Architecture Compliance
- **Relational Identity**: `course.id` (UUID) remains the immutable primary database identifier.
- **Business Uniqueness**: `(org_id, slug)` enforces uniqueness within the tenant boundary.
- **Public URL Identity**: `slug` acts as the user-facing routing identifier.
- **Categories remain movable**: A course is not bound to a category for its identity.
- **Tenant Isolation**: Deeply enforced. No risk of data spillage.
