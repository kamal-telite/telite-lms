# ADR-006: Resource Identity and Tenant-Scoped Uniqueness

## Status
**Accepted**

## Context
During the resolution of the Duplicate Course Creation Bug (RC-003), it became evident that the application relied on globally unique identifiers (`slug`) for business resources. This violated the core tenet of our multi-tenant SaaS architecture, where resources should be securely isolated and uniquely identifiable strictly within the scope of their tenant (`org_id`). Additionally, the previous pattern exposed raw database `IntegrityError` exceptions to the user upon conflict, which resulted in poor UX and 500 errors.

## Decision
This ADR applies to every tenant-owned business resource exposing a human-readable identifier, including but not limited to Categories, Courses, Learning Paths, Programs, Certificate Templates, Tracks, and future domain entities.

### 1. Identity Definitions
Every business resource must clearly separate its identity into three distinct concepts:
- **Relational Identity**: The immutable database identifier. This must always be a UUID (e.g., `id = course-<hash>`). UUIDs are immutable internal identifiers and must never change throughout the lifecycle of the resource.
- **Business Uniqueness**: Business Uniqueness must be defined per domain entity. For human-readable resources, the default pattern is `UNIQUE(org_id, slug)`. If a different business key is required, it must be justified through a separate Architecture Decision Record.
- **Public URL Identity**: The human-readable string used for frontend routing (e.g., `slug`). Slugs must only be unique within their tenant, never globally.

### 2. Tenant Boundaries
- Every business resource belongs to exactly one organization (`org_id`).
- No business rule or database constraint should enforce global uniqueness on properties like names or slugs.

### 3. Reusable Validation Pattern (Race Condition Safe)
Application code must validate duplicates proactively to provide good UX, but the database remains the final enforcement layer. All entity creation workflows must follow this sequence:

1. **Repository Check**: Perform a `get_by_slug(slug, org_id)` read check and raise a domain exception if a duplicate is found.
2. **Database Flush**: Issue a `session.flush()` within a `try-except` block to commit the pending insert to the transaction state.
3. **Integrity Fallback**: Catch `IntegrityError` (which occurs if two concurrent requests bypass the read check). Roll back the transaction and convert the exception into a domain exception.
4. **Structured Domain Exception**: Raise a unified `DuplicateResourceError(resource_type, field, message)`.
5. **API Mapping**: The router catches the domain exception and returns an HTTP `409 Conflict` structured JSON payload. Organizational Standard: Use `409 Conflict` for duplicate resources and uniqueness violations. Use `422 Unprocessable Entity` exclusively for validation failures such as invalid format, required fields, or business rule violations unrelated to uniqueness.
6. **Frontend Inline Validation**: The React client maps the 409 error's `field` attribute directly into the local form's error state, rendering inline validation (e.g., "Course name already exists" attached to the specific input field) rather than a generic toast.

## Consequences
- **Positive**: Complete elimination of race condition bugs leading to 500 errors.
- **Positive**: Strict tenant isolation prevents different organizations from colliding on common names like "Introduction to Python".
- **Positive**: A uniform validation UX is guaranteed application-wide.
- **Negative**: Adds slight boilerplate to repository methods (the `try-except IntegrityError` wrapper), but this can be abstracted into a generic repository mixin or decorator in the future.

## Related Decisions
- ADR-005 — Universal Block Architecture
- ADR-006 — Resource Identity and Tenant-Scoped Uniqueness
- RC-003 — Duplicate Course Creation Resolution
- Master Technical Debt Backlog v1.0
