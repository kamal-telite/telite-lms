# TELITE Native Manual Enrollment Workflow

Status: Implemented and verified for TELITE V1 / Phase O-1.

This document is part of the authoritative native onboarding architecture. Manual enrollment is an admin-authorized provisioning path under the same Phase O-1 constraints as invitation onboarding: `UserProvisioningService` owns identity creation, tenant scope is derived from authenticated context, and `CourseProgress` is the learner progress source of truth.

## Architecture Summary

Manual learner enrollment is now a native Phase O-1 workflow:

```text
Category Admin UI
-> POST /api/v1/enrol/manual
-> EnrollmentService.manual_enroll()
-> UserProvisioningService.provision_manual_learner()
-> EnrollmentRepository
-> ProgressRepository / CourseProgress
-> AuditRepository
```

`UserProvisioningService` remains the sole identity authority. Route handlers and `EnrollmentService` do not call `UserRepository.create_user()` directly.

Authoritative rules:

- Organization comes from the authenticated user context.
- Category authority comes from the authenticated user and selected courses.
- `category_slug` in the request is tolerated only for backward-compatible payload shape and is not trusted for authorization.
- `EnrollmentRequest(status='approved')` records category-level enrollment approval.
- `CourseProgress` records course-level learner progress and prevents duplicate course enrollment effects.
- Manual enrollment does not use Moodle, pending verification, or self-signup code.

## API Contract

`POST /api/v1/enrol/manual`

Request:

```json
{
  "full_name": "Learner Name",
  "email": "learner@example.com",
  "course_ids": ["course-123"],
  "enrollment_type": "manual",
  "note": "optional admin note"
}
```

`category_slug` may still be sent by older frontend payloads, but the backend ignores it for authorization. Organization and category scope are derived from the authenticated user and selected courses.

Response:

```json
{
  "status": "ok",
  "user": {
    "id": "user-...",
    "email": "learner@example.com",
    "full_name": "Learner Name",
    "role": "learner",
    "org_id": 1,
    "category_scope": "backend-development"
  },
  "request": {
    "id": "enrol-...",
    "status": "approved"
  },
  "category_slug": "backend-development",
  "enrolled_course_ids": ["course-123"],
  "skipped_course_ids": []
}
```

## Migration Impact

- Frontend manual enrollment now calls `/api/v1/enrol/manual`.
- Existing legacy `/enrol/*` routes were not removed in this change.
- No Moodle, pending verification, or self-signup workflow was introduced.
- No schema migration is required.

## Deprecated Legacy Routes

The following legacy routes remain registered but are deprecated:

- `POST /enrol/self`
- `GET /enrol/requests`
- `POST /enrol/requests/{request_id}/approve`
- `POST /enrol/requests/{request_id}/reject`
- `POST /enrol/requests/approve-batch`
- `POST /payment/verify-and-enrol`

These routes must not receive new feature work. Future enrollment work should target `/api/v1/enrol/*` and use service/repository boundaries.

## Security Review

- Allowed actors: `platform_admin`, `super_admin`, `category_admin`.
- `org_id` always comes from the authenticated token context.
- `category_slug` and organization identifiers from the request are not trusted.
- Category Admins can only enroll into `current_user.category_scope`.
- Every selected course must belong to the authenticated org and one allowed category.
- Courses must be `active` or `published`.
- Existing learner emails from another org are rejected.
- Existing non-learner accounts are not downgraded or reused as learners.
- Duplicate course progress records are skipped instead of failing the request.
- The authenticated DB session RLS context is used; no manual enrollment bypasses RLS.

## Manual Verification Checklist

- Category Admin opens category dashboard and clicks Add Learner.
- Category Admin enrolls a new learner into one published course.
- Learner user is created with role `learner`.
- `EnrollmentRequest` is created or reused with `status=approved`.
- `CourseProgress` is created for the selected course.
- Repeating the same enrollment returns success and lists the course under `skipped_course_ids`.
- Category Admin cannot enroll a learner into another category's course.
- Super Admin can enroll into a course in their organization.
- Cross-tenant course IDs fail.
- Existing learner in the same org is reused.
- Existing email in another org fails.
- Existing admin email in same org fails and is not downgraded.
- Learner logs in and can see the enrolled course.
- Audit log records `learner.manual_provisioned` for new learners and `enrollment.manual`.
