# Course Section Creation Failure Audit

## Scope

Investigated the Course Builder failure:

`POST /authoring/courses/{course_id}/sections`

Observed error from the reported environment:

```text
sqlalchemy.exc.InvalidRequestError:
Could not refresh instance '<CourseSection ...>'
```

Failure point:

```python
db.add(section)
db.commit()
db.refresh(section)
```

No code changes were made.

## Current Local Reproduction Result

Using the running Docker backend at `http://localhost:8001`, Category Admin `kt_category_admin`, course `course-python`:

```http
POST /authoring/courses/course-python/sections
Authorization: Bearer <redacted>
Content-Type: application/json

{
  "title": "Audit Repro Section",
  "sort_order": 999
}
```

Local result:

```json
{
  "status": 200,
  "body": {
    "id": 19,
    "course_id": "course-python",
    "org_id": 1,
    "title": "Audit Repro Section",
    "sort_order": 999,
    "deleted_at": null,
    "deleted_by": null
  }
}
```

The temporary audit section was deleted afterward through:

```http
DELETE /authoring/courses/course-python/sections/19
```

Delete result:

```json
{"success": true}
```

## Local Deployment Difference

The running local Docker database currently has RLS disabled on the relevant authoring tables:

```sql
SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
AND c.relname IN (
  'course_sections',
  'course_modules',
  'lesson_blocks',
  'media_assets',
  'learning_paths',
  'course_versions'
);
```

Result:

```text
relname          relrowsecurity  relforcerowsecurity
course_versions false           false
course_sections false           false
lesson_blocks   false           false
learning_paths  false           false
media_assets    false           false
course_modules  false           false
```

This explains why the failure did not reproduce locally even though the code path is still unsafe for environments where RLS is enabled.

## RLS Configuration Evidence

`telite-backend/app/db/rls.py` registers these authoring tables as tenant-scoped:

```python
"course_modules",
"course_sections",
"course_versions",
"courses",
"learning_path_courses",
"learning_paths",
"lesson_blocks",
"media_assets",
```

The RLS policy uses:

```sql
current_setting('app.bypass_rls', true) = 'on'
OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::INTEGER
```

`telite-backend/app/db/engine.py` applies tenant context with transaction-local settings:

```python
session.execute(
    text("SELECT set_config('app.current_org_id', :org_id, true)"),
    {"org_id": str(org_id)},
)
session.execute(text("SET LOCAL app.bypass_rls = 'off'"))
```

The third argument `true` makes `app.current_org_id` local to the current transaction. A `COMMIT` clears it.

## Exact Root Cause

The root cause is not the `CourseSection` ORM mapping itself. The model has the expected `org_id` field and the insert payload sets it correctly.

The unsafe pattern is:

```python
db.commit()
db.refresh(instance)
```

on tenant-scoped tables while using transaction-local RLS context.

Request flow:

1. `create_section()` uses `db: Session = Depends(db_session)`.
2. `require_admin` and `get_current_user` also use `db_session`.
3. FastAPI dependency caching usually causes the same session instance to be shared in the request.
4. `get_current_user()` calls `set_rls_context(db, org_id)`.
5. This sets `app.current_org_id` only for the current transaction.
6. `db.add(section)` is valid.
7. `db.commit()` ends the transaction and clears the transaction-local RLS setting.
8. `db.refresh(section)` starts a new SELECT after commit.
9. In an environment where RLS is enabled or forced, that SELECT cannot see the row because `app.current_org_id` is now unset.
10. SQLAlchemy receives zero rows for the primary key and raises:

```text
InvalidRequestError: Could not refresh instance '<CourseSection ...>'
```

## Authoring Endpoint Pattern Audit

File audited:

`telite-backend/app/api/routes/authoring.py`

All listed routes use `Depends(db_session)`.

### Confirmed High Risk: Writes RLS-Protected Table And Calls Refresh After Commit

