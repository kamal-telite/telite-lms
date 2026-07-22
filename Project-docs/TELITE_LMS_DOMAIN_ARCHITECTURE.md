# TELITE LMS Domain Architecture

## 1. URL and Slug Architecture

### Tenant Awareness
The platform is built on a multi-tenant architecture where `Organization` is the root tenant. Every tenant-scoped entity inherits from `TenantMixin`, which embeds an `org_id` foreign key.

### Lookup Logic & URL Format
- **URLs:** The application uses tenant-specific routing, typically in the format `https://<org_slug>.telite.in/` or mapped to a custom domain via `https://<custom_domain>/`.
- **Lookup:** Tenants are primarily resolved via `domain` or `slug`. 

### Current Uniqueness Rules
- **Organization:** `name`, `domain`, and `slug` are all globally unique.
- **Category:** `slug` is marked as globally unique (`unique=True`). 
- **Course:** `slug` is marked as globally unique (`unique=True`).
- **User:** `username` and `email` are globally unique.
- **Membership:** The combination of `(user_id, org_id)` is unique per user-tenant pair.

---

## 2. Core Business Domain Model

### Organization (Tenant)
- **Business Meaning:** The root of the multi-tenant hierarchy (e.g., a college or company).
- **Owner:** Platform Administrator or Creator.
- **Lifecycle:** Created -> Active (managed via `status`). Plans define access (e.g., 'free').
- **Relationships:** Has many `Users`, `Memberships`, `Categories`, and a 1:1 mapping to `OrganizationBranding`.
- **Tenant Scope:** Global (Root entity).
- **Soft Delete:** Managed via the `status` field (no explicit `deleted_at`).
- **Foreign Keys:** `admin_user_id`, `created_by`.
- **Unique Constraints:** `name`, `domain`, `slug`.

### User
- **Business Meaning:** Represents an individual identity in the system (learner, instructor, admin).
- **Owner:** Self-owned, administered by Organization Admins.
- **Lifecycle:** Managed via `is_active` flag and `status` ('active', 'suspended', 'disabled').
- **Relationships:** Links to `Organizations` (via `Memberships`) and `AuthSessions`.
- **Tenant Scope:** Scoped to `org_id` (via `TenantMixin`), with legacy fallback to `organization_id`.
- **Soft Delete:** Flag-based (`is_active=False`).
- **Foreign Keys:** `org_id` (canonical), `organization_id` (legacy).
- **Unique Constraints:** `username`, `email`.

### Membership
- **Business Meaning:** Enterprise RBAC mapping of Users to Organizations. Allows a single user to hold different roles across multiple organizations.
- **Owner:** Organization Admin.
- **Lifecycle:** 'active', 'suspended', or 'invited' (managed via `status`).
- **Relationships:** Joins `User` and `Organization`.
- **Tenant Scope:** Cross-reference linking User to Tenant.
- **Soft Delete:** Status-based.
- **Foreign Keys:** `user_id`, `org_id`, `granted_by`.
- **Unique Constraints:** Composite constraint on `(user_id, org_id)`.

### Category
- **Business Meaning:** Represents a department, school, or grouping within an organization.
- **Owner:** Organization.
- **Lifecycle:** Active -> Archived.
- **Relationships:** Belongs to `Organization`, contains many `Courses`.
- **Tenant Scope:** Scoped to `org_id` via `TenantMixin`.
- **Soft Delete:** Uses `archived_at` timestamp.
- **Foreign Keys:** `organization_id` (legacy), `org_id`, `admin_user_id`.
- **Unique Constraints:** `slug`.

### Course
- **Business Meaning:** A learning product containing educational modules, tracking progress, and analytics.
- **Owner:** Category / Organization.
- **Lifecycle:** Draft -> Published (managed via `status`).
- **Relationships:** Belongs to `Category` (linked via `category_slug`).
- **Tenant Scope:** Scoped to `org_id` via `TenantMixin`.
- **Soft Delete:** Status-based (e.g., 'draft', 'archived').
- **Foreign Keys:** `category_slug`, `org_id`, `prerequisite_course_id`.
- **Unique Constraints:** `slug`.

### CourseModule
- **Business Meaning:** A structural container for content within a course.
- **Owner:** Course.
- **Lifecycle:** Draft -> Published. Supports strict deletion tracking.
- **Relationships:** Belongs to `Course`.
- **Tenant Scope:** Scoped to `org_id` via `TenantMixin`.
- **Soft Delete:** Explicitly tracked via `deleted_at` and `deleted_by`.
- **Foreign Keys:** `course_id`, `section_id`, `org_id`, `deleted_by`.
- **Unique Constraints:** None natively defined (relies on sort_order).

### LessonBlock
- **Business Meaning:** A granular piece of content (text, image, video, quiz_ref) within a module.
- **Owner:** CourseModule.
- **Lifecycle:** Active -> Deleted.
- **Relationships:** Belongs to `CourseModule`, can reference `MediaAsset`.
- **Tenant Scope:** Scoped to `org_id` explicitly.
- **Soft Delete:** Explicitly tracked via `deleted_at` and `deleted_by`.
- **Foreign Keys:** `module_id`, `org_id`, `media_asset_id`, `deleted_by`.
- **Unique Constraints:** None.

### EnrollmentRequest
- **Business Meaning:** Tracks a user's request to enroll in a specific category.
- **Owner:** User / Reviewing Admin.
- **Lifecycle:** Pending -> Reviewed (Approved/Rejected).
- **Relationships:** References `Category` via `category_slug`.
- **Tenant Scope:** Scoped to `org_id` via `TenantMixin`.
- **Soft Delete:** Status-based or hard-deleted upon approval/rejection.
- **Foreign Keys:** `org_id`.
- **Unique Constraints:** None.
