# TELITE LMS - Master Technical Debt Verification

**Verification Date:** 2026-07-21  
**Source Backlog Reviewed:** `C:\Users\kamal\Downloads\MASTER_TECHNICAL_DEBT_BACKLOG_newly_UPdated.md`  
**Scope:** Verification-only audit of every item listed under Active Technical Debt. No code or backlog edits were made.

## Executive Summary

| Classification | Count |
|:---|---:|
| Verified Open | 20 |
| Already Fixed | 1 |
| Obsolete | 1 |
| Needs Manual Decision | 0 |

Key corrections:

- TD-018 is still open, but the backlog title is stale. The current observed full backend run is not "21 failing tests"; it produced `44 failed, 109 passed, 10 skipped, 10 errors` before command timeout/teardown noise.
- Moodle removal is only partially complete. Docker Compose no longer defines a `moodle:` service, and Moodle legacy ORM columns have a cleanup migration, but Moodle config/env/CI/frontend/backend route references still exist.
- TD-014 should move to Completed Technical Debt.
- TD-015 should be removed or rewritten: current runtime RLS config no longer references Moodle tables, and remaining Moodle table/RLS references are historical migrations.

## Verification Notes

- `python -m pytest -q` was run from `telite-backend`. It reached the pytest summary but the command timed out after teardown/logging noise. Reported summary: `44 failed, 109 passed, 10 skipped, 10 errors in 736.89s`.
- `python -m pytest tests/test_auth_edge_cases.py -q` reported `10 passed`, but the command process still timed out after pytest cache permission warnings.
- Existing uncommitted user/repo changes were present before this report was created, including auth/repository/seed changes and `telite-backend/tests/test_auth_edge_cases.py`.

## Item-by-Item Verification

### TD-012 - Restrict dev seed script execution on live production database environments

**Status:** Verified Open  
**Evidence:** `telite-backend/scripts/seed_kt_learn.py` resolves `TELITE_MIGRATION_DATABASE_URL`, `TELITE_DATABASE_URL`, or derived Postgres env values, then creates an engine without checking `ENVIRONMENT`, `ENV`, hostname, database name, or an explicit destructive confirmation. The script executes destructive cleanup via `TRUNCATE TABLE organizations CASCADE` and iterates `DELETE_ORDER` with `TRUNCATE TABLE {table} CASCADE`.  
**Recommendation:** Keep active. Add a production/live database guard before destructive operations.

### TD-028 - Missing Foreign Keys and Indexes on core relations

**Status:** Verified Open  
**Evidence:** Several core models still store relationship identifiers without FK constraints. Examples: `Notification.user_id` is a plain indexed string in `telite-backend/app/models/notification.py`; `PalQuizScore.user_id` and `PalQuizScore.course_id` are plain columns in `telite-backend/app/models/pal.py`; `AllowedDomain.org_id` is plain nullable integer in `telite-backend/app/models/allowed_domain.py`; `PasswordResetToken.user_id` and `PasswordResetToken.org_id` are plain columns in `telite-backend/app/models/password_reset_token.py`.  
**Recommendation:** Keep active. Define the intended FK/index policy and add migrations.

### TD-029 - Missing standalone index on LearningPath composite PK

**Status:** Verified Open  
**Evidence:** `LearningPathCourse` has composite primary key `(path_id, course_id)` in `telite-backend/app/models/learning_path.py`, and migration `417f828b3e0a_phase_c_native_course_builder.py` creates indexes only on `org_id` and `path_id` for `learning_path_courses`; repository search found no standalone `course_id` index for this table.  
**Recommendation:** Keep active. Add a standalone `course_id` index if reverse course-to-path lookup is a supported query.

### TD-014 - Remove deprecated Moodle schema columns from models

**Status:** Already Fixed  
**Evidence:** Repository search across `telite-backend/app/models`, active repositories, services, DB helpers, and API code found no active model columns for `moodle_id`, `moodle_course_id`, `moodle_cmid`, `moodle_category_id`, `moodle_tenant_key`, or `synced_from_moodle`. Migration `f2c3f178fd8b_drop_moodle_legacy_columns.py` explicitly drops these columns. Remaining matches are historical migrations/downgrades or comments.  
**Recommendation:** Move to Completed Technical Debt.

### TD-015 - Drop unused Moodle database tables and RLS policy entries

**Status:** Obsolete  
**Evidence:** Current runtime RLS table list in `telite-backend/app/db/rls.py` does not include `moodle_tenants` or `moodle_sync_logs`. Remaining references are in older Alembic migrations such as `001_phase3_initial.py`, `a5f006_classify_remaining_tables.py`, and `a5f007_rewrite_rls_policies_safe_context.py`, which are migration history rather than current runtime RLS configuration.  
**Recommendation:** Remove this item or rewrite it as a migration-history cleanup decision. Do not keep it as active runtime technical debt unless live database inspection proves those tables still exist.