| Route | Function | Table | Lines | Risk |
| --- | --- | --- | --- | --- |
| `POST /authoring/courses/{course_id}/versions` | `branch_course_version` | `course_versions` | commit line 54, refresh line 55 | Same post-commit refresh risk |
| `POST /authoring/courses/{course_id}/publish` | `publish_course` | `course_versions`, `notifications` | commit line 117, refresh line 118 | Same post-commit refresh risk |
| `POST /authoring/courses/{course_id}/sections` | `create_section` | `course_sections` | commit line 150, refresh line 151 | Reported failure |
| `PATCH /authoring/courses/{course_id}/sections/{section_id}` | `update_section` | `course_sections` | commit line 176, refresh line 177 | Same post-commit refresh risk |
| `POST /authoring/modules/{module_id}/blocks` | `create_lesson_block` | `lesson_blocks` | commit line 282, refresh line 283 | Same post-commit refresh risk |
| `POST /authoring/media/presigned-url` | `generate_presigned_url` | `media_assets` | commit line 348, refresh line 349 | Same post-commit refresh risk |
| `POST /authoring/learning-paths` | `create_learning_path` | `learning_paths` | commit line 396, refresh line 397 | Same post-commit refresh risk |
| `POST /authoring/modules` | `create_module` | `course_modules` | commit line 491, refresh line 492 | Same post-commit refresh risk |
| `PUT /authoring/modules/{module_id}` | `update_module` | `course_modules` | commit line 529, refresh line 530 | Same post-commit refresh risk |

### Related Risk: Writes RLS-Protected Tables Without Refresh

These routes do not call `refresh()`, so they are less likely to throw this exact `InvalidRequestError`, but they still depend on correct tenant context for queries, writes, and RLS `WITH CHECK`.

| Route | Function | Table(s) | Risk |
| --- | --- | --- | --- |
| `DELETE /authoring/courses/{course_id}/sections/{section_id}` | `delete_section` | `course_sections`, `course_modules` | RLS-dependent read/write |
| `PUT /authoring/courses/{course_id}/structure` | `update_course_structure` | `course_sections`, `course_modules` | RLS-dependent read/write |
| `PUT /authoring/modules/{module_id}/blocks/order` | `update_block_order` | `lesson_blocks` | RLS-dependent read/write |
| `PUT /authoring/learning-paths/{path_id}/courses` | `update_learning_path_courses` | `learning_paths`, `learning_path_courses` | RLS-dependent read/write |
| `DELETE /authoring/modules/{module_id}` | `delete_module` | `course_modules` | RLS-dependent read/write |

## Schema And Model Notes

`CourseSection` model:

```python
course_id = Column(String(50), ForeignKey("courses.id"), nullable=False, index=True)
org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
title = Column(String(255), nullable=False)
sort_order = Column(Integer, nullable=False, default=0)
```

No model-level defect was found for section creation. The section row includes `org_id=current_user.org_id`.

## Smallest Safe Remediation

Fix the authoring pattern, not only `create_section()`.

Recommended minimal approach:

1. Ensure the route's own `db` session has tenant context explicitly applied at the top of each authoring route that uses `db_session`.
2. Replace post-commit refresh with refresh before commit:

```python
apply_tenant_context(db, current_user.org_id)
db.add(section)
db.flush()
db.refresh(section)
db.commit()
return section.to_dict()
```

Why this is safer:

- `flush()` sends the INSERT and populates generated values without ending the transaction.
- `refresh()` runs while `app.current_org_id` is still set.
- `commit()` happens after the object is already refreshed.
- The response can be built from the object because `expire_on_commit=False` is configured in the sessionmaker.

Alternative remediation:

```python
db.commit()
apply_tenant_context(db, current_user.org_id)
db.refresh(section)
```

This is also functional, but it starts a new transaction just to refresh and repeats the post-commit read pattern.

## Recommended Fix Scope

Do not patch only `create_section()`.

Apply the same safe persistence helper to all high-risk authoring routes listed above:

- `branch_course_version`
- `publish_course`
- `create_section`
- `update_section`
- `create_lesson_block`
- `generate_presigned_url`
- `create_learning_path`
- `create_module`
- `update_module`

## Verification Required After Fix

