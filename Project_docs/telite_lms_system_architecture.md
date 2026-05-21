# Telite LMS - System Architecture and Tech Stack

> Version: 5.1.0  
> Last updated: 2026-05-07  
> Status: Active local development with live Moodle integration

---

## 1. Platform Overview

Telite LMS is a role-aware, multi-tenant learning operations platform for colleges and companies. It provides a React dashboard layer, a FastAPI orchestration backend, local Telite LMS data storage, and a Moodle instance used as the course delivery engine.

The platform separates operational workflows from Moodle content delivery:

- Telite LMS owns authentication, role-based access, dashboards, organization management, enrollment workflows, PAL analytics, tasks, signup verification, payment flow, and audit history.
- Moodle owns course runtime delivery and is accessed through Moodle Web Services.
- PostgreSQL stores Moodle data in Docker.
- SQLite or PostgreSQL can store Telite backend data depending on local environment settings.

---

## 2. Current Tech Stack

### Frontend

| Area | Technology | Project Usage |
| --- | --- | --- |
| Runtime | Node.js | Runs Vite development server and production builds |
| Framework | React 18 | SPA pages and dashboards |
| Build tool | Vite 5 | Dev server, HMR, production build |
| Routing | React Router DOM 6 | Public and protected route tree |
| Styling | CSS + Tailwind configuration | `styles.css`, `landing.css`, utility-style classes, Tailwind config |
| State | Zustand | Dashboard, learner, and shared UI state stores |
| HTTP | Axios | API client with auth header injection and token refresh |
| Charts | Chart.js + react-chartjs-2 | Dashboard analytics and visual reports |
| Drag/drop | `@dnd-kit` | Task board interactions |
| Exports | jsPDF, jspdf-autotable, html2canvas | Report/export-style frontend utilities |

### Backend

| Area | Technology | Project Usage |
| --- | --- | --- |
| Runtime | Python 3.11+ / 3.13 local compatible | FastAPI service |
| API framework | FastAPI | REST API with modular routers |
| Server | Uvicorn | Local API server |
| Validation | Pydantic | Request/response models |
| HTTP client | HTTPX | Moodle REST calls |
| Forms/uploads | python-multipart, pandas, openpyxl | Auth forms and verification/bulk upload workflows |
| Database access | sqlite3 + psycopg | SQLite local DB or PostgreSQL backend mode |
| Auth crypto | hashlib + HMAC SHA-256 | Password hashing and signed tokens |

### LMS and Infrastructure

| Area | Technology | Project Usage |
| --- | --- | --- |
| LMS engine | Moodle 4.x | Course content, course launch, Moodle user/course/category sync |
| Moodle database | PostgreSQL 14 | Docker Compose service for Moodle |
| Containers | Docker Compose | Moodle + PostgreSQL stack |
| Registry | GitHub Container Registry | Moodle image sharing |
| Email | SMTP / Gmail SMTP | Signup, approval, rejection, reset, and PAL emails |
| Payment | Razorpay | Guest course payment flow and signature verification |

---

## 3. High-Level Architecture

```text
Browser
  |
  | React SPA on Vite
  | http://localhost:3000
  v
Vite dev proxy
  |
  | API requests: /auth, /dashboard, /api/platform, /categories, ...
  | Current local proxy target: http://127.0.0.1:8001
  v
FastAPI backend
  |
  +-- Telite data store
  |     +-- SQLite: telite-backend/telite_lms.db
  |     +-- optional PostgreSQL mode through TELITE_DB_BACKEND=postgres
  |
  +-- PAL store
  |     +-- SQLite: telite-backend/pal_data.db
  |
  +-- Moodle Bridge
  |     +-- Moodle REST Web Services
  |     +-- Moodle at http://localhost:8082
  |
  +-- SMTP email service
  |
  +-- Razorpay payment gateway
```

Production/container Moodle path:

