# TELITE LMS Authorization Matrix

## Overview
TELITE LMS utilizes a Role-Based Access Control (RBAC) mechanism combined with Tenant and Category Isolation.

## Security Constraints
1. **Tenant Isolation:** All operations (except Platform Admin operations) are scoped to the user's specific organization. Users cannot view or modify data outside their `org_id`.
2. **Category Isolation:** `category_admin` operations are strictly verified against the `category_slug` scope. They cannot perform CRUD operations outside their assigned category.

## Role Definitions & Capabilities

### 1. Platform Admin
- **Scope:** Global (Bypasses Tenant/Org Isolation)
- **Permissions / Actions:**
  - Full access to all platform operations.
  - Create, Read, Update, Delete Organizations (`PLATFORM_MANAGE_ORGS`).
  - View Platform Analytics (`PLATFORM_VIEW_ANALYTICS`).
  - Manage other Platform Admins (`PLATFORM_MANAGE_ADMINS`).
  - Full inheritance of all Super Admin, Category Admin, and Authoring permissions.

### 2. Super Admin (Org Admin)
- **Scope:** Tenant-Wide (Bounded by `org_id`)
- **Permissions / Actions:**
  - Manage Users in the Org (`ORG_MANAGE_USERS`)
  - Manage all Courses in the Org (`ORG_MANAGE_COURSES`)
  - Manage all Categories in the Org (`ORG_MANAGE_CATEGORIES`)
  - View Org Analytics (`ORG_VIEW_ANALYTICS`)
  - Manage Org Settings and Permissions (`ORG_MANAGE_SETTINGS`, `ORG_MANAGE_PERMISSIONS`)
  - Manage Enrollments Org-wide (`ORG_MANAGE_ENROLLMENTS`)
  - Authoring: Full CRUD on Blocks, Sections, Modules, Media, H5P, Question Banks.
  - Gradebook: View, Release, Lock, Override, Audit View.

### 3. Category Admin
- **Scope:** Category-Wide (Bounded by `org_id` and `category_slug`)
- **Permissions / Actions:**
  - Manage Courses in their assigned category (`CAT_MANAGE_COURSES`)
  - Manage Learners enrolled in their category (`CAT_MANAGE_LEARNERS`)
  - View Analytics for their category (`CAT_VIEW_ANALYTICS`)
  - Manage Tasks in their category (`CAT_MANAGE_TASKS`)
  - Authoring: CRUD on Blocks, Sections, Modules, Media, H5P, Question Banks, and Submit for Review within their category scope.
  - Gradebook: View, Release, Lock, Override, Audit View for courses in their category.

### 4. Author / Instructor
- **Scope:** Course/Authoring Specific
- **Permissions / Actions:**
  - Create, Update, Delete content Blocks, Sections, and Modules (`AUTHORING_MANAGE_BLOCKS`, `AUTHORING_MANAGE_SECTIONS`, `AUTHORING_MANAGE_MODULES`).
  - Upload, Replace, Delete Media and H5P content.
  - Manage Questions (`AUTHORING_MANAGE_QUESTIONS`).
  - Submit content for review (`AUTHORING_SUBMIT_REVIEW`).

### 5. Reviewer
- **Scope:** Course/Authoring Specific
- **Permissions / Actions:**
  - Approve or Reject course changes (`AUTHORING_APPROVE_REJECT`).
  - View Authoring Audit Logs (`AUTHORING_VIEW_AUDIT_LOG`).

### 6. Learner
- **Scope:** Personal Data (Bounded by `org_id` and own `user_id`)
- **Permissions / Actions:**
  - View published courses (`LEARNER_VIEW_COURSES`)
  - Enroll in courses (`LEARNER_ENROL`)
  - View own learning progress (`LEARNER_VIEW_PROGRESS`)
  - View own Gradebook data (`GRADEBOOK_LEARNER_VIEW`)
  - View H5P content (`H5P_VIEW`)
  - Learners cannot access or alter data of other learners.
