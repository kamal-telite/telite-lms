# Telite LMS Production Readiness

This document is the deployment contract for Telite LMS. It covers the checks that must pass before a production release and the operational baseline expected after release.

## Release Gates

- Backend release-tooling lint passes in CI.
- Backend smoke/unit tests pass in CI; live API/RLS tests remain opt-in.
- Frontend lint passes with `npm run lint:ci`.
- Frontend has no critical npm audit findings.
- Frontend build passes with `npm run build`.
- Docker production overlay is valid with `docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet`.
- Backend and frontend production images build successfully.
- `python -m scripts.validate_production_env` passes against the target environment.

## Hardening Backlog

The backend currently has existing full-repository Ruff debt. Treat `ruff check app tests scripts` as a required cleanup milestone before enforcing it as a blocking enterprise gate.

The frontend currently has npm audit findings below the critical threshold. Upgrade `axios`, `react-router-dom`, and the Vite/esbuild chain in a dedicated dependency-hardening pass.

## Required Production Settings

Set these values through the deployment platform secret store, not in Git:

- `ENVIRONMENT=production`
- `TELITE_AUTH_SECRET`
- `TELITE_PASSWORD_SALT`
- `POSTGRES_PASSWORD`
- `TELITE_POSTGRES_DB`
- `TELITE_POSTGRES_USER`
- `TELITE_POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `TELITE_APP_URL`
- `TELITE_CORS_ORIGINS`
- `COOKIE_SECURE=true`
- `COOKIE_SAMESITE=strict`

When Moodle live integration is enabled, also set `MOODLE_TOKEN` and the production Moodle URL values. When R2 media storage is enabled, set `R2_ENDPOINT`, `R2_ACCESS_KEY`, `R2_SECRET_KEY`, and `R2_BUCKET`.

## CI/CD Layout

- `.github/workflows/ci.yml` validates backend, frontend, production environment contracts, and Docker builds on pull requests and branch pushes.
- `.github/workflows/container-release.yml` publishes backend and frontend images to GHCR on version tags or manual dispatch.
- Version tags should use `vMAJOR.MINOR.PATCH`, for example `v1.4.0`.

## Deployment Flow

1. Merge only after CI passes.
2. Create a version tag from the release commit.
3. Wait for the container release workflow to publish images.
4. Deploy the tagged images to staging.
5. Run smoke checks:
   - `GET /health/liveness`
   - `GET /health/readiness`
   - Login flow for one platform admin
   - One tenant learner course list
6. Promote the same image tags to production.
7. Watch application logs, error rate, and readiness for at least one release window.

## Runtime Expectations

- Backend runs behind HTTPS and exposes `/health/liveness`, `/health/readiness`, and `/metrics`.
- Frontend is served by Nginx and proxies API paths to the backend.
- PostgreSQL and Redis are internal-only in production.
- Database schema changes are applied by Alembic during backend startup.
- Uploads must use persistent volume storage or R2-compatible object storage.

## Rollback

Rollback by redeploying the previous backend and frontend image tags. If a release includes database migrations, verify whether the migration is backward compatible before rolling back application images.
