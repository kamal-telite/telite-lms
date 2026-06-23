# Production Deployment Runbook

## Purpose

Deploy Telite LMS using immutable backend and frontend image references.

## Required GitHub Environment Secrets

Configure these secrets for both `staging` and `production` GitHub Environments:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_PATH`
- `DEPLOY_SSH_PRIVATE_KEY`

Production should require manual approval in GitHub Environments.

## Deployment Workflow

Use:

```text
.github/workflows/deploy.yml
```

Required inputs:

- `environment`: `staging` or `production`
- `backend_image`: immutable backend tag or digest
- `frontend_image`: immutable frontend tag or digest
- `app_url`: public HTTPS URL

## Deployment Rules

1. Deploy staging first.
2. Run smoke checks.
3. Promote the same image references to production.
4. Do not rebuild between staging and production.
5. Record backend and frontend image references in the release notes.

## Post-Deploy Verification

Check:

```bash
curl -fsS https://<app-url>/api/health/readiness
curl -fsS https://<app-url>/api/metrics
```

Then verify:

- Login works.
- Admin dashboard loads.
- Learner dashboard loads.
- Tenant isolation smoke test passes.
- Manual enrollment smoke test passes.

## Failure Handling

If readiness fails:

1. Do not retry blindly.
2. Capture container logs.
3. Check database migration logs.
4. Roll back to the previous known-good image references.

