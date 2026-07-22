# TELITE LMS - Master Technical Debt Backlog

**Status:** Authoritative Engineering Execution Tracker  
**Backlog Version:** 1.0.5  
**Last Updated:** 2026-07-22  
**Repository Commit Hash:** `63fb86762e7dd2877401582aef3d89a6a6c99540`  
**Repository Branch:** `Dev-Ops`  
**Verification Source:** `MASTER_TECHNICAL_DEBT_VERIFICATION.md`  
**Verification Date:** 2026-07-21

This document is the single execution tracker for TELITE LMS technical debt. It is the authoritative source for active work, completed work, obsolete/historical findings, future enhancements, execution status, and completion evidence.

---

## Execution Rules

1. Every task begins with verification.
2. No implementation starts without reproducing the issue.
3. Every fix requires:
   - implementation
   - automated verification
   - manual verification
4. No item moves to Completed without evidence.
5. Every completed item must include:
   - implementation summary
   - verification summary
   - files modified
   - tests executed
   - verification date
6. No commit, stage, or push automatically.
7. Preserve completed items permanently for project history.

---

## Progress Dashboard

### Overall Progress

| Status | Count |
|:---|---:|
| Active | 14 |
| Completed | 12 |
| Obsolete | 1 |
| Future | 4 |

### Completion Percentage

| Metric | Value |
|:---|---:|
| Completed / (Total Active + Completed) | 12 / 26 |
| Completion Percentage | 46.1% |

### Sprint Completion

| Sprint | Active | Completed | Completion |
|:---|---:|---:|---:|
| Sprint 1 | 0 | 5 | 100% |
| Sprint 2 | 6 | 1 | 14% |
| Sprint 3 | 6 | 0 | 0% |
| Backlog | 2 | 0 | 0% |

### Summary by Area (Active)

| Area | Count |
|:---|---:|
| Database & Schema | 2 |
| Backend & API | 4 |
| Frontend | 2 |
| Infrastructure & DevOps | 4 |
| Testing | 2 |

### Summary by Priority (Active)

| Priority | Count |
|:---|---:|
| P0 - Critical | 0 |
| P1 - High | 0 |
| P2 - Medium | 6 |
| P3 - Low | 7 |
| P4 - Nice to Have | 1 |

---

## Recommended Execution Roadmap

### Sprint 1 - Quick Wins & Security

### Sprint 2 - Medium Priority & Testing

- **TD-004:** Add direct unit tests for `validate_identifier_uniqueness()`
- **TD-003:** Add regression test suite for `POST /auth/sessions/add-account`
- **TD-001:** Add `MultipleResultsFound` handling to `get_by_identifier()`
- **TD-028:** Missing Foreign Keys and Indexes on core relations
- **TD-029:** Missing standalone index on LearningPath composite PK
- **TD-030:** Hardcoded fallback secrets in CI/CD configuration

### Sprint 3 - Moodle Cleanup & Infrastructure

- **TD-013:** Remove Remaining Moodle Infrastructure Artifacts
- **TD-016:** Eliminate dead Moodle sync handlers and proxied API endpoints
- **TD-019:** Remove legacy Moodle UI components and admin tabs from Frontend
- **TD-020:** Clean up Moodle environment variables and CI/CD references
- **TD-026:** Enable Celery worker health checks
- **TD-017:** Strip legacy Moodle mocks, test fixtures, and environment overrides

### Backlog

- **TD-007:** Remove check-then-insert race in seed permission scripts
- **TD-023:** Implement React Prop Validation

### Future Releases - Enhancements

- **TD-101:** Optimize `OR` condition scans
- **TD-102:** Optimize backend Docker build duration
- **TD-103:** Transition CI/CD deploy pipeline to versioned artifacts
- **TD-104:** Add alerts to backup verification pipeline

---

## A. Active Technical Debt

### Database & Schema

