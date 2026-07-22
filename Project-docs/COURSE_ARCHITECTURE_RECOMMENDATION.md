# TELITE LMS Course Architecture Recommendations

## 1. Review of Existing Architecture Documents (Contradictions & Verifications)

### 1.1. `TELITE_LMS_DATABASE_SCHEMA_AUDIT.md`
- **Contradiction (Incorrect)**: Lists `organization_id` as the tenant field for `courses`.
- **Verification (Code)**: The `Course` model inherits from `TenantMixin`, which provides `org_id` as the canonical tenant field. There is no `organization_id` on the `Course` model.

### 1.2. `TELITE_LMS_TENANT_ARCHITECTURE.md`
- **Contradiction (Incorrect/Outdated)**: Claims "Zero chance of cross-tenant data leakage due to developer error" via PostgreSQL Row-Level Security (RLS).
- **Verification (Code)**: While RLS restricts `SELECT`/`UPDATE`/`DELETE` operations, **PostgreSQL UNIQUE constraints operate globally, ignoring RLS**. The `slug` field on `courses` is defined as `unique=True`. This results in a side-channel data leak: if Org B tries to create a course with the same name as Org A, the DB throws an `IntegrityError`, revealing the existence of that course name in another tenant's workspace.

### 1.3. `TELITE_LMS_ARCHITECTURE_RECOMMENDATIONS.md`
- **Status (Verified)**: Recommends transitioning to Domain-Driven Design (DDD) and splitting monolithic domains. This remains accurate and necessary for long-term scalability.

---

## 2. Immediate RC-003 Bug Fix

**RC-003** represents the critical bug where globally unique slugs violate multi-tenant isolation, causing `IntegrityError` on duplicate course names across different organizations.

**Immediate Resolution Steps:**
1. **Application Layer (Graceful Degradation)**:
   - Update `app/repositories/course_repo.py` (`create_course` method).
   - Catch or preempt the `slug` collision.
   - Implement an auto-incrementing suffix logic: query for existing slugs `LIKE 'base-slug%'` scoped to the `org_id` (or globally, before schema change), and append `-1`, `-2` to ensure uniqueness.
2. **Schema Layer (Long-Term Fix)**:
   - Generate an Alembic migration to drop the global unique constraint on `(slug)` in the `courses` and `categories` tables.
   - Replace it with a composite unique constraint on `(org_id, slug)`.
   - *Note:* Changing DB constraints requires downtime or careful migration if data is already populated. 

---

## 3. Long-Term Architectural Recommendations

To align with **Domain-Driven Design (DDD), Multi-tenancy, Scalability, and Maintainability**, the following long-term shifts are recommended for the Course domain:

### 3.1. Strict Bounded Contexts (DDD)
Extract the `Course` domain out of the flat `app/models` directory into a dedicated `Catalog` or `LearningContent` bounded context.
- **Current**: Everything is mixed (Courses, Grading, Enrollments).
- **Target**: `app/domain/catalog/models/course.py`. Enrollments should not dictate course schema.

### 3.2. True Multi-Tenant Identifiers
Instead of relying solely on RLS and hoping developers remember composite unique constraints, embed the tenant identity into the application's unique identifiers.
- **Target**: Use compound slugs (e.g., `org-123-intro-to-python`) or UUIDv7 for external sharing, mapping them back to human-readable slugs internally. 

### 3.3. Event-Driven Propagation
- **Current**: Progress and analytics (`module_count`, `enrolled_count`, `completion_rate`) are stored directly on the `Course` table and updated synchronously.
- **Target**: Course creation, enrollment, and progress updates should emit Domain Events (e.g., `CourseCreated`, `LearnerEnrolled`). An asynchronous worker handles updating the read-optimized aggregations (CQRS pattern). This reduces table locks and improves API write latency.

### 3.4. Decoupling Category and Course
- **Current**: `Course` relies on `category_slug` as a foreign key (`category_slug = Category.slug`). This is fragile. If a category slug changes, it breaks the relationship or requires cascading string updates.
- **Target**: Use immutable primary keys (like UUIDs or `id`) for relationships (`category_id`), and keep `slug` strictly for presentation (URLs/routing).