```text
Docker Compose
  |
  +-- moodle container
  |     +-- Apache/PHP Moodle app
  |     +-- exposed on MOODLE_PORT, default 8082
  |
  +-- postgres container
        +-- PostgreSQL 14
        +-- persistent volume: telite_pgdata
```

---

## 4. Repository Structure

```text
telite-lms/
  moodle/                    Moodle source bundled into the custom image
  telite-backend/            FastAPI backend, data store, Moodle bridge
  telite-frontend/           React/Vite frontend
  Project_docs/              Product, design, and architecture docs
  scripts/                   Utility scripts
  docker-compose.yml         Moodle + PostgreSQL stack
  Dockerfile                 Moodle image build
  docker-config.php          Moodle environment-driven config
  .env.example               Root environment template
```

Important backend files:

```text
telite-backend/
  main.py                    FastAPI app factory, middleware, router registration
  auth.py                    Login, refresh, logout, auth dependencies
  telite_store.py            Core data store, schema, seed, RBAC, builders
  platform_routes.py         Platform admin APIs
  management_routes.py       Categories, courses, users, admins, settings
  dashboard_routes.py        Role-specific dashboard endpoints
  enrol_routes.py            Enrollment workflows
  signup_routes.py           Organization signup and verification
  pal_routes.py              PAL API surface
  pal_engine.py              PAL scoring and recommendations
  pal_db.py                  PAL database helpers
  moodle_bridge.py           Moodle REST abstraction
  moodle_reports.py          Moodle-backed dashboard/user report builders
  payment_routes.py          Razorpay and guest enrollment flow
  email_service.py           SMTP and console fallback email service
  seed_data.py               Seed categories, courses, users, tasks, logs
```

Important frontend files:

```text
telite-frontend/
  vite.config.js             Vite config and API proxy
  src/App.jsx                Route tree and route guards
  src/api/client.js          Shared Axios client and auth refresh logic
  src/api/platform.js        Platform admin API wrapper
  src/lib/session.js         Session persistence and default route selection
  src/lib/store.js           Admin dashboard Zustand store
  src/lib/learnerStore.js    Learner dashboard Zustand store
  src/components/            Shared layout, UI, charts, icons, task board
  src/pages/                 Public pages and role dashboards
```

---

## 5. Role Model

### Canonical System Roles

| Role | Stored Value | Scope | Main Route |
| --- | --- | --- | --- |
| Platform Admin | `super_admin` + `is_platform_admin = 1` | All organizations and platform APIs | `/platform-admin` |
| Tenant Super Admin | `super_admin` + `is_platform_admin = 0` | Own organization | `/super-admin` |
| Category Admin | `category_admin` | Assigned category | `/categories/:slug/admin` |
| Learner | `learner` | Own learner dashboard and assigned category | `/learner` |

### Signup Role Normalization

The backend normalizes older or domain-specific role names into the canonical role model:

| Incoming Role | Canonical Role |
| --- | --- |
| `college_super_admin` | `super_admin` |
| `company_super_admin` | `super_admin` |
| `college_admin` | `super_admin` |
| `company_admin` | `super_admin` |
| `teacher` | `category_admin` |
| `project_admin` | `category_admin` |
| `admin` | `category_admin` |
| `student` | `learner` |
| `employee` | `learner` |
| `intern` | `learner` |

### Seeded Login Roles

| Role | Username | Password | Notes |
| --- | --- | --- | --- |
| Platform Admin | `globaladmin` | `Global@1234` | `is_platform_admin = 1` |
| Tenant Super Admin | `superadmin` | `Super@1234` | Telite University/Telite Systems tenant admin style access |
| ATS Category Admin | `anika` | `Admin@1234` | `category_scope = ats` |
| DevOps Category Admin | `vikram` | `Admin@1234` | `category_scope = devops` |
| Cloud Category Admin | `priya` | `Admin@1234` | `category_scope = cloud` |
| Learner | `rahul` | `Learner@1234` | ATS learner |

---

## 6. Authentication and Session Flow