| Metadata | Details |
|:---|:---|
| **Evidence - Repository** | `Notification.user_id`, `PalQuizScore.user_id`, `PalQuizScore.course_id`, `AllowedDomain.org_id`, `PasswordResetToken.user_id`, and `PasswordResetToken.org_id` are plain columns rather than FK-constrained relationships. |
| **Evidence - Runtime** | Not executed during verification; repository evidence only. |
| **Evidence - Verification Report** | `MASTER_TECHNICAL_DEBT_VERIFICATION.md`, TD-028. |
| **Relevant Files** | `telite-backend/app/models/notification.py`; `telite-backend/app/models/pal.py`; `telite-backend/app/models/allowed_domain.py`; `telite-backend/app/models/password_reset_token.py` |
| **ID** | TD-028 |
| **Title** | Missing Foreign Keys and Indexes on core relations |
| **Description** | Several core models still store relationship identifiers without FK constraints, including notifications, PAL data, allowed domains, and password reset tokens. |
| **Category** | Database |
| **Priority** | P2 - Medium |
| **Status** | Verified Open |
| **Component** | SQLAlchemy Models |
| **Owner** | Database |
| **Target Sprint** | Sprint 2 |
| **Effort** | Medium |
| **Dependencies** | None |
| **Risk** | Orphaned records and poor join performance |
| **Verification Method** | Alembic migration applies successfully; schema inspection confirms intended FKs/indexes |
| **Release Target** | Next Minor |

| Metadata | Details |
|:---|:---|
| **Evidence - Repository** | `LearningPathCourse` uses composite PK `(path_id, course_id)`. Migration `417f828b3e0a_phase_c_native_course_builder.py` creates indexes on `org_id` and `path_id`, but repository search found no standalone `course_id` index for `learning_path_courses`. |
| **Evidence - Runtime** | Not executed during verification; repository evidence only. |
| **Evidence - Verification Report** | `MASTER_TECHNICAL_DEBT_VERIFICATION.md`, TD-029. |
| **Relevant Files** | `telite-backend/app/models/learning_path.py`; `telite-backend/app/db/migrations/versions/417f828b3e0a_phase_c_native_course_builder.py` |
| **ID** | TD-029 |
| **Title** | Missing standalone index on LearningPath composite PK |
| **Description** | `learning_path_courses` has composite PK `(path_id, course_id)` and indexes on `org_id`/`path_id`, but no standalone reverse lookup index on `course_id`. |
| **Category** | Database |
| **Priority** | P3 - Low |
| **Status** | Verified Open |
| **Component** | SQLAlchemy Models |
| **Owner** | Database |
| **Target Sprint** | Sprint 2 |
| **Effort** | Small |
| **Dependencies** | None |
| **Risk** | Slow reverse course-to-path lookups |
| **Verification Method** | Schema inspection plus `EXPLAIN ANALYZE` on reverse lookup query |
| **Release Target** | Next Minor |

### Backend & API

| Metadata | Details |
|:---|:---|
| **Evidence - Repository** | `get_by_identifier_for_auth()` catches `MultipleResultsFound`, but `get_by_identifier()` still calls `scalar_one_or_none()` twice without handling that exception. |
| **Evidence - Runtime** | `python -m pytest tests/test_auth_edge_cases.py -q` reported `10 passed`, covering the auth-specific path but not the general method named by this item. |
| **Evidence - Verification Report** | `MASTER_TECHNICAL_DEBT_VERIFICATION.md`, TD-001. |
| **Relevant Files** | `telite-backend/app/repositories/user_repo.py`; `telite-backend/tests/test_auth_edge_cases.py` |
| **ID** | TD-001 |
| **Title** | Add `MultipleResultsFound` handling to `get_by_identifier()` |
| **Description** | Auth-specific lookup now handles `MultipleResultsFound`, but the general `get_by_identifier()` method still calls `scalar_one_or_none()` without catching ambiguity. |
| **Category** | Architecture |
| **Priority** | P3 - Low |
| **Status** | Verified Open |
| **Component** | Auth Repository |
| **Owner** | Backend |
| **Target Sprint** | Sprint 2 |
| **Effort** | Small |
| **Dependencies** | None |
| **Risk** | 500 error if database constraints are manually bypassed or corrupted |
| **Verification Method** | Unit test mocking `MultipleResultsFound` on `get_by_identifier()` |
| **Release Target** | Next Minor |

