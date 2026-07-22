# TELITE LMS - Course Edge Case Matrix

This document outlines the expected versus actual behavior of course-related edge cases in the TELITE LMS, particularly highlighting the current constraint issues (RC-003).

## 1. Edge Case Matrix

| Edge Case | Current Behavior (Verified from Code) | Expected / Target Behavior | Impact / Status |
| :--- | :--- | :--- | :--- |
| **Same course name (Same Org)** | **Fails**. `slugify(name)` produces identical slug. DB throws `IntegrityError` due to global `slug` `UNIQUE` constraint. | Application should append a suffix (e.g., `-1`, `-2`) or use a composite key to allow duplicate names or handle slugs gracefully. | 🔴 Bug / UX Issue |
| **Same course name (Different Org)** | **Fails (RC-003)**. `slug` is unique across the entire `courses` table. Org B cannot create a course if Org A has one with the same name. | **Success**. Slugs must be scoped to `org_id` (or include org prefix) to maintain strict multi-tenant isolation. | 🔴 Critical Bug (RC-003) |
| **Different Tier / Different Category** | **Fails** if the course name is identical to an existing course, due to the global `slug` uniqueness. | **Success**. The tier or category should not prevent creating a course, provided tenant-scoped unique constraints are respected. | 🔴 Bug |
| **Different Capitalization**| **Fails**. `slugify("Python")` and `slugify("python")` both yield `python`. Throws `IntegrityError`. | Application should detect collision and append a numeric suffix to the slug. | 🔴 Bug |
| **Whitespace Differences**| **Fails**. `slugify(" Python ")` yields `python`. Throws `IntegrityError`. | Names should be trimmed; slug should auto-increment suffix if a collision occurs. | 🔴 Bug |
| **Soft Deleted Course** | *N/A*. Courses do not use `is_deleted`. They use `status = "archived"`. | *N/A*. | ⚪ N/A |
| **Archived Course** | **Fails**. The slug of an archived course remains in the database. Creating a new course with the same name throws `IntegrityError`. | Application should allow the new course (by suffixing the new slug) or clear the slug of the archived course. | 🔴 Bug |
| **Restored Course** | **Success**. Changing `status` from `archived` to `draft`/`active` works because the slug remained intact. | **Success**. Course becomes active again. | 🟢 Working |
| **Duplicate Slug Payload**| **Fails**. Passing an explicit duplicate `slug` in the API payload throws `IntegrityError` (HTTP 500 DB error). | API should catch `IntegrityError` and return a clean HTTP 400 or HTTP 409 Conflict. | 🟡 Unhandled Exception |
| **Course Rename** | **Partial**. `update_course` modifies `name` but does not automatically recalculate the `slug`. | **Success**. The slug should *not* change automatically to prevent breaking external links, unless explicitly requested. | 🟢 Working (By Design) |
| **Course Duplication** | **Fails** (if implemented natively without slug mutation) due to `slug` uniqueness constraint. | Must append " (Copy)" to the name and regenerate a unique slug. | 🔴 Depends on Impl. |
| **Course Import** | **Fails** if an imported course name/slug conflicts with *any* course across the entire platform. | Should append suffixes to slugs upon collision within the tenant. | 🔴 High Risk |

## 2. Root Cause Analysis (RC-003)
In `app/models/course.py`:
```python
slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
```
In a multi-tenant system, relying on a globally unique `slug` without a tenant prefix (`org_id`) violates tenant isolation boundaries. Organizations are unintentionally aware of each other's data footprints through slug collision errors.

## 3. Recommended Fix
- **Database Level**: Change the unique constraint from `(slug)` to `(org_id, slug)`.
- **Application Level**: Update `CourseRepository.create_course` to handle slug collisions gracefully by fetching existing slugs like `slug%` and appending `-1`, `-2`, etc.
