# Category Admin Feature Visibility Audit

## Scope

Investigated why Announcements and Question Bank appear after login but reportedly disappear after logout/login as Category Admin.

Required evidence captured:

- `POST /auth/login` response payload.
- `GET /auth/me` response payload.
- Resolved user role.
- Category scope.
- Permissions.
- Current route after:
  - Initial login.
  - Logout/login within the SPA.
  - Hard browser refresh.

No code changes were made.

## Account Tested

Category Admin:

```text
username: kt_category_admin
role: category_admin
category_scope: backend-development
org_id: 1
```

## Backend Payload Comparison

### POST /auth/login

Status:

```text
200 OK
```

Selected payload:

```json
{
  "user_id": "kt_category_admin",
  "username": "kt_category_admin",
  "role": "category_admin",
  "name": "KT Category Admin",
  "email": "categoryadmin@ktlearn.local",
  "category_scope": "backend-development",
  "org_id": 1,
  "is_platform_admin": false,
  "permissions_count": 20,
  "theme_preference": "light"
}
```

Permissions:

```json
[
  "authoring.manage_blocks",
  "authoring.manage_media",
  "authoring.manage_modules",
  "authoring.manage_questions",
  "authoring.manage_sections",
  "authoring.publish_questions",
  "authoring.submit_review",
  "authoring.view_audit_log",
  "cat.manage_courses",
  "cat.manage_learners",
  "cat.manage_tasks",
  "cat.view_analytics",
  "h5p.delete",
  "h5p.edit",
  "h5p.upload",
  "h5p.view",
  "learner.enrol",
  "learner.view_courses",
  "learner.view_progress",
  "org.manage_banks"
]
```

### GET /auth/me

Status:

```text
200 OK
```

Selected payload:

```json
{
  "user_id": "kt_category_admin",
  "username": "kt_category_admin",
  "role": "category_admin",
  "name": "KT Category Admin",
  "email": "categoryadmin@ktlearn.local",
  "category_scope": "backend-development",
  "org_id": 1,
  "is_platform_admin": false,
  "is_active": true,
  "permissions_count": 20,
  "theme_preference": "light"
}
```

Permissions exactly match `POST /auth/login`.

## Payload Divergence Verdict

No meaningful identity, role, category-scope, or permission divergence was found between:

- `POST /auth/login`
- `GET /auth/me`

The earlier hypothesis that this is caused by a backend login/me payload mismatch is not supported by the captured data.

## Browser State Verification

Captured with a fresh browser context against the running Docker frontend at `http://localhost:3000`.

### 1. Initial Login

Current route:

```text
/categories/backend-development/admin
```

Resolved session user:

```json
{
  "user_id": "kt_category_admin",
  "role": "category_admin",
  "name": "KT Category Admin",
  "email": "categoryadmin@ktlearn.local",
  "category_scope": "backend-development",
  "org_id": 1,
  "is_platform_admin": false,
  "permissions_count": 20
}
```

Visibility:

```text
Question banks: visible
Announcements: not visible
```

Rendered sidebar text excerpt:

```text
Management
Courses
Question banks
Learners
Enrollment
Verifications
Tasks
```

### 2. SPA Logout

Current route:

```text
/login
```

Session storage:

```text
empty
```

### 3. SPA Logout/Login

Current route:

```text
/categories/backend-development/admin
```

Resolved session user remains:

```json
{
  "user_id": "kt_category_admin",
  "role": "category_admin",
  "category_scope": "backend-development",
  "org_id": 1,
  "is_platform_admin": false,
  "permissions_count": 20
}
```

Visibility:

```text
Question banks: visible
Announcements: not visible
```

### 4. Hard Browser Refresh

Current route:

```text
/categories/backend-development/admin
```

`GET /auth/me` returns the same category admin identity and permissions.

Visibility:

```text
Question banks: visible
Announcements: not visible
```

## Direct Route Verification

### Question Bank Route

URL:

```text
http://localhost:3000/categories/backend-development/question-banks
```

Result:

```text
route: /categories/backend-development/question-banks?bank=2
heading: Question Bank Manager
Question Bank APIs called successfully
```

Network:

```text
GET /api/v1/question-banks?category_slug=backend-development -> 200
GET /api/v1/question-banks/tags -> 200
GET /api/v1/question-banks/categories?tree=true -> 200
GET /api/v1/question-banks/questions?... -> 200
```

### Announcements Route

URL:

```text
http://localhost:3000/categories/backend-development/announcements
```

Result:

```text
route: /categories/backend-development/admin
heading: Backend Development Admin Dashboard
Announcements API was not called
```

This means the running frontend router did not match the announcements route and fell back to the Category Admin dashboard route.