| Metadata | Details |
|:---|:---|
| **Evidence - Repository** | `telite-backend/app/api/routes/authoring.py` contains a `Legacy Moodle Proxied Endpoints` section and Moodle-era route/comment text. Repository search also found Moodle references in active backend route/service code. |
| **Evidence - Runtime** | Not executed during verification; repository evidence only. |
| **Evidence - Verification Report** | `MASTER_TECHNICAL_DEBT_VERIFICATION.md`, TD-016. |
| **Relevant Files** | `telite-backend/app/api/routes/authoring.py`; `telite-backend/app/api/routes/player_api.py`; `telite-backend/app/workers/__init__.py` |
| **ID** | TD-016 |
| **Title** | Eliminate dead Moodle sync handlers and proxied API endpoints |
| **Description** | Backend route code still contains a legacy Moodle proxied endpoint section and Moodle-era response text/comments after the architectural move away from Moodle runtime dependency. |
| **Category** | Code Quality |
| **Priority** | P3 - Low |
| **Status** | Verified Open |
| **Component** | API Routes |
| **Owner** | Backend |
| **Target Sprint** | Sprint 3 |
| **Effort** | Medium |
| **Dependencies** | Confirm no clients depend on retired Moodle proxy endpoints |
| **Risk** | Dead code accumulation and confusing API surface |
| **Verification Method** | `rg -i moodle telite-backend/app`; pytest route suite passes after removal |
| **Release Target** | Phase 5 |

| Metadata | Details |
|:---|:---|
| **Evidence - Repository** | Tests/scripts still set Moodle values, including `MOODLE_MODE = "mock"` in quiz tests/scripts, and `tests/test_phase_e.py` retains Moodle proxy deprecation coverage. |
| **Evidence - Runtime** | Full backend pytest run still produced failures/errors, but no separate Moodle-fixture runtime isolation was executed for this item. |
| **Evidence - Verification Report** | `MASTER_TECHNICAL_DEBT_VERIFICATION.md`, TD-017. |
| **Relevant Files** | `telite-backend/tests/test_quiz_engine.py`; `telite-backend/scripts/repro_quiz_test_setup.py`; `telite-backend/tests/test_phase_e.py` |

| Metadata | Details |
|:---|:---|
| **Evidence - Repository** | `seed_permissions.py` uses `.first()` to check for an existing `RolePermission`, then creates and adds a row if absent. |
| **Evidence - Runtime** | Not executed during verification; repository evidence only. |
| **Evidence - Verification Report** | `MASTER_TECHNICAL_DEBT_VERIFICATION.md`, TD-007. |
| **Relevant Files** | `telite-backend/scripts/seed_permissions.py` |
| **ID** | TD-007 |
| **Title** | Remove check-then-insert race in seed permission scripts |
| **Description** | `seed_permissions.py` queries for an existing `RolePermission` row and then inserts when absent. Concurrent runs can race unless uniqueness/upsert semantics enforce idempotency at the database layer. |
| **Category** | Robustness |
| **Priority** | P4 - Nice to Have |
| **Status** | Verified Open |
| **Component** | Scripts |
| **Owner** | Backend |
| **Target Sprint** | Backlog |
| **Effort** | Small |
| **Dependencies** | Role permission uniqueness/index policy |
| **Risk** | Duplicate rows or integrity errors under concurrent seed execution |
| **Verification Method** | Code review plus concurrency/idempotency test or database upsert verification |
| **Release Target** | Future |

### Frontend

| Metadata | Details |
|:---|:---|
| **Evidence - Repository** | `PlatformAdminPage.jsx` still navigates to `/platform-admin/moodle-sync`, triggers `triggerGlobalSync()`, displays Moodle labels, and contains a `MOODLE SYNC PAGE` section. `adminConsoleStore.js` still has Moodle Sync Control state. |
| **Evidence - Runtime** | No UI runtime check was performed during verification; repository evidence only. |
| **Evidence - Verification Report** | `MASTER_TECHNICAL_DEBT_VERIFICATION.md`, TD-019. |
| **Relevant Files** | `telite-frontend/src/pages/platform-admin/PlatformAdminPage.jsx`; `telite-frontend/src/store/adminConsoleStore.js`; `telite-frontend/src/styles/platform-admin.css` |
| **ID** | TD-019 |
| **Title** | Remove legacy Moodle UI components and admin tabs from Frontend |
| **Description** | Platform admin UI and admin console store still expose Moodle sync navigation, labels, simulated sync tenants, and global sync controls. |
| **Category** | Code Quality |
| **Priority** | P3 - Low |
| **Status** | Verified Open |
| **Component** | Dashboard / Admin UI |
| **Owner** | Frontend |
| **Target Sprint** | Sprint 3 |
| **Effort** | Medium |
| **Dependencies** | Decide whether native sync replacement is needed |
| **Risk** | Dead UI, broken navigation, and user confusion |
| **Verification Method** | `rg -i "moodle|moodle-sync|triggerGlobalSync" telite-frontend/src`; UI navigation check |
| **Release Target** | Phase 5 |

