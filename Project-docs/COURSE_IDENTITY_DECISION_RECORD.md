# Architecture Decision Record: Course Identity

## Context
Telite LMS is transitioning to a strict multi-tenant architecture. The current database schema enforces a global uniqueness constraint on the `slug` field for both `Course` and `Category` models. This prevents multiple organizations from using common course slugs (e.g., "introduction-to-programming"), leading to failed course creations and cross-tenant leakage (Bug RC-003).

Furthermore, we must determine the correct canonical boundary for course uniqueness: Should a course be unique globally, per organization, or per category within an organization?

## Decision
We will adopt **`org_id + slug`** as the canonical identity and uniqueness constraint for both `Course` and `Category` models.

## Rationale
1. **Multi-Tenant Isolation:** Enforcing uniqueness at the `org_id` level ensures that each tenant operates within an isolated namespace. A slug collision in Org A will not affect Org B.
2. **Category Independence:** We rejected scoping by `category_slug` (i.e., `org_id + category_slug + slug`) because `course_repo.py` allows courses to be updated and moved between categories. Binding identity to a mutable relationship leads to brittle URLs and complex migration scenarios.
3. **Routing Continuity:** Internal routing already relies predominantly on the UUID `id` (e.g., `/courses/{id}`). Updating the unique constraint on the database level will not disrupt existing primary key routing while enabling safe slug generation.

## Consequences
- **Database Migration:** An Alembic migration is required to drop the existing `UNIQUE(slug)` constraint on both `courses` and `categories` tables, and replace it with a composite `UNIQUE(org_id, slug)` constraint.
- **Application Logic:** Slugs must be generated and validated against the `org_id` context. The `create_course` and `create_category` functions in repositories must handle potential slug collisions within the tenant scope gracefully (e.g., appending a suffix).
- **Resolution:** This decision directly resolves the multi-tenant collision bug (RC-003).