### TD-001 - Add `MultipleResultsFound` handling to `get_by_identifier()`

**Status:** Verified Open  
**Evidence:** `telite-backend/app/repositories/user_repo.py` has `MultipleResultsFound` handling in `get_by_identifier_for_auth()`, and `tests/test_auth_edge_cases.py` covers that path. However, the general `get_by_identifier()` method still calls `scalar_one_or_none()` twice without catching `MultipleResultsFound`.  
**Recommendation:** Keep active as written, or rename it if the intended scope was only authentication. The auth-specific collision work appears complete.

### TD-002 - Mask raw identifiers in security log messages

**Status:** Verified Open  
**Evidence:** `get_by_identifier_for_auth()` logs `CRITICAL SECURITY EVENT: MultipleResultsFound triggered for auth identifier '{ident}'`, exposing the raw normalized identifier. Other operational messages also include raw email addresses, such as invitation/provisioning messages in `telite-backend/app/services/user_provisioning.py`.  
**Recommendation:** Keep active. Mask identifiers before logging security-sensitive authentication/provisioning events.

### TD-016 - Eliminate dead Moodle sync handlers and proxied API endpoints

**Status:** Verified Open  
**Evidence:** `telite-backend/app/api/routes/authoring.py` still contains a `Legacy Moodle Proxied Endpoints` section and Moodle-related response text/comments. `rg -i moodle telite-backend/app` also finds retained Moodle references in active route/service code, including `authoring.py`, `player_api.py`, and worker package comments.  
**Recommendation:** Keep active. Remove or rename remaining Moodle proxy/sync-era backend routes and comments after confirming no clients depend on them.

### TD-017 - Strip legacy Moodle mocks, test fixtures, and environment overrides

**Status:** Verified Open  
**Evidence:** Tests/scripts still set Moodle test environment values, including `telite-backend/tests/test_quiz_engine.py` setting `MOODLE_MODE = "mock"` and `telite-backend/scripts/repro_quiz_test_setup.py` setting `MOODLE_MODE`. `tests/test_phase_e.py` still includes Moodle proxy deprecation coverage.  
**Recommendation:** Keep active. Remove or reframe legacy Moodle test scaffolding once the architecture is fully native.

### TD-007 - TOCTOU race condition in seed scripts

**Status:** Verified Open  
**Evidence:** `telite-backend/scripts/seed_permissions.py` performs check-then-insert logic: it queries `RolePermission` with `.first()` and then adds a row if none exists. That is still a TOCTOU pattern if the script can run concurrently. The backlog title says "raw SQL INSERT", but the currently visible race is ORM check-then-add.  
**Recommendation:** Keep active but update the wording. Use database-enforced uniqueness plus idempotent upsert behavior.

### TD-021 - Clean up 31 debug `console.log` statements

**Status:** Verified Open  
**Evidence:** `rg --count "console\.log" telite-frontend` found 32 current matches, including `LearnerPlayer.jsx` with 11, `CourseSidebar.jsx` with 10, `offlineSyncManager.js` with 4, and additional matches in quiz/player/H5P files.  
**Recommendation:** Keep active. Update count from 31 to 32 unless some are intentionally development-only.

### TD-022 - Resolve duplicated and deprecated `@studio-freight/lenis` package

**Status:** Verified Open  
**Evidence:** `telite-frontend/package.json` includes both `@studio-freight/lenis` and `lenis`. `npm ls lenis @studio-freight/lenis` reports both `@studio-freight/lenis@1.0.42` and `lenis@1.3.23`; `package-lock.json` records the deprecation warning for `@studio-freight/lenis`.  
**Recommendation:** Keep active. Remove the deprecated package and normalize imports.

### TD-019 - Remove legacy Moodle UI components and admin tabs from Frontend

**Status:** Verified Open  
**Evidence:** `telite-frontend/src/pages/platform-admin/PlatformAdminPage.jsx` still navigates to `/platform-admin/moodle-sync`, triggers `triggerGlobalSync()`, displays "Sync Moodle", "Moodle Gateway", and contains a `MOODLE SYNC PAGE` section. `telite-frontend/src/store/adminConsoleStore.js` still has "Moodle Sync Control Page States" and simulated sync tenants.  
**Recommendation:** Keep active. Remove dead admin UI/state or rebrand it to a native sync concept if still needed.

### TD-023 - Implement React Prop Validation

**Status:** Verified Open  
**Evidence:** `telite-frontend/eslint.config.js` has `"react/prop-types": "off"`. `prop-types` exists only as a transitive package in `package-lock.json`; repository search did not find component-level PropTypes usage.  
**Recommendation:** Keep active unless the project chooses TypeScript or another validation strategy instead.

### TD-024 - Backend Docker container runs as `root`

**Status:** Verified Open  
**Evidence:** `telite-backend/Dockerfile` creates a `telite` user but leaves `USER telite` commented out. Containers built from this Dockerfile therefore default to root unless overridden externally.  
**Recommendation:** Keep active. Enable the non-root user and verify write permissions for uploads/runtime paths.