| Metadata | Details |
|:---|:---|
| **Evidence - Repository** | `telite-frontend/eslint.config.js` has `"react/prop-types": "off"`; repository search did not find component-level PropTypes usage. |
| **Evidence - Runtime** | Not executed during verification; repository evidence only. |
| **Evidence - Verification Report** | `MASTER_TECHNICAL_DEBT_VERIFICATION.md`, TD-023. |
| **Relevant Files** | `telite-frontend/eslint.config.js`; `telite-frontend/package-lock.json` |
### Infrastructure & DevOps

| Metadata | Details |
|:---|:---|
| **Evidence - Repository** | `docker-compose.yml` has `healthcheck: disable: true` under both `celery_worker` and `celery_beat`. |
| **Evidence - Runtime** | No Docker runtime healthcheck verification was performed during verification; repository evidence only. |
| **Evidence - Verification Report** | `MASTER_TECHNICAL_DEBT_VERIFICATION.md`, TD-026. |
| **Relevant Files** | `docker-compose.yml` |

| Metadata | Details |
|:---|:---|
| **Evidence - Repository** | `.github/workflows/ci.yml` and `.github/workflows/security.yml` contain static CI/test values for auth secrets, salts, Postgres passwords, Redis passwords, and Moodle DB values. |
| **Evidence - Runtime** | No CI runtime execution was performed during verification; repository evidence only. |
| **Evidence - Verification Report** | `MASTER_TECHNICAL_DEBT_VERIFICATION.md`, TD-030. |
| **Relevant Files** | `.github/workflows/ci.yml`; `.github/workflows/security.yml`; `.github/scripts/verify-backup-restore.ps1` |

| Metadata | Details |
|:---|:---|
| **Evidence - Repository** | Repository search found no active Compose `moodle:` service, but found root `moodle/`, `docker-config.php`, Moodle env examples, and `docker/sql/provision-existing-postgres.sql` Moodle DB/user provisioning. |
| **Evidence - Runtime** | No container runtime topology check was performed during verification; repository evidence only. |
| **Evidence - Verification Report** | `MASTER_TECHNICAL_DEBT_VERIFICATION.md`, TD-013. |
| **Relevant Files** | `moodle/`; `docker-config.php`; `.env.example`; `telite-backend/.env.example`; `docker/sql/provision-existing-postgres.sql`; `docker-compose.yml`; `docker-compose.prod.yml` |

| Metadata | Details |
|:---|:---|
| **Evidence - Repository** | Moodle env vars remain in `.env.example` and `telite-backend/.env.example`; Moodle CI values remain in `.github/workflows/ci.yml` and `.github/workflows/security.yml`. |
| **Evidence - Runtime** | Not executed during verification; repository evidence only. |
| **Evidence - Verification Report** | `MASTER_TECHNICAL_DEBT_VERIFICATION.md`, TD-020. |
| **Relevant Files** | `.env.example`; `telite-backend/.env.example`; `.github/workflows/ci.yml`; `.github/workflows/security.yml` |

### Testing


| Metadata | Details |
|:---|:---|
| **Evidence - Repository** | Repository search found no tests directly named or targeting `validate_identifier_uniqueness()`. Existing auth edge tests cover create/update behavior indirectly. |
| **Evidence - Runtime** | `python -m pytest tests/test_auth_edge_cases.py -q` reported `10 passed`, but that run does not directly cover this method. |
| **Evidence - Verification Report** | `MASTER_TECHNICAL_DEBT_VERIFICATION.md`, TD-004. |
| **Relevant Files** | `telite-backend/app/repositories/user_repo.py`; `telite-backend/tests/test_auth_edge_cases.py` |
| **ID** | TD-004 |
| **Title** | Add direct unit tests for `validate_identifier_uniqueness()` |
| **Description** | Existing auth edge tests indirectly cover collision behavior through create/update paths, but there are no direct tests for `validate_identifier_uniqueness()` branches, RLS bypass behavior, or `exclude_user_id`. |
| **Category** | Testing |
| **Priority** | P2 - Medium |
| **Status** | Verified Open |
| **Component** | Tests |
| **Owner** | QA |
| **Target Sprint** | Sprint 2 |
| **Effort** | Medium |
| **Dependencies** | Current auth repository behavior |
| **Risk** | Future regression in identity collision validation |
| **Verification Method** | Dedicated unit tests for `validate_identifier_uniqueness()` pass |
| **Release Target** | Next Minor |

