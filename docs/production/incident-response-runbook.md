# Incident Response Runbook

## Severity Levels

| Severity | Description | Examples |
| --- | --- | --- |
| SEV1 | Platform unavailable or tenant data exposure suspected | API down, database down, RLS bypass |
| SEV2 | Major workflow broken | login failure, enrollment failure, certificate issuance failure |
| SEV3 | Partial degradation | slow dashboard, delayed notifications |
| SEV4 | Low-impact issue | copy, styling, isolated support issue |

## First 10 Minutes

1. Confirm incident scope.
2. Assign incident owner.
3. Capture current deployment image references.
4. Check readiness:

```bash
curl -fsS https://<app-url>/health/readiness
```

5. Check recent deployment history.
6. Check backend logs using request IDs.
7. Check database and Redis health.
8. Decide rollback versus hotfix.

## Data Isolation Incident

If cross-tenant data exposure is suspected:

1. Treat as SEV1.
2. Stop risky write paths if needed.
3. Preserve logs.
4. Identify affected org IDs.
5. Run RLS verification checks.
6. Do not run cleanup scripts until evidence is preserved.

## Deployment Regression

If the incident began after deployment:

1. Roll back to previous known-good image references.
2. Run smoke checks.
3. Keep failed image references for forensic analysis.

## Communication

Minimum update cadence:

- SEV1: every 15 minutes
- SEV2: every 30 minutes
- SEV3: every 2 hours

## Post-Incident Review

Record:

- timeline
- root cause
- affected tenants
- data impact
- detection gap
- prevention action
- owner and deadline