```text
1. User submits login form.
2. Frontend posts x-www-form-urlencoded credentials to /auth/login.
3. Backend verifies PBKDF2-HMAC-SHA256 password hash.
4. Backend returns access token, refresh token, role, org_id, category_scope, and is_platform_admin.
5. Frontend stores session in localStorage through src/lib/session.js.
6. Axios request interceptor attaches Authorization: Bearer <access_token>.
7. On 401, Axios response interceptor calls /auth/refresh and retries the original request.
8. Logout revokes the refresh session and clears localStorage.
```

Token characteristics:

- Custom compact signed payload, not a third-party JWT library.
- Signature uses HMAC-SHA256 and `TELITE_AUTH_SECRET`.
- Access token expiry is controlled by `TELITE_ACCESS_TOKEN_HOURS` and defaults to 8 hours.
- Refresh token expiry is controlled by `TELITE_REFRESH_TOKEN_DAYS` and defaults to 14 days.
- Refresh sessions are stored server-side in `auth_sessions`.

---

## 7. Frontend Routing

Routes are defined in `telite-frontend/src/App.jsx`.

```text
/login                         Public login page
/signup                        Public organization signup wizard
/accept-invite                 Public invitation acceptance page
/platform-admin/*              Protected platform admin workspace
/super-admin/*                 Protected tenant super admin workspace
/categories/:slug/admin/*      Protected category admin workspace
/categories/:slug/stats        Protected category analytics page
/learner/*                     Protected learner workspace
/dashboard                     Role-aware redirect
/                              Public landing page
*                              Fallback redirect
```

Route guards:

- `ProtectedRoute` checks for a valid session and allowed canonical roles.
- `ProtectedPlatformRoute` requires `session.user.is_platform_admin` or a legacy `platform_admin` role.
- `getDefaultRoute()` in `session.js` sends users to the correct workspace after login.

---

## 8. Backend Router Architecture

Routers are registered in `main.py`.

| Router/File | Prefix | Purpose |
| --- | --- | --- |
| `auth.py` | `/auth` | Login, refresh, logout, current user |
| `dashboard_routes.py` | `/dashboard` | Super admin, category admin, stats, learner dashboards |
| `management_routes.py` | root-level paths | Categories, courses, users, admins, settings, notifications |
| `enrol_routes.py` | `/enrol` | Manual enrollment, self-enrollment, request approvals |
| `task_routes.py` | `/tasks` | Task CRUD and learner submission |
| `pal_routes.py` | `/pal` | PAL user detail, leaderboard, distribution, recomputation |
| `payment_routes.py` | `/payment` | Razorpay orders, verification, guest enrollment |
| `signup_routes.py` | `/signup`, `/admin/verifications`, `/api/invitations` | Signup and verification workflows |
| `platform_routes.py` | `/api/platform` | Platform admin organizations, admins, analytics, Moodle sync, audit |

---

## 9. Platform Admin Module

The platform admin area is the newest top-level admin workspace. It is accessed by `globaladmin` and any user with `is_platform_admin = 1`.

Frontend file:

```text
telite-frontend/src/pages/PlatformAdminPage.jsx
```

Backend file:

```text
telite-backend/platform_routes.py
```

### Platform Admin Routes

| Frontend Tab | Route | Backend APIs |
| --- | --- | --- |
| Overview | `/platform-admin` | `GET /api/platform/analytics/overview` |
| Organizations | `/platform-admin/organizations` | `GET/POST/PATCH /api/platform/organizations` |
| Admin Control | `/platform-admin/admins` | `GET /api/platform/admins`, invite/status APIs |
| Analytics | `/platform-admin/analytics` | Placeholder UI; backend overview/per-org APIs exist |
| Moodle Sync | `/platform-admin/moodle` | Moodle tenant list and sync APIs |
| Audit Logs | `/platform-admin/audit` | `GET /api/platform/audit` |
| Feature Flags | `/platform-admin/features` | `GET/PATCH /api/platform/features` |