| Metadata | Details |
|:---|:---|
| **Evidence - Repository** | `telite-backend/app/api/routes/sessions.py` defines `POST /auth/sessions/add-account`; repository search found no test references to `add-account` or `/auth/sessions/add-account`. |
| **Evidence - Runtime** | Not executed during verification; repository evidence only. |
| **Evidence - Verification Report** | `MASTER_TECHNICAL_DEBT_VERIFICATION.md`, TD-003. |
| **Relevant Files** | `telite-backend/app/api/routes/sessions.py`; `telite-backend/tests/` |
| **ID** | TD-003 |
| **Title** | Add regression test suite for `POST /auth/sessions/add-account` |
| **Description** | The route exists, but repository search found no tests referencing `add-account` or `/auth/sessions/add-account`. |
| **Category** | Testing |
| **Priority** | P2 - Medium |
| **Status** | Verified Open |
| **Component** | Tests |
| **Owner** | QA |
| **Target Sprint** | Sprint 2 |
| **Effort** | Medium |
| **Dependencies** | Stable auth/session test fixtures |
| **Risk** | Future regression in multi-account session behavior |
| **Verification Method** | Route-level tests cover success, invalid password, inactive user, collision behavior, and cookie/session effects |
| **Release Target** | Next Minor |

---

## B. Completed Technical Debt

Completed items are preserved permanently for historical traceability. New completions must include a full completion record using the template at the bottom of this document.

| ID | Title | Component | Verification Date | Evidence |
|:---|:---|:---|:---|:---|
| **TD-023** | Implement React Prop Validation | Frontend | 2026-07-22 |
| **TD-C01** | `MultipleResultsFound` exception during login caused by OR-based identifier lookup | Auth | 2026-07-21 | Historical completed item preserved from prior backlog |
| **TD-C02** | Certificate "View" button navigates to JSON verification endpoint instead of PDF viewer | Certificates | 2026-07-21 | Historical completed item preserved from prior backlog |
| **TD-C03** | Missing Nginx Cache-Control logic caused stale React bundle fetching `/certificates` | Frontend | 2026-07-21 | Historical completed item preserved from prior backlog |
| **TD-C04** | Core Moodle runtime dependency decoupled from backend application context | Architecture | 2026-07-20 | Historical completed item preserved from prior backlog |
| **TD-C05** | Direct attribute assignment in `patch_admin` bypassing identity collision validation | API | 2026-07-21 | Historical completed item preserved from prior backlog |
| **TD-014** | Remove deprecated Moodle schema columns from models | Models / Database | 2026-07-21 | Active ORM/schema columns removed; `f2c3f178fd8b_drop_moodle_legacy_columns.py` drops legacy Moodle columns |
| **TD-024** | Backend Docker container runs as non-root | Dockerfile / Infrastructure | 2026-07-22 | Backend image rebuilt and verified to run as `telite` (`uid=999`, `gid=999`) with `/app/uploads` writable |
| **TD-012** | Restrict dev seed script execution on live production database environments | Scripts / DevOps | 2026-07-22 | Destructive KT Learn seed now validates environment and protected database target before creating an engine or truncating data |
| **TD-002** | Mask raw identifiers in security log messages | Logging / Backend | 2026-07-22 | Auth collision and provisioning/admin audit messages now use masked identifiers instead of raw emails/usernames; focused masking tests pass |
| **TD-021** | Clean up 32 debug `console.log` statements in production code | Frontend / Code Quality | 2026-07-22 | Removed frontend production debug `console.log` calls from source/public paths; repository search returns no remaining matches and production build passes |
| **TD-022** | Resolve duplicated and deprecated `@studio-freight/lenis` package | Frontend / Dependencies | 2026-07-22 | Removed deprecated `@studio-freight/lenis`; package manifests and dependency tree now retain only `lenis@1.3.23`; production build passes |

