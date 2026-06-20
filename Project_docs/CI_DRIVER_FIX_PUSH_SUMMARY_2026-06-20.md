# CI Driver Fix Push Summary - 2026-06-20

## Purpose

Fix the GitHub Actions backend test failure caused by SQLAlchemy selecting the legacy `psycopg2` dialect while TELITE installs and standardizes on `psycopg` v3.

## Root Cause

The CI failure occurred during pytest fixture setup before backend tests executed:

```text
ModuleNotFoundError: No module named 'psycopg2'
```

The workflow already uses `postgresql+psycopg://` URLs, but test/runtime URL normalization did not defensively convert explicit legacy `postgresql+psycopg2://` URLs. If that driver name reached SQLAlchemy, it selected `sqlalchemy.dialects.postgresql.psycopg2` and attempted to import `psycopg2`, which is not installed.

## Pushed In This Change

- `telite-backend/app/db/engine.py`
  - Normalizes `postgresql+psycopg2://` to `postgresql+psycopg://` before creating runtime database engines.

- `telite-backend/tests/conftest.py`
  - Normalizes `TELITE_TEST_DATABASE_URL` legacy driver URLs to `psycopg` v3 for PostgreSQL test fixtures.

- `telite-backend/tests/test_rls_isolation.py`
  - Normalizes explicit RLS test database URLs to `psycopg` v3.

- `Project_docs/CI_DRIVER_FIX_PUSH_SUMMARY_2026-06-20.md`
  - Records the CI failure cause, fix scope, validation, and excluded files.

## Validation Run Locally

```text
python -m compileall app/db/engine.py tests/conftest.py tests/test_rls_isolation.py
```

Result:

```text
passed
```

Forced legacy-driver reproduction:

```text
TELITE_TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres123@localhost:55432/test_telite_backend
python -m pytest tests/test_health.py -q
```

Result:

```text
5 passed, 1 warning
```

Backend CI subset:

```text
python -m pytest tests/test_health.py tests/test_course_creation.py tests/test_task_workflow.py -q
```

Result:

```text
8 passed, 1 warning
```

## Not Pushed In This Change

The following local/untracked items were intentionally excluded because they are unrelated to the CI driver fix:

- `moodle/` untracked content
- `.github/copilot-instructions.md`
- `telite-backend/scripts/audit_onboarding.py`
- `telite-backend/scripts/audit_user_statuses.py`
- `telite-backend/scripts/fix_user_statuses.py`
- `ycopg2`

## Notes

- No `psycopg2-binary` dependency was added.
- No RLS bypass was added.
- No onboarding, assignment, theme, Moodle, or frontend logic was changed.
- The remaining warning is the existing Starlette `python_multipart` deprecation warning and is not related to this CI failure.
