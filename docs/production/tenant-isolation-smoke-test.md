# Tenant Isolation Smoke Test

## Purpose

Verify that production deployment preserves tenant boundaries.

## Required Accounts

- Tenant A Super Admin
- Tenant B Super Admin
- Tenant A learner
- Tenant B learner

## Test Steps

1. Login as Tenant A Super Admin.
2. Capture a known Tenant A resource ID.
3. Logout.
4. Login as Tenant B Super Admin.
5. Attempt direct navigation to the Tenant A resource ID.
6. Confirm the response is `404` or `403`.
7. Confirm Tenant B dashboards do not include Tenant A users, courses, enrollments, certificates, gradebook records, or notifications.
8. Repeat with learner accounts.

## Pass Criteria

- No cross-tenant data is visible.
- Direct URL manipulation is blocked.
- API response does not leak resource existence.
- Audit logs include denied access where applicable.

