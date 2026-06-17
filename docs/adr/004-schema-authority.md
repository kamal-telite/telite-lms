# ADR-004: Schema Authority

## Status

Accepted — 2026-06-16

## Context

Telite LMS evolved from a SQLite + SQLAlchemy `create_all()` bootstrap path into a PostgreSQL deployment managed by Alembic. Two mechanisms could modify live schema:

1. **Alembic** — run on container startup via `scripts/run_migrations.py` → `alembic upgrade head`
2. **`repair_shared_columns()`** — run from `run_phase3_init()` on app lifespan when legacy bootstrap was enabled

The generic loop in `repair_shared_columns()` mirrored every ORM column onto existing tables. When a model field (e.g. `media_assets.metadata_json`) landed before its Alembic revision, startup added the column while `alembic_version` stayed behind. The later migration then failed with `DuplicateColumn`.

This is a schema authority conflict, not a feature bug.

## Decision

### Production and PostgreSQL: Alembic only

All schema changes for PostgreSQL (development Docker, staging, production) **must** be delivered as Alembic revisions. No application startup path may `ALTER TABLE` domain columns.

| Environment | `ENVIRONMENT` | Database | Schema authority |
|---|---|---|---|
| Production / staging | `production`, `prod`, `staging` | PostgreSQL | Alembic only |
| Docker / local dev | `development` | PostgreSQL | Alembic only |
| CI / unit tests | `development` | SQLite | Legacy bootstrap allowed when `TELITE_USE_ALEMBIC=false` |

PostgreSQL is always treated as Alembic-managed (`_use_alembic_migrations()` returns true when `is_postgres_dsn()`), regardless of `TELITE_USE_ALEMBIC`.

### `repair_shared_columns()`: development SQLite bootstrap only

`repair_shared_columns()` runs only when **all** of the following hold:

- `ENVIRONMENT=development`
- not production-like (`production`, `prod`, `staging`)
- `TELITE_USE_ALEMBIC` is false
- database is **not** PostgreSQL

It may repair only legacy mixin columns: `created_at`, `updated_at`, `org_id`.

It **must not** add arbitrary ORM/domain columns (e.g. `metadata_json`, `folder`, `tags_json`). Those require Alembic revisions.

### Migrations must be idempotent when feasible

Revisions that add columns should inspect existing schema before `ADD COLUMN`, matching the pattern in `a5f009` and `b2d976c3de97`, so drift recovery does not block startup.

## Consequences

### Positive

- Single source of truth for PostgreSQL schema history
- No race between ORM model changes and Alembic on Docker startup
- Clear rule for contributors: model change → Alembic revision → deploy

### Negative / trade-offs

- SQLite CI bootstrap no longer auto-adds new domain columns; tests using `TELITE_USE_ALEMBIC=false` rely on `create_all()` for new tables/columns on fresh DBs
- Existing databases with drift must be reconciled via idempotent migrations or `alembic stamp`, not `repair_shared_columns()`

## Implementation

- `app/core/runtime.py` — `is_development()`
- `app/db/init_db.py` — `_allow_legacy_schema_bootstrap()`, PostgreSQL guard on `_use_alembic_migrations()`, mixin-only `repair_shared_columns()`
- `scripts/docker-entrypoint.sh` — Alembic runs before uvicorn (unchanged)
- `docker-compose.yml` — `TELITE_USE_ALEMBIC=true` by default (unchanged)

## Checklist for new schema changes

1. Add column/table in an Alembic revision under `app/db/migrations/versions/`
2. Update SQLAlchemy model(s)
3. Use inspector guard if the change may encounter drifted databases
4. Do **not** extend `repair_shared_columns()` for domain columns
5. Verify: `SELECT version_num FROM alembic_version` matches head after deploy

## Related

- Incident: `a5f009` / `media_assets.metadata_json` duplicate column (2026-06-16)
- `docs/production-readiness.md` — production env contract