## Source Versus Running Frontend Bundle

Local source file:

`telite-frontend/src/pages/company/CategoryAdminPage.jsx`

Local source includes:

```javascript
{ id: "question_banks", label: "Question banks", icon: "database" },
{ id: "announcements", label: "Announcements", icon: "bell" },
```

Local source route file:

`telite-frontend/src/routes/org_router.jsx`

Local source includes:

```javascript
<Route
  path="announcements"
  element={
    <ProtectedRoute session={session} allowRoles={["category_admin"]}>
      <AnnouncementManagementPage session={session} onLogout={onLogout} />
    </ProtectedRoute>
  }
/>
```

Running Docker frontend image inspection:

```text
docker inspect telite_frontend --format '{{json .Mounts}}'
```

Result:

```json
[]
```

The running frontend container is not using a live source mount. It is serving a built bundle from the image.

Container asset timestamp:

```text
/usr/share/nginx/html/assets/CategoryAdminPage-C13jwJW-.js
```

In the running bundle, the `CategoryAdminPage` nav group contains `Question banks` but does not contain `Announcements`, and the `onNavClick` handler has a branch for `question_banks` but no branch for `announcements`.

This proves the running Docker frontend bundle is stale relative to the local source.

## Root Cause Assessment

### Question Bank

Current evidence does not reproduce the reported Question Bank disappearance.

Evidence:

- Session identity remains correct after initial login, SPA logout/login, and hard refresh.
- `Question banks` remains visible.
- Direct Question Bank route loads.
- Question Bank APIs return 200.

### Announcements

Announcements are missing from the rendered Docker frontend because the running frontend bundle is stale and does not include the local source route/sidebar changes.

This is not a backend permission failure.

Evidence:

- Backend login/me payloads are correct.
- Category Admin permissions are stable.
- Direct announcements URL is handled by the SPA but falls back to `/categories/backend-development/admin`.
- No announcements API request is made.
- Local source contains the route and nav item.
- Running Docker bundle does not contain that route/nav item.

## Shared Underlying Visibility Bug?

Based on current evidence:

```text
Question Bank and Announcements do not share the same confirmed visibility bug.
```

Question Bank is operational in the running environment.

Announcements are affected by a frontend deployment artifact mismatch.

If QA observed both disappearing, the likely causes are:

1. A stale frontend bundle or browser cache in that QA environment.
2. A route fallback caused by an older `OrgRouter` bundle.
3. A separate data-load issue not reproduced in the current Docker environment.

The captured payloads do not support a role permission or category scope regression.

## Smallest Safe Remediation

Do not modify `session.js` or route guards based on the current evidence.

Recommended next fix, after approval:

1. Rebuild the frontend Docker image from the current source.
2. Restart the frontend container.
3. Hard-refresh the browser or clear cached chunks.
4. Verify the built container bundle contains:
   - `Announcements`
   - `/categories/:slug/announcements`
5. Re-run the same browser verification sequence.

## Verification Required After Rebuild

Expected results:

```text
Initial login:
  route = /categories/backend-development/admin
  Question banks visible = true
  Announcements visible = true

SPA logout/login:
  route = /categories/backend-development/admin
  Question banks visible = true
  Announcements visible = true

Hard refresh:
  route = /categories/backend-development/admin
  Question banks visible = true
  Announcements visible = true

Direct route:
  /categories/backend-development/announcements
  heading = Announcements
  announcements API called
```

## Frontend Rebuild Verification Update

After the audit confirmed deployment drift, the frontend image was rebuilt and the frontend container was restarted:

```text
docker compose build frontend
docker compose up -d frontend
```

Container status after rebuild:

```text
telite_frontend  telite-lms-frontend  Up 20 minutes (healthy)  0.0.0.0:3000->80/tcp
```

Browser verification after rebuild using Category Admin `kt_category_admin`:

```text
route after login: /categories/backend-development/admin
Question banks visible: true
Announcements visible: true
```

Clicking the rebuilt Announcements navigation item now routes correctly:

```text
route: /categories/backend-development/announcements
heading: Announcement Center
```

The page then calls the announcements API and receives:

```text
GET /api/v1/announcements -> 404
```

This confirms the original visibility problem was a stale frontend bundle/deployment issue. The remaining `404` is a separate backend route-prefix/runtime availability issue and is not evidence of auth/session drift or Category Admin permission loss.

## Readiness Verdict

Auth payload mismatch is not confirmed.

Category Admin route and session state remain stable across login, SPA logout/login, and hard refresh.

The confirmed issue is that the running Docker frontend image is stale relative to the local source. Rebuild/redeploy frontend before making session or permission changes.

The frontend has now been rebuilt from current source, and Announcements is visible and routable for Category Admin.
