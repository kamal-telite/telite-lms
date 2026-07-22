# TELITE LMS Frontend Architecture

## Overview
TELITE LMS uses a modular frontend architecture with React and React Router. The routing is broken down into domain-specific routers based on tenant constraints and user roles.

## Route Map

### Public Routes
- **`/login`**
  - **Component:** `Login`
  - **Roles:** Anonymous (redirects authenticated users to their default route)
- **`/signup`**
  - **Component:** Redirects to `/login`
- **`/accept-invite`** & **`/set-password`**
  - **Component:** `AcceptInvitePage`
- **`/reset-password`**
  - **Component:** `ResetPasswordPage`
- **`/public/verify/:token`**
  - **Component:** `CertificateVerifyPage`
- **`/` (Landing Page)**
  - **Component:** `LandingPage`

### Platform Administration Routes
- **`/platform-admin/*`**
  - **Router:** `PlatformRouter`
  - **Page:** `PlatformAdminPage`
  - **Roles Allowed:** Platform Admin (`is_platform_admin = true`)
  - **Tenant Restrictions:** Unbound (global access)
  - **API Calls:** Platform-level configurations, org management.

### Super Admin (Organization) Routes
- **`/super-admin/*`**
  - **Router:** `OrgRouter`
  - **Page:** `SuperAdminPage`
  - **Roles Allowed:** Super Admin (`super_admin`)
  - **Tenant Restrictions:** Scoped to the User's Organization.

### Category Admin / Authoring Routes
- **`/categories/:slug/*`**
  - **Router:** `OrgRouter`
  - **Roles Allowed:** Category Admin (`category_admin`), Super Admin (implicitly through `/super-admin/`)
  - **Tenant Restrictions:** Scoped to User's Organization AND specific `category_slug` scope.
  - **Child Pages:**
    - `/categories/:slug/admin/*` -> `CategoryAdminPage`
    - `/categories/:slug/stats` -> `CategoryStatsPage`
    - `/categories/:slug/builder/:course_id` -> `CourseBuilderPage`
    - `/categories/:slug/paths/:pathId` -> `LearningPathBuilder`
    - `/categories/:slug/question-banks/*` -> `QuestionBankManagerPage`
    - `/categories/:slug/announcements` -> `AnnouncementManagementPage`

### Learner Routes
- **`/learner/*`**
  - **Router:** `LearnerRouter`
  - **Page:** `LearnerPage`
  - **Roles Allowed:** Learner (`learner`), Admins/Authors can usually implicitly access for testing.
  - **Tenant Restrictions:** Scoped to User's Organization.
  - **API Calls:** Fetch courses, enrollments, learner progress, user dashboard.

## Store and State Management
- **Session Management:** Uses a local `session` context state wrapping the application (`App.jsx`), persisted typically in local storage or session storage (`getSession()`, `persistSession()`, `clearSession()`).
- **Offline Sync:** `offlineSyncManager` is used for managing operations that happen while disconnected.
- **Theme/Branding:** `ThemeProvider` and `BrandingProvider` for dynamic UI customization based on tenant.

## Component Structure
- `AppShell`: The main application wrapper injecting branding and toast providers.
- `RouterNavigationBridge`: Event listeners for auth expiration (`telite:auth-expired`) and imperative routing events.
- `LazyChunkErrorBoundary`: Handles dynamic import failures (vite chunk loading errors).
- `ProtectedRoutes`:
  - `ProtectedRoute`: Used for org-scoped routes, enforcing standard roles (super admin, category admin, learner).
  - `ProtectedPlatformRoute`: Specific guard ensuring only users with `is_platform_admin` flag access the route.
