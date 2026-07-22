# TELITE LMS Tenant Architecture

This document details the multi-tenant architecture and isolation mechanisms implemented in the Telite LMS platform.

## 1. How `org_id` Flows
The `org_id` represents the tenant (organization) identity. 
- **Authentication**: Upon login, the user's `org_id` is embedded in their JWT payload.
- **API Request Context**: On each request, dependencies in `telite-backend/app/api/auth.py` parse the JWT. Functions like `resolve_org_scope` and `ensure_org_access` identify the target `org_id`.
- **Database Session**: The `org_id` is then passed to `set_rls_context(session, org_id)` which injects the tenant ID directly into the PostgreSQL connection context (`app.current_org_id`).

## 2. Tenant Isolation Enforcement (PostgreSQL RLS)
The cornerstone of tenant isolation in Telite LMS is **PostgreSQL Row-Level Security (RLS)**.
- Detailed in `telite-backend/app/db/rls.py`, a policy named `telite_tenant_isolation_{table}` is applied to all tenant-scoped tables.
- The policy enforces that any row accessed or modified must have an `org_id` matching `current_setting('app.current_org_id')`.
- This ensures that even if application logic fails to filter by `org_id`, the database inherently prevents cross-tenant data spillage.
- Platform administrators can bypass this by setting `app.bypass_rls = 'on'`.

## 3. Repository Filtering
While RLS acts as a safety net, the application layer proactively filters by `org_id` using the repository pattern.
- **BaseRepository (`telite-backend/app/repositories/base_repo.py`)**: Provides foundational query helpers.
- `get_by_id_and_org(record_id, org_id)` explicitly checks `hasattr(record, "org_id") and record.org_id != org_id`.
- `list_by_org(org_id)` adds an explicit `WHERE org_id = :org_id` clause.
- Most domain repositories inherit from `BaseRepository` and utilize these tenant-safe methods.

## 4. API Validation
The API layer relies on dependencies in `auth.py` to validate tenant boundaries before processing business logic:
- `verify_super_admin`: Validates that a user holds the `super_admin` role and that their `org_id` matches the path/body `org_id`.
- `resolve_org_scope`: Resolves the operating context. If a user tries to act on a different `org_id` without proper platform admin permissions, the scope is defaulted to their own `org_id` or access is denied.

## 5. UI Restrictions
The frontend (`telite-frontend`) inherently respects tenant boundaries by relying on the scoped API endpoints. Additionally:
- The user session state (`session.js`, `dashboardStore.js`) stores the `org_id`.
- For non-platform admins, lists of organizations and tenant switchers are strictly filtered (`isolatedOrgs.filter(org => org.id === user.org_id)`).

## 6. Background Worker Isolation
Celery tasks and background workers (`telite-backend/app/workers/`) execute safely across multiple tenants without mixing data.
- Task workers (like `notification_tasks.py` and `reminder_tasks.py`) iterate over a list of active `org_ids`.
- For each tenant, the worker uses the `get_tenant_session(org_id)` context manager, which establishes an isolated DB session with the RLS context specifically bound to that `org_id`.

## 7. Analytics Isolation
Analytics and event streams are isolated by using tenant-specific namespaces.
- As seen in `analytics_worker.py`, Redis streams are prefixed with the tenant ID: `tenant:{org_id}:analytics_stream`.
- Rollup tasks process these streams individually, extracting the `org_id` and performing analytics calculations scoped strictly to that tenant.

## 8. File Ownership
Media assets and uploaded files are tied to tenants.
- `telite-backend/app/models/media_asset.py` defines the `org_id` foreign key for every asset.
- Any file operations (like serving signed URLs or deletion) validate ownership against the tenant before execution, ensuring users cannot access another organization's S3/storage objects.

## 9. Features Lacking Isolation
A review of the models in `telite-backend/app/models/` reveals standard compliance with `TenantMixin` for tenant-scoped resources.
- **Global Resources**: `platform_settings` purposefully lack `org_id` as they dictate global system configurations (e.g., SMTP servers, platform-wide feature flags) and are strictly accessible only to platform admins with `bypass_rls`.
- **Note**: Ensure that any new models created inheriting `Base` rather than `TenantMixin` are either intentionally global or correctly added to the `TENANT_SCOPED_TABLES` list in `rls.py`.
