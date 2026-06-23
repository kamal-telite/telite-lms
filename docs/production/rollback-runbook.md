# Production Rollback Runbook

## Purpose

Restore Telite LMS to the previous known-good backend and frontend images.

## Required Information

- Previous backend image digest or immutable tag.
- Previous frontend image digest or immutable tag.
- Current failed deployment timestamp.
- Current failed workflow run URL.

## Rollback Procedure

Run the Deploy workflow with:

- `environment`: affected environment
- `backend_image`: previous backend image
- `frontend_image`: previous frontend image
- `app_url`: affected environment URL

The rollback must deploy existing images only. Do not rebuild.

## Verification

After rollback:

```bash
curl -fsS https://<app-url>/api/health/readiness
```

Verify:

- API readiness is healthy.
- Frontend loads.
- Login works.
- No new 5xx spike appears in logs.
- Database migrations are compatible with the previous image.

## Database Rollback

Database rollback is not automatic.

If a deployment included destructive or incompatible migrations:

1. Stop application writers.
2. Restore from verified backup.
3. Restart services.
4. Run tenant isolation and login smoke checks.