### TD-026 - Disabled Celery worker healthchecks

**Status:** Verified Open  
**Evidence:** `docker-compose.yml` has `healthcheck: disable: true` under both `celery_worker` and `celery_beat`.  
**Recommendation:** Keep active. Add meaningful Celery worker/beat healthchecks and verify `docker compose ps` health state.

### TD-030 - Hardcoded fallback secrets in CI/CD configuration

**Status:** Verified Open  
**Evidence:** `.github/workflows/ci.yml` and `.github/workflows/security.yml` contain CI fallback/static values such as `TELITE_AUTH_SECRET: ci-test-auth-secret-not-for-production-use`, `ci-production-secret-with-more-than-32-characters`, `TELITE_PASSWORD_SALT: ci-production-salt-value`, and static Postgres/Redis passwords.  
**Recommendation:** Keep active. Replace misleading production-like fallback names with scoped CI-only generated values or documented test-only secrets.

### TD-013 - Decommission Moodle container and Docker infrastructure configurations

**Status:** Verified Open  
**Evidence:** `rg "moodle:" docker-compose.yml docker-compose.prod.yml docker` found no active Compose `moodle:` service, so container topology is partly decommissioned. However, Moodle infrastructure remains: root `moodle/` directory exists, `docker-config.php` is a Moodle config file, `.env.example` exposes Moodle DB/runtime variables, and `docker/sql/provision-existing-postgres.sql` still creates/owns/grants a `moodle` database and `moodleuser`.  
**Recommendation:** Keep active, but narrow it to remaining Moodle infra/config artifacts rather than Compose service removal.

### TD-020 - Clean up Moodle environment variables and CI/CD references

**Status:** Verified Open  
**Evidence:** Moodle env vars remain in `.env.example` and `telite-backend/.env.example`, including `MOODLE_MODE`, `MOODLE_URL`, `MOODLE_TOKEN`, role IDs, and sync rate limits. CI still includes Moodle values in `.github/workflows/ci.yml` and `.github/workflows/security.yml`.  
**Recommendation:** Keep active. Remove Moodle env/CI references after deciding whether any docs-only compatibility story remains.

### TD-018 - Fix 21 pre-existing integration/unit test failures

**Status:** Verified Open  
**Evidence:** Full backend pytest run from `telite-backend` reported `44 failed, 109 passed, 10 skipped, 10 errors in 736.89s`. It also showed errors unrelated to application assertions, including missing fixture `seed_data` in `tests/api/test_bulk_e2e_verification.py` and Windows temp-dir permission errors under `C:\Users\kamal\AppData\Local\Temp\pytest-of-kamal`.  
**Recommendation:** Keep active but update the title/count. Split environment/test-harness errors from actual failing assertions.

### TD-004 - Add direct unit tests for `validate_identifier_uniqueness()`

**Status:** Verified Open  
**Evidence:** Repository search found no test directly named or targeting `validate_identifier_uniqueness()`. `tests/test_auth_edge_cases.py` indirectly covers collision behavior through `create_user()` and `update()`, but it does not directly exercise the method's branches, RLS bypass behavior, or `exclude_user_id` cases as isolated unit tests.  
**Recommendation:** Keep active. Add direct repository unit tests for the method.

### TD-003 - Add regression test suite for `POST /auth/sessions/add-account`

**Status:** Verified Open  
**Evidence:** The route exists in `telite-backend/app/api/routes/sessions.py`, but repository search found no tests referencing `add-account` or `/auth/sessions/add-account`.  
**Recommendation:** Keep active. Add route-level regression tests for success, invalid password, inactive user, collision behavior, and cookie/session effects.

## Moodle Re-Verification Summary

| ID | Status | Summary |
|:---|:---|:---|
| TD-013 | Verified Open | Compose service is gone, but Moodle directory/config/env/database provisioning remain. |
| TD-014 | Already Fixed | Active ORM/schema columns removed; cleanup migration exists. |
| TD-015 | Obsolete | Runtime RLS no longer references Moodle tables; remaining references are historical migrations. |
| TD-016 | Verified Open | Backend authoring route still contains legacy Moodle proxied endpoint section/text. |
| TD-019 | Verified Open | Platform admin UI/store still contains Moodle sync flows and labels. |
| TD-020 | Verified Open | Moodle env vars and CI values remain. |

## Recommended Backlog Actions

- Move TD-014 to Completed Technical Debt.
- Remove or rewrite TD-015; current evidence does not support keeping it as active runtime debt.
- Update TD-018 title/count to reflect the current failing suite state.
- Update TD-021 count from 31 to 32 if all current `console.log` matches are in scope.
- Refine TD-013 wording to focus on remaining Moodle artifacts rather than Compose container removal.
- Refine TD-007 wording from "raw SQL INSERT" to "seed script check-then-insert/upsert race" unless another raw SQL race is identified.
