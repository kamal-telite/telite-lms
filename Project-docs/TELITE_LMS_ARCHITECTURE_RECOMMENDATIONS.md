# TELITE LMS Architecture Recommendations

## 1. Implement Domain-Driven Design (DDD) Boundaries
**Current Implementation**: Flat structure for all models in `app/models`.
**Alternative Designs**: Group related entities into Bounded Contexts (e.g., `Identity`, `Catalog`, `Enrollment`, `Assessment`).
**Pros**: Easier to reason about, clear ownership, paves the way for microservices.
**Cons**: Requires refactoring imports and potentially complex DB migrations.
**Migration Complexity**: High
**Regression Risk**: Moderate
**Recommended Approach**: Start logically grouping models into sub-packages within the monolith before physically separating them.

## 2. Event-Driven Progress Tracking
**Current Implementation**: Likely synchronous cascading updates across `LessonBlockProgress`, `ModuleProgress`, `CourseProgress`.
**Alternative Designs**: Use Domain Events (e.g., `LessonCompletedEvent`) published to a message bus or event queue, handled by asynchronous workers.
**Pros**: Decouples the progress aggregation logic, improves API latency, handles scale better.
**Cons**: Eventual consistency might confuse users if UI does not reflect progress immediately.
**Migration Complexity**: High
**Regression Risk**: High
**Recommended Approach**: Introduce an internal in-memory event bus or use `app/workers` for out-of-band progress recalculation.

## 3. Decouple `main.py`
**Current Implementation**: `main.py` is nearly 16KB and likely handles too many responsibilities.
**Alternative Designs**: Split into `router.py`, `dependencies.py`, `middleware.py`, and `config.py`.
**Pros**: Improves maintainability and readability.
**Cons**: None.
**Migration Complexity**: Low
**Regression Risk**: Low
**Recommended Approach**: Refactor immediately. Extract route registrations into domain-specific routers.

## 4. Consolidate Audit Logging
**Current Implementation**: Disparate audit logs (`audit.py`, `audit_log.py`, `builder_activity_log.py`, `learner_activity_log.py`).
**Alternative Designs**: Use a unified `EventStore` or a single `ActivityLog` with a JSON payload for context.
**Pros**: Easier to query, unified schema, easier to ship to ELK/Splunk.
**Cons**: JSON queries can be slower if not indexed properly.
**Migration Complexity**: Medium
**Regression Risk**: Low
**Recommended Approach**: Deprecate specific log tables in favor of a central polymorphic `Event` table with JSONB for metadata.

## 5. Tenancy Enforcement via Middleware/Database Policies
**Current Implementation**: `TenantMixin` suggests application-level filtering.
**Alternative Designs**: Row-Level Security (RLS) in PostgreSQL.
**Pros**: Zero chance of cross-tenant data leakage due to developer error.
**Cons**: Harder to implement connection pooling and requires setting DB context per request.
**Migration Complexity**: High
**Regression Risk**: Medium
**Recommended Approach**: Stick to ORM-level filtering but enforce it automatically via SQLAlchemy event listeners rather than relying on developers adding `.filter(tenant_id=...)`.
