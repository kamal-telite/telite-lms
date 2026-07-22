# Course Tenant Analysis

This document analyzes how Course uniqueness should be scoped within the multi-tenant architecture of TELITE LMS.

## Current Architecture Context
- **Tenancy Model**: The platform uses `TenantMixin` for database-level tenancy. Every tenant-scoped entity, including `Course`, embeds an `org_id` foreign key. Row-Level Security (RLS) is applied on top of this.
- **Ownership Model**: Courses belong to an `Organization` (tenant).
- **Categories**: Courses also belong to a `Category` (via `category_slug` / `category_id`), which itself is scoped to an `Organization`.

## Analysis of Uniqueness Scopes

### 1. Global Uniqueness (Current Implementation)
- **Feasibility**: Not suitable.
- **Why**: In a multi-tenant platform (like a white-label LMS), organizations should not collide with each other. If Organization A creates a course called "Introduction to React", Organization B must also be able to create "Introduction to React". Global uniqueness prevents this and leaks information about what other tenants have created.

### 2. Category-Level or Org + Category Uniqueness
- **Feasibility**: Possible, but flawed.
- **Why**: If a slug is only unique within a category, the URL must permanently include the category slug (e.g., `/:org_slug/categories/:category_slug/courses/:course_slug`). 
- If an admin decides to move a course from one category to another, there is a risk of a slug collision if the destination category already has a course with that slug. This makes course movement complex and brittle.

### 3. Organization-Level Uniqueness (Recommended)
- **Feasibility**: Highly Recommended.
- **Why**: Scoping uniqueness to `(org_id, slug)` is the standard approach for multi-tenant applications.
  - **Tenancy Isolation**: Each organization has full control over their slugs without interference from others.
  - **Flexibility**: Courses can be moved across categories within the same organization without slug conflicts.
  - **Simpler Routing**: Course routes can just be `/:org_slug/courses/:course_slug`, which is cleaner.
  - **Business Rules Alignment**: The `TELITE_LMS_BUSINESS_RULES.md` document already dictates that Course slugs should be unique within an organization.

## Recommendation Steps
To align the architecture with proper multi-tenant design:
1. **Drop Global Constraint**: Remove the global `uq_courses_slug` constraint and `unique=True` on the `slug` column in `app/models/course.py`.
2. **Add Composite Constraint**: Create a composite unique constraint `uq_courses_org_slug` on `(org_id, slug)` via a new Alembic migration.
3. **Application Layer**: Update `CourseRepository.create_course` to verify slug uniqueness against the `org_id` and auto-increment a suffix (e.g., `-1`, `-2`) if there's a collision during generation.