### Platform Admin Backend APIs

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/platform/organizations` | List organizations |
| POST | `/api/platform/organizations` | Create organization |
| GET | `/api/platform/organizations/{org_id}` | Organization detail |
| PATCH | `/api/platform/organizations/{org_id}` | Update organization |
| PATCH | `/api/platform/organizations/{org_id}/status` | Activate/suspend organization |
| GET | `/api/platform/admins` | List platform-visible admins |
| POST | `/api/platform/admins/invite` | Invite organization admin |
| PATCH | `/api/platform/admins/{user_id}/status` | Activate/suspend admin |
| GET | `/api/platform/analytics/overview` | Global KPIs, org usage, Moodle health, recent activity |
| GET | `/api/platform/analytics/org/{org_id}` | Per-org analytics |
| GET | `/api/platform/moodle/tenants` | Moodle tenant sync status |
| POST | `/api/platform/moodle/sync/{org_id}` | Sync one organization |
| POST | `/api/platform/moodle/sync-all` | Sync all organizations |
| GET | `/api/platform/features` | List org feature flags |
| PATCH | `/api/platform/features/{org_id}` | Toggle feature flag |
| GET | `/api/platform/audit` | Global platform audit log |

---

## 10. Data Model

The current local SQLite database contains these tables:

```text
activity_log
admin_actions
allowed_domains
audit_log
auth_sessions
categories
courses
enrollment_requests
moodle_tenants
notifications
org_feature_flags
org_invitations
organizations
password_reset_tokens
pending_verifications
tasks
users
```

### Primary Entities

| Entity | Purpose |
| --- | --- |
| `organizations` | Top-level college/company tenant records |
| `users` | All admins and learners, including org and role metadata |
| `categories` | Learning categories such as ATS, DevOps, Cloud |
| `courses` | Telite course metadata and Moodle course ID mapping |
| `enrollment_requests` | Manual/self enrollment approval queue |
| `pending_verifications` | Signup registration review queue |
| `tasks` | Admin-assigned and learner-submitted tasks |
| `audit_log` | Admin/system mutation trail |
| `activity_log` | User-facing timeline/activity feed |
| `notifications` | User notifications |
| `auth_sessions` | Refresh session tracking and logout revocation |
| `moodle_tenants` | Organization-to-Moodle sync status |
| `org_feature_flags` | Per-organization feature toggles |
| `org_invitations` | Invitation tokens for admin onboarding |

### Database Modes

The backend can run in two data modes:

| Mode | Env | Notes |
| --- | --- | --- |
| SQLite | `TELITE_DB_BACKEND=sqlite` | Local file mode, default for fast development |
| PostgreSQL | `TELITE_DB_BACKEND=postgres` | Uses `TELITE_DATABASE_URL` or explicit `TELITE_POSTGRES_*` settings |

The root `.env.example` includes both local SQLite migration paths and PostgreSQL configuration for future backend persistence.

---

## 11. Moodle Integration

Moodle communication is centralized in `moodle_bridge.py`.

### Moodle Modes

| Mode | Env Value | Behavior |
| --- | --- | --- |
| Auto | `MOODLE_MODE=auto` | Try live Moodle and fall back when unavailable |
| Live | `MOODLE_MODE=live` | Use real Moodle API and report errors |
| Mock | `MOODLE_MODE=mock` | Use local synthetic responses |

### Important Moodle Environment Variables

| Variable | Purpose |
| --- | --- |
| `MOODLE_URL` | Browser/external Moodle URL, commonly `http://localhost:8082` |
| `MOODLE_INTERNAL_URL` | Docker internal service URL, commonly `http://moodle` |
| `MOODLE_TOKEN` | Moodle web service token |
| `MOODLE_TEACHER_ROLE_ID` | Moodle teacher role id |
| `MOODLE_STUDENT_ROLE_ID` | Moodle student role id |

### Moodle Bridge Responsibilities

