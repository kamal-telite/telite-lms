# Course Identity Audit

## Overview
This document audits all identifiers associated with the `Course` entity in the TELITE LMS repository. It analyzes their purpose, classifies them, and identifies the canonical identity based on database schema and application logic.

## Course Identifiers Analyzed

1. **`id` (Database Identifier / UUID)**
   - **Type:** `String(50)` (Format: `course-<10-hex-chars>`)
   - **Definition:** `primary_key=True`
   - **Purpose:** Acts as the primary database surrogate key. It is used in internal relationships where strict referential integrity is needed (e.g., `LearningPathCourse.course_id`, `prerequisite_course_id`).
   - **Classification:** Database Identifier.

2. **`slug` (Business & Routing Identifier)**
   - **Type:** `String(100)`
   - **Definition:** `unique=True, nullable=False`
   - **Purpose:** Used primarily for URL routing and API lookups (e.g., `get_by_slug` in `CourseRepository`). Interestingly, it is marked as globally unique across the entire database, not just within a tenant.
   - **Classification:** Business/Routing Identifier.

3. **`category_slug` (Structural/Relational Identifier)**
   - **Type:** `String(100)`
   - **Definition:** `nullable=False, index=True` (Foreign key to `Category.slug`)
   - **Purpose:** Forms the structural hierarchy linking a `Course` to a `Category`. This is an architectural anomaly where a business/routing identifier (`slug`) is used as a foreign key instead of the database identifier (`category.id`).
   - **Classification:** Relational / Routing Identifier.

4. **`name` (Display Identifier)**
   - **Type:** `String(255)`
   - **Definition:** `nullable=False`
   - **Purpose:** The human-readable title of the course presented to users in the UI.
   - **Classification:** Display Identifier.

5. **`org_id` (Tenant / Security Identifier)**
   - **Type:** `Integer`
   - **Definition:** Foreign key to `organizations.id` (Inherited via `TenantMixin`).
   - **Purpose:** Provides the tenant boundary. Used by PostgreSQL Row-Level Security (RLS) policies and all tenant-scoped queries (e.g., `CourseRepository.list_by_org`).
   - **Classification:** Security/Tenant Identifier.

## Canonical Identity
- **Routing & API Canonical Identity:** `slug`. Most external systems and frontend clients address the course via its `slug`. Since it has a `unique=True` constraint globally, it can unambiguously identify a course regardless of tenant context.
- **Database Canonical Identity:** `id`. Used for true relational joins (like learning paths).
- **Security Canonical Identity:** The composite of `(org_id, id)`. In a multi-tenant system, access must always be verified using `org_id` to prevent cross-tenant data leakage.

## Potential Issues / Tech Debt
- **Global Uniqueness of Slug:** `slug` is strictly `unique=True` without `org_id` included in a composite unique constraint. This means two different tenants cannot have a course with the same slug (e.g., "intro-to-python").
- **Denormalized Foreign Keys:** Using `category_slug` as the foreign key to `Category` breaks standard normalization. If a Category's slug changes, it cascades down to all Courses, which could cause significant operational overhead or broken references if not handled carefully.
