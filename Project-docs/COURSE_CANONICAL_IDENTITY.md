# Course Canonical Identity Recommendation

## Executive Summary
After auditing the Telite LMS database schema, repository behavior, and routing architecture, the recommended canonical identity for a Course is **Option B: `org_id + slug`**.

## Evidence & Evaluation of Options

### Option A: Global Slug (Current Architecture)
- **Status:** Rejected.
- **Evidence:** `app/models/course.py` defines `slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)`.
- **Reason:** This enforces global uniqueness across the entire platform. Organization A cannot create a course named "Introduction to Python" (slug: `intro-to-python`) if Organization B has already used it. This fundamentally breaks multi-tenancy and is the root cause of RC-003.

### Option C: `org_id + category_slug + slug`
- **Status:** Rejected.
- **Evidence:** `CourseRepository.update_course` allows arbitrary field updates (`setattr(course, key, value)`), which includes changing `category_slug`.
- **Reason:** Scoping uniqueness to the category is highly brittle. If a course is moved to a different category (e.g., from "Drafts" to "Computer Science"), its identity signature changes. This would require cascaded updates to slugs and would break existing external links or bookmarks. Category is a mutable relationship, not a bounded context for course identity.

### Option B: `org_id + slug` (Recommended)
- **Status:** Approved.
- **Evidence:** The system routes heavily using the immutable primary key `course_id` (e.g., Learner API routes via `/courses/{id}` and Management via `/categories/{category_slug}/courses/{course_id}`). However, slugs are used for user-friendly URLs and uniqueness enforcement.
- **Reason:** 
  - **DDD:** The Organization is the ultimate root aggregate for multi-tenancy.
  - **Multi-Tenancy:** By replacing the global `UNIQUE(slug)` constraint with `UNIQUE(org_id, slug)`, multiple tenants can use generic slugs ("math-101") without collision.
  - **Scalability:** It fully supports future features like global search or marketplace (since the tenant ID guarantees uniqueness within the tenant's namespace).

## Conclusion
Migrating the `UNIQUE` constraint from `(slug)` to `(org_id, slug)` on both `courses` and `categories` tables provides robust multi-tenancy while retaining the flexibility for courses to move between categories.
