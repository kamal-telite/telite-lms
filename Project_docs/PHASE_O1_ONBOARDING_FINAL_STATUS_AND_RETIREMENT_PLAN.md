# TELITE Phase O-1 Onboarding Final Status and Legacy Retirement Plan

Status: Phase O-1 onboarding consolidation is complete and closed for TELITE V1.

## Implemented Workflows

- Platform Admin creates organizations and issues first Super Admin invitations.
- Super Admin accepts invitation and activates the tenant organization.
- Admin invitation flow provisions identities through `UserProvisioningService`.
- Native manual learner enrollment is available at `POST /api/v1/enrol/manual`.
- Manual enrollment creates or reuses learner identities through `UserProvisioningService`.
- Manual enrollment creates approved `EnrollmentRequest` records and `CourseProgress` records.
- Learner course access uses `CourseProgress` and approved enrollment state.
- Assignment, learner, and player flows enforce enrollment access through native repositories.

## Source-of-Truth Audit

- `UserProvisioningService` is the identity authority.
- `UserRepository.create_user()` is called only inside `UserProvisioningService`.
- Onboarding workflows do not write directly to `user.course_progress_json`.
- `CourseProgress` is the authoritative course progress source.
- Native onboarding and manual enrollment do not depend on Moodle.
- Moodle columns and tables still exist as deprecated schema/runtime residue for later retirement, not as onboarding dependencies.

## Deprecated Workflows

The legacy `/enrol/*` routes remain registered for temporary compatibility and discovery, but are deprecated:

- `POST /enrol/self`
- `GET /enrol/requests`
- `POST /enrol/requests/{request_id}/approve`
- `POST /enrol/requests/{request_id}/reject`
- `POST /enrol/requests/approve-batch`

The payment enrollment endpoint also remains outside the native V1 manual enrollment flow:

- `POST /payment/verify-and-enrol`

These paths must not receive new feature work. New enrollment behavior belongs under `/api/v1/enrol/*`.

## Legacy Helper Functions Still Referenced

The deprecated `app/api/routes/enrolments.py` routes still reference old helper names:

- `create_self_enrollment_request`
- `list_enrollment_requests`
- `fetch_enrollment_request_by_id`
- `approve_enrollment_request`
- `reject_enrollment_request`
- `approve_enrollment_requests_batch`
- `is_category_admin_role`
- `fetch_user_by_id`

These are not used by `POST /api/v1/enrol/manual`, but they are still technical debt while the deprecated routes remain registered.

## Migration Dependencies

- Confirm no production clients call deprecated `/enrol/*` endpoints.
- Replace any remaining UI calls to legacy request approval/rejection endpoints with native repository/service-backed APIs.
- Decide whether self-enrollment is permanently removed or rebuilt as an invitation-first native workflow.
- Move analytics reads from `user.course_progress_json` to `CourseProgress`.
- Complete Moodle Release B schema retirement for deprecated Moodle columns and tables.
- Update README/runtime documentation to reflect native LMS as primary and Moodle as retired/deprecated where applicable.

## Safe Removal Criteria

Legacy `/enrol/*` routes can be removed when:

- Access logs show no traffic to the deprecated endpoints for the agreed deprecation window.
- Frontend service calls no longer reference deprecated enrollment endpoints.
- Admin pending-request UX has native v1 equivalents or is formally retired.
- Tests cover native request listing, approval/rejection if those workflows remain product requirements.
- Production data has no pending legacy self-enrollment records requiring old approval semantics.
- Release notes communicate endpoint removal to any API consumers.

## Remaining Technical Debt

- Deprecated `/enrol/*` routes still reference stale helper names and should be migrated or removed.
- `AnalyticsRepository` still reads `user.course_progress_json` as legacy fallback.
- Moodle schema residue remains in models, migrations, RLS tables, README, and some PAL/analytics terminology.
- `datetime.utcnow()` deprecation warnings remain in onboarding-related code/tests.
- Test fixtures still rely on table recreation and hardcoded IDs in some areas.

## Unresolved Risks

- Legacy `/enrol/*` routes can still fail if called directly because their helper dependencies are not part of the native service architecture.
- `EnrollmentRequest` remains category-scoped, while `CourseProgress` is course-scoped. This is acceptable for V1 but should be revisited if per-course approval metadata becomes a requirement.
- Moodle references outside onboarding may confuse future contributors until Release B cleanup is complete.

## Phase O-2 Recommendations

- Build Bulk CSV Import through `UserProvisioningService` and `EnrollmentService`.
- Route SCIM provisioning through `UserProvisioningService`.
- Route SSO first-login provisioning through `UserProvisioningService`.
- Add native v1 request-management endpoints only if pending enrollment review remains a product requirement.
- Replace legacy analytics progress reads with `CourseProgress` queries.
- Schedule Moodle Release B deletion after production data audits and rollback planning.
