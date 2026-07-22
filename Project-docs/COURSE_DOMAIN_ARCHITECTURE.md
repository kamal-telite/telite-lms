# Course Domain Architecture & Ownership Chain

## Overview
This document traces the complete ownership chain for the `Course` entity within the TELITE LMS, verifying relationships based on the SQLAlchemy models, repositories, and existing architecture documentation.

## Complete Ownership Chain

The hierarchy is structured as follows:
`Platform` -> `Organization (Tenant)` -> `Category` -> `Course`

### 1. Platform -> Organization
- **Relationship:** The Platform (application root) hosts multiple Organizations.
- **Repository Evidence:** `Organization` represents the root tenant entity (`organizations` table). There is no explicit "Platform" table; the platform is the system itself.

### 2. Organization -> Category
- **Relationship:** One-to-Many. An Organization contains multiple Categories.
- **Repository Evidence:** 
  - `Category` inherits from `TenantMixin` giving it `org_id`.
  - `Category` also has a legacy `organization_id` field (`ForeignKey("organizations.id")`).
  - The SQLAlchemy relationship in `Category` is mapped via `organization_id`:
    ```python
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="categories", foreign_keys=[organization_id]
    )
    ```
  - **Note on Redundancy:** There is a duplication of tenant fields here (`org_id` from mixin vs `organization_id`).

### 3. Category -> Course
- **Relationship:** One-to-Many. A Category contains multiple Courses.
- **Repository Evidence:**
  - `Course` model contains `category_slug` (`String(100)`).
  - The relationship is defined using slugs rather than surrogate IDs:
    ```python
    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="courses",
        foreign_keys=[category_slug],
        primaryjoin="Course.category_slug == Category.slug",
    )
    ```

### 4. Organization -> Course (Direct Tenant Link)
- **Relationship:** Implicit One-to-Many. A Course strictly belongs to an Organization.
- **Repository Evidence:**
  - `Course` inherits from `TenantMixin`, granting it a non-nullable `org_id` (`Integer`, foreign key to `organizations.id`).
  - Data access in `CourseRepository` enforces this tenant boundary (e.g., `stmt = select(Course).where(Course.org_id == org_id)`).

## The "True Parent" of a Course
The `Course` entity suffers from a dual-parentage architecture:
1. **The Business/Logical Parent is `Category`.** A course sits inside a category for structural and display purposes.
2. **The Security/Tenant Parent is `Organization`.** A course sits inside an organization for data-isolation and RLS policies.

Technically, the **Organization** is the true authoritative parent. Even if a Category were missing, the system relies on `org_id` for authorization, billing (`price_paise`), and data retrieval. The `Category` acts more as a grouping mechanism (a namespace) than a strict security boundary.

## Contradictions with Existing Documentation
- **TELITE_LMS_DATABASE_SCHEMA_AUDIT.md** states that the "Tenant Field" for `Courses` is `organization_id`. **This is incorrect.** The actual code (`app/models/course.py`) inherits from `TenantMixin`, which defines `org_id`, not `organization_id`.
- The architecture audit does not mention that `Course` to `Category` linkage is done via `category_slug`. Standard relational models use IDs, so this deviation is important but was omitted in `TELITE_LMS_ENTITY_RELATIONSHIP.md` (which we assume follows the schema audit).

## Conclusion
The architecture ensures strong tenant isolation through `TenantMixin.org_id`, but implements a loosely coupled, non-standard business hierarchy between `Course` and `Category` by relying on `slug` rather than `id` for foreign key relationships.