- Create and delete Moodle categories.
- Create and delete Moodle courses.
- Create Moodle users.
- Search Moodle users.
- Enroll learners in Moodle courses.
- Fetch Moodle site information.
- Generate Moodle health diagnostics.
- Build Moodle-backed dashboard/report payloads.

---

## 12. Core Product Modules

### Authentication

- Username/password login.
- Access and refresh token lifecycle.
- Session persistence and automatic refresh in Axios.
- Logout and server-side refresh token revocation.

### Platform Administration

- Global organization listing and creation.
- Organization activation/suspension.
- Admin invitation and status control.
- Global usage analytics.
- Moodle tenant sync controls.
- Feature flag management.
- Platform-wide audit log.

### Tenant Super Admin

- Organization-level category, course, user, enrollment, task, verification, PAL, and audit management.
- Cross-category workflows for the tenant.
- Moodle-backed category/course sync.

### Category Admin

- Category-scoped dashboard.
- Category course CRUD.
- Learner list and progress visibility.
- Enrollment queue approval/rejection.
- Verification queue review.
- Task assignment.
- PAL leaderboard and activity feed.

### Learner

- Personal dashboard.
- Assigned courses and course launch.
- PAL score and breakdown.
- Assigned tasks and submission.
- Activity timeline and notifications.

### Signup and Verification

- Organization selection.
- College/company role selection.
- Dynamic fields by role.
- Domain validation.
- Pending verification queue.
- Approval creates user, syncs Moodle, sends email.
- Rejection stores reason and sends email.

### PAL Engine

- PAL scoring based on completion, quiz average, task completion, time spent, and streak.
- Level classification and recommendations.
- Category leaderboard and distribution APIs.
- Admin-triggered recomputation.

### Payment

- Razorpay order creation.
- Signature verification.
- Guest enrollment into selected course.
- Mock order behavior when Razorpay credentials are absent.

---

## 13. Local Development

### Moodle and PostgreSQL

```powershell
docker compose up -d
```

Moodle default URL:

```text
http://localhost:8082
```

### Backend

Current local backend port is `8001` because port `8000` is unavailable on this Windows machine.

```powershell
cd C:\Users\kamal\OneDrive\Desktop\telite-lms\telite-backend
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Health check:

```powershell
curl.exe http://127.0.0.1:8001/health
```

### Frontend

```powershell
cd C:\Users\kamal\OneDrive\Desktop\telite-lms\telite-frontend
npm run dev
```

Frontend default URL:

```text
http://localhost:3000
```

Current Vite proxy target:

```text
http://127.0.0.1:8001
```

If the backend returns to port `8000`, update `telite-frontend/vite.config.js` accordingly and restart Vite.

---

## 14. Security Model

| Concern | Implementation |
| --- | --- |
| Password storage | PBKDF2-HMAC-SHA256 via `hashlib.pbkdf2_hmac` |
| Token signing | HMAC-SHA256 with `TELITE_AUTH_SECRET` |
| Refresh sessions | Stored in `auth_sessions`; revoked on logout |
| Route protection | FastAPI dependencies and React protected routes |
| Platform admin protection | `is_platform_admin` checked in backend and frontend |
| Tenant isolation | `org_id` and `organization_id` filters in store queries |
| Category isolation | `category_scope` checks for category admins |
| Domain control | Organization/domain checks during signup |
| Auditability | Mutating admin actions written to audit/activity logs |
| Payment security | Razorpay signature verification |
| Soft delete | Users and organizations are deactivated/suspended rather than hard-deleted |

---

## 15. Known Local Notes

- `globaladmin / Global@1234` is the platform admin seed account.
- `superadmin / Super@1234` is the tenant super admin seed account.
- The platform admin frontend was hardened to tolerate empty analytics arrays.
- Vite proxy currently points to backend port `8001`.
- Moodle is configured in live mode in `telite-backend/.env`.
- Do not commit `.env`, tokens, generated logs, or local DB files unless intentionally producing a snapshot.