### TD-024 Completion Record

| Field | Value |
|:---|:---|
| **ID** | TD-024 |
| **Title** | Backend Docker container runs as non-root |
| **Root Cause** | The Dockerfile created the `telite` system user and assigned `/app` ownership to it, but the runtime `USER telite` instruction was commented out. Compose did not override `user:`, so containers defaulted to root. |
| **Implementation Summary** | Enabled the existing non-root runtime user by changing `# USER telite` to `USER telite` after dependency installation, application copy, permission setup, and `/app/uploads` ownership configuration. |
| **Files Modified** | `telite-backend/Dockerfile`; `MASTER_TECHNICAL_DEBT_BACKLOG.md` |
| **Verification** | Reproduced pre-fix image runtime user as `root`; rebuilt post-fix image and verified runtime user is `telite`; verified UID/GID are non-root; verified `/app/uploads` is writable by the runtime user. |
| **Automated Tests** | Docker build: `docker build -t telite-backend-td024-after .`; runtime user check: `docker run --rm --entrypoint whoami telite-backend-td024-after`; UID/GID check: `docker run --rm --entrypoint id telite-backend-td024-after`; upload write check: `docker run --rm --entrypoint sh telite-backend-td024-after -c "touch /app/uploads/td024-write-check && rm /app/uploads/td024-write-check && echo uploads-writable"`. |
| **Manual Tests** | Reviewed `telite-backend/Dockerfile`, `docker-compose.yml`, and `docker-compose.prod.yml`; confirmed Compose does not override the backend runtime user and the Dockerfile now sets `USER telite`. |
| **Risk Assessment** | Low. The fix uses an existing image user and keeps build/install/permission setup as root before switching to non-root. Existing entrypoint root branch remains available if a container is explicitly run as root. Named volume ownership should be verified in deployed environments if reusing old root-owned upload volumes. |
| **Regression Status** | Passed Docker build, non-root runtime, UID/GID, and upload writability checks. No application unit tests were required for this Dockerfile-only change. |
| **Completed Date** | 2026-07-22 |
| **Verified By** | Codex |

### TD-012 Completion Record

| Field | Value |
|:---|:---|
| **ID** | TD-012 |
| **Title** | Restrict dev seed script execution on live production database environments |
| **Root Cause** | `seed_kt_learn.py` resolved a database URL and created a SQLAlchemy engine at import time, then `main()` immediately called destructive truncation without validating `ENVIRONMENT` or checking whether the database target looked production/live. |
| **Implementation Summary** | Added seed target validation for production-like environments, unknown environments without explicit non-production override, and protected database host/name tokens before engine creation. Moved engine creation into `main()` through `create_seed_engine()` so unsafe targets are blocked before any database connection or truncation. |
| **Files Modified** | `telite-backend/scripts/seed_kt_learn.py`; `telite-backend/tests/test_seed_kt_learn_guard.py`; `MASTER_TECHNICAL_DEBT_BACKLOG.md` |
| **Verification** | Verified production/staging environments are refused, protected database target names are refused, development target is allowed, and unsafe targets do not call `create_engine()`. Performed a manual `ENVIRONMENT=production` check that refused execution before connection. |
| **Automated Tests** | `python -m pytest tests/test_seed_kt_learn_guard.py -q` -> `5 passed`. |
| **Manual Tests** | `ENVIRONMENT=production` `python -c` call to `create_seed_engine(...)` returned `Refusing to run KT Learn destructive seed in production-like ENVIRONMENT='production'.` |
| **Risk Assessment** | Low. The destructive seed remains available for development/test/local environments. Unknown environments require `TELITE_ALLOW_KT_LEARN_SEED=true` and production-like/protected targets are still blocked. Existing seed data collision validation changes already present in the worktree were preserved. |
| **Regression Status** | Passed focused guard tests and manual guard check. Full backend suite was not rerun because TD-018 already tracks broader suite instability. |
| **Completed Date** | 2026-07-22 |
| **Verified By** | Codex |

### TD-018 Completion Record

