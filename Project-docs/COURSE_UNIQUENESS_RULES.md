# Course Uniqueness Rules Analysis

This document details the current uniqueness constraints for Courses across the TELITE LMS architecture, highlighting contradictions between the implementation and business rules.

## Current Uniqueness Scope Table

| Layer | Current Scope | Evidence |
|-------|---------------|----------|
| **Database Constraints** | Global | Explicit constraint `uq_courses_slug` created in `courses` table. |
| **SQLAlchemy Models** | Global | `app/models/course.py`: `slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)` |
| **Alembic Migrations** | Global | `000_bootstrap_foundation.py` lines 136: `sa.UniqueConstraint("slug", name="uq_courses_slug")` |
| **Repository Layer** | None | `app/repositories/course_repo.py`: `create_course` automatically populates slug using `slugify(name)` without checking if it exists first. |
| **Service / API Layer** | None | `app/api/routes/management.py`: `post_course` endpoint tries to insert and catches the generic DB exception, but performs no explicit pre-check for slug uniqueness. |
| **Frontend Validation** | None | Client relies on the backend returning a 400 Bad Request if the database insertion fails. |
| **Documentation (Business Rules)** | Org-level | `TELITE_LMS_BUSINESS_RULES.md` (line 10) explicitly states: *"Course Slugs: Course slugs are unique within an organization, not globally."* |
| **Documentation (Domain Arch)** | Global | `TELITE_LMS_DOMAIN_ARCHITECTURE.md` (line 15) states: *"- Course: slug is marked as globally unique (unique=True)."* |

## Contradictions and Issues
1. **Business Logic vs Implementation**: The biggest contradiction is between `TELITE_LMS_BUSINESS_RULES.md`, which dictates that course slugs should only be unique within an organization, and the actual codebase (SQLAlchemy and Alembic), which forces a strict **global** unique constraint (`uq_courses_slug`).
2. **Missing Application-Level Checks**: Because the repository and API layers do not verify if a slug exists before attempting an insert, if a course name like "Introduction" is used by Tenant A, Tenant B will experience a raw 400 database exception if they try to create a course with the same name.
3. **Documentation Conflict**: The existing documentation is conflicted. The business rules document specifies per-org uniqueness, while the domain architecture document accurately describes the current (but incorrect) global code constraint.
