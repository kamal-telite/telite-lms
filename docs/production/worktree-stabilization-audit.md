# Production Worktree Stabilization Audit

Date: 2026-06-23

## Purpose

Before production CI/CD changes are merged, active product work must be separated from DevOps hardening work.

## Current Risk

The repository currently contains many modified and untracked files across:

- backend routes
- backend services
- models
- migrations
- frontend pages
- frontend utilities
- tests
- local verification scripts
- local audit artifacts

Production hardening must avoid reverting or overwriting active product work.

## Stabilization Rules

1. Do not revert files that are already modified.
2. Keep DevOps changes isolated to:
   - `.github/`
   - `docs/production/`
   - `docker/observability/`
   - Docker/Compose config when required
3. Do not stage local logs or scratch scripts.
4. Do not move ignored `Project_docs/` artifacts into Git unless they are promoted to durable docs.
5. Treat `.env`, backups, logs, dumps, and generated reports as local-only.

## Required Checks

Run before production-hardening commit:

```bash
git status --short
git diff -- .github docs/production docker/observability docker-compose.yml docker-compose.prod.yml
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
```

## Exit Criteria

The worktree is ready for production-hardening review when:

- DevOps changes are reviewable independently.
- No feature implementation files are accidentally included.
- No secrets or local backups are included.
- CI workflow syntax validates.
- Compose production overlay validates.