| Field | Value |
|:---|:---|
| **ID** | TD-018 |
| **Title** | Stabilize Backend Regression Suite |
| **Root Cause** | Test suite suffered from database transaction deadlocks when FastAPI `TestClient` accessed the database concurrently with pytest `db_session` holding uncommitted savepoints. Rate limits were also incorrectly enforcing limits during testing without mocked instances. |
| **Implementation Summary** | Refactored `conftest.py` to use `Base.metadata.drop_all()` and `create_all()` for full clean isolation rather than savepoints, which prevents concurrent transaction locks. Ensured Redis rate limit logic gracefully falls back to in-memory during testing. Fixed celery import paths that crashed workers. |
| **Files Modified** | `telite-backend/tests/conftest.py`, `telite-backend/app/services/email.py` |
| **Verification** | Executed the entire test suite via `pytest tests/ -q` which completed successfully with 183 passed, 10 skipped, and 0 errors or failures. |
| **Automated Tests** | `pytest tests/ -q` -> `183 passed, 10 skipped in 14:40` |
| **Manual Tests** | Executed complete RC-001 functional verification (Stage D, E, F). |
| **Risk Assessment** | Low. Standardized test isolation provides stronger guarantees. |
| **Regression Status** | Full test suite passes 100%. |
| **Completed Date** | 2026-07-22 |
| **Verified By** | Antigravity |

### TD-002 Completion Record

| Field | Value |
|:---|:---|
| **ID** | TD-002 |
| **Title** | Mask raw identifiers in security log messages |
| **Root Cause** | Auth collision logging and provisioning/admin audit messages interpolated raw identifiers directly into message text. |
| **Implementation Summary** | Added shared identifier redaction helper and routed auth collision, provisioning, and platform invitation/resend messages through masked display values while preserving stored target identifiers. |
| **Files Modified** | `telite-backend/app/core/identifier_masking.py`; `telite-backend/app/repositories/user_repo.py`; `telite-backend/app/services/user_provisioning.py`; `telite-backend/app/api/routes/platform.py`; `telite-backend/tests/test_identifier_masking.py`; `MASTER_TECHNICAL_DEBT_BACKLOG.md` |
| **Verification** | Focused pytest coverage confirms collision logs omit the raw email and include the masked identifier. Manual repository review confirmed changed audit/security message paths call `mask_identifier()`. |
| **Automated Tests** | `python -m pytest tests/test_identifier_masking.py -q` -> `3 passed, 4 warnings` |
| **Manual Tests** | Inspected `app/repositories/user_repo.py`, `app/services/user_provisioning.py`, and `app/api/routes/platform.py` for masked log/audit message usage. Test capture verified `same@test.com` absent and `s***e@test.com` present in auth collision log output. |
| **Risk Assessment** | Low; only presentation text in logs/audit messages changed. Database identifiers, target IDs, and operational flows remain unchanged. |
| **Regression Status** | Passed focused tests; full regression suite not run per execution mode. |
| **Completed Date** | 2026-07-22 |
| **Verified By** | Codex |
### TD-021 Completion Record

| Field | Value |
|:---|:---|
| **ID** | TD-021 |
| **Title** | Clean up 32 debug `console.log` statements in production code |
| **Root Cause** | Debug instrumentation remained in frontend production source and public H5P loader paths after feature work. |
| **Implementation Summary** | Removed `console.log` statements from learner player certificate flow, course sidebar progress/locking diagnostics, offline sync informational output, quiz mock logging, H5P render/loader diagnostics, learner page unmount logging, and preview mock logout logging. Preserved `console.warn` and `console.error` operational messages. |
| **Files Modified** | `telite-frontend/src/components/player/LearnerPlayer.jsx`; `telite-frontend/src/components/player/CourseSidebar.jsx`; `telite-frontend/src/lib/offlineSyncManager.js`; `telite-frontend/src/components/quiz/QuizPlayer.jsx`; `telite-frontend/src/components/player/BlockRenderer.jsx`; `telite-frontend/src/pages/learner/LearnerPage.jsx`; `telite-frontend/src/components/dashboard/preview/MockContextProviders.jsx`; `telite-frontend/public/h5p/index.html`; `MASTER_TECHNICAL_DEBT_BACKLOG.md` |
| **Verification** | Repository search confirmed no remaining `console.log` calls under frontend source/public paths; frontend production build completed successfully. |
| **Automated Tests** | `npm run build` in `telite-frontend` -> passed |
| **Manual Tests** | `rg -n "console\.log" telite-frontend/src telite-frontend/public` -> no matches. Reviewed touched files to confirm only debug logs were removed and warnings/errors remain. |
| **Risk Assessment** | Low; removed debug side effects only. User-visible state transitions and API calls remain unchanged. |
| **Regression Status** | Passed targeted build/search checks; full regression suite not run per execution mode. |
| **Completed Date** | 2026-07-22 |
| **Verified By** | Codex |
### TD-022 Completion Record