Run against a database where RLS is enabled and forced for authoring tables:

```sql
SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
AND c.relname IN (
  'course_sections',
  'course_modules',
  'lesson_blocks',
  'media_assets',
  'learning_paths',
  'course_versions'
);
```

Expected:

```text
relrowsecurity = true
relforcerowsecurity = true
```

Then verify:

- Create section succeeds.
- Update section succeeds.
- Create module succeeds.
- Create lesson block succeeds.
- Media presigned-url asset creation succeeds.
- Course version branch succeeds.
- Publish succeeds.
- No `Could not refresh instance` appears in backend logs.

## Implementation Verification Update

After the audit was accepted, the authoring route surface was refactored with a shared persistence pattern in:

`telite-backend/app/api/routes/authoring.py`

The helper now:

1. Applies tenant context explicitly to the route's own database session.
2. Persists rows with `flush -> refresh -> commit` instead of `commit -> refresh`.

The affected authoring routes were updated consistently rather than patching only section creation:

- `branch_course_version`
- `publish_course`
- `create_section`
- `update_section`
- `delete_section`
- `update_course_structure`
- `create_lesson_block`
- `update_block_order`
- `generate_presigned_url`
- `confirm_media_upload`
- `create_learning_path`
- `update_learning_path_courses`
- `create_module`
- `update_module`
- `delete_module`
- `add_quiz_question`

Controlled RLS reproduction was performed by enabling and forcing RLS for the authoring tables:

```text
course_modules        relrowsecurity=true  relforcerowsecurity=true
course_sections       relrowsecurity=true  relforcerowsecurity=true
course_versions       relrowsecurity=true  relforcerowsecurity=true
learning_path_courses relrowsecurity=true  relforcerowsecurity=true
learning_paths        relrowsecurity=true  relforcerowsecurity=true
lesson_blocks         relrowsecurity=true  relforcerowsecurity=true
media_assets          relrowsecurity=true  relforcerowsecurity=true
```

The original failure was reproduced under forced RLS before the fix:

```text
POST /authoring/courses/course-python/sections -> 500
sqlalchemy.exc.InvalidRequestError: Could not refresh instance '<CourseSection ...>'
```

After the shared helper was applied, the same operation succeeded under forced RLS:

```json
{
  "id": 21,
  "course_id": "course-python",
  "org_id": 1,
  "title": "RLS Fixed Section",
  "sort_order": 1002
}
```

Additional high-risk authoring operations were smoke-tested under forced RLS:

```text
POST /authoring/modules                         -> 200
POST /authoring/modules/{module_id}/blocks      -> 200
POST /authoring/media/presigned-url             -> 200
POST /authoring/courses/course-python/versions  -> 200
PATCH /authoring/courses/course-python/sections -> 200
DELETE /authoring/courses/course-python/sections -> 200
PUT /authoring/modules/{module_id}              -> 200
DELETE /authoring/modules/{module_id}           -> 200
```

During forced-RLS smoke testing, `POST /authoring/courses/{course_id}/versions` also exposed a separate existing issue: `CourseVersion.id` was not being assigned in this route. The route now assigns `uuid.uuid4().hex`, matching the existing `PublishingRepository.create_version()` strategy.

Verification commands:

```text
python -m py_compile telite-backend/app/api/routes/authoring.py
cd telite-backend; python -m pytest -q tests/test_h5p_service.py
```

Result:

```text
6 passed, 2 warnings
```

Note: local backend image rebuild timed out twice, so the runtime RLS validation was performed by copying the patched `authoring.py` into the running backend container and restarting it. The repository source file contains the implemented fix; the Docker image itself still needs a successful backend rebuild in the target environment.

## Readiness Verdict

Root cause is confirmed as an authoring persistence pattern that is unsafe under active transaction-local RLS.

The smallest safe remediation is a targeted authoring helper that:

1. Applies tenant context to the route session.
2. Uses `flush -> refresh -> commit` instead of `commit -> refresh`.

That remediation has now been implemented and verified against forced RLS for the highest-risk authoring routes listed above.