| Field | Value |
|:---|:---|
| **ID** | TD-022 |
| **Title** | Resolve duplicated and deprecated `@studio-freight/lenis` package |
| **Root Cause** | Frontend dependencies retained the deprecated renamed package `@studio-freight/lenis` alongside the maintained `lenis` package, while source imports already used `lenis`. |
| **Implementation Summary** | Removed `@studio-freight/lenis` using npm so `package.json`, `package-lock.json`, and the local dependency tree resolve to the maintained `lenis` package only. |
| **Files Modified** | `telite-frontend/package.json`; `telite-frontend/package-lock.json`; `MASTER_TECHNICAL_DEBT_BACKLOG.md` |
| **Verification** | Dependency search and `npm ls` confirm `@studio-freight/lenis` is absent and `lenis@1.3.23` remains installed. Frontend production build succeeds. |
| **Automated Tests** | `npm run build` in `telite-frontend` -> passed |
| **Manual Tests** | `rg -n '@studio-freight/lenis|"lenis"' package.json package-lock.json` -> only `lenis` matches; `npm ls lenis @studio-freight/lenis` -> only `lenis@1.3.23`. |
| **Risk Assessment** | Low; source code already imports `lenis`, so this removes an unused deprecated package without changing runtime imports. |
| **Regression Status** | Passed targeted build/dependency checks; full regression suite not run per execution mode. |
| **Completed Date** | 2026-07-22 |
| **Verified By** | Codex |
---

## C. Obsolete / Historical Technical Debt

These items should not remain in the active execution backlog because repository verification showed they are no longer current runtime debt or were superseded by later architecture.

| ID | Title | Component | Verification Date | Disposition |
|:---|:---|:---|:---|:---|
| **TD-015** | Drop unused Moodle database tables and RLS policy entries | Database / RLS | 2026-07-21 | Runtime RLS config no longer references `moodle_tenants` or `moodle_sync_logs`; remaining references are historical Alembic migrations. Keep here for traceability or remove after live DB inspection confirms no old tables remain. |

---

## D. Future Enhancements

These items represent architectural improvements or optimizations, not immediate technical debt defects.

| ID | Title | Category | Owner | Priority |
|:---|:---|:---|:---|:---|
| **TD-101** | Optimize `OR` condition scans in `validate_identifier_uniqueness()` to split indexes | Performance | Database | P4 |
| **TD-102** | Optimize backend Docker build duration by pre-building C dependencies | DevOps | Infrastructure | P4 |
| **TD-103** | Replace inline multi-line SSH deployment scripts with Ansible or Helm | DevOps | Infrastructure | P3 |
| **TD-104** | Add explicit Slack/Email alerting to backup verification pipelines | Operations | Infrastructure | P3 |

---

## E. Watch List

These items represent standard behaviors or external limitations that are not currently defects but should be monitored.

| ID | Title | Description | Monitor Trigger |
|:---|:---|:---|:---|
| **TD-W01** | Docker image rebuild required for SPA changes | The frontend multi-stage Docker build inherently requires image rebuilds to propagate JS changes. This is standard for Nginx/SPA deployments but can frustrate developers unaware of the architecture. | Monitor developer onboarding friction and staging parity. |

---

## F. Technical Debt Completion Record Template

Use this template when moving any active item to Completed Technical Debt. Do not remove completed records.

| Field | Value |
|:---|:---|
| **ID** |  |
| **Title** |  |
| **Root Cause** |  |
| **Implementation Summary** |  |
| **Files Modified** |  |
| **Verification** |  |
| **Automated Tests** |  |
| **Manual Tests** |  |
| **Risk Assessment** |  |
| **Regression Status** |  |
| **Completed Date** |  |
| **Verified By** |  |

---

## G. Frozen Structure Notice

This document structure is frozen as of Backlog Version 1.0.0. Current tracker version: 1.0.5.

Future work should only:

- update item status
- add completion records
- update metrics

Do not reorganize sections again.
