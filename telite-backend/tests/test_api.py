import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class TeliteApiTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["TELITE_DB_BACKEND"] = "sqlite"
        os.environ["TELITE_DB_PATH"] = os.path.join(self.tempdir.name, "test_telite_lms.db")
        os.environ.pop("TELITE_DATABASE_URL", None)
        os.environ.pop("TELITE_SQLITE_SOURCE_PATH", None)
        os.environ["MOODLE_MODE"] = "mock"
        main = importlib.import_module("main")
        importlib.reload(main)
        self.store = importlib.import_module("telite_store")
        importlib.reload(self.store)
        self.client = TestClient(main.create_app())
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def login(self, username: str, password: str) -> dict:
        response = self.client.post(
            "/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def auth_headers(self, username: str, password: str) -> dict:
        token = self.login(username, password)["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def seed_org2_fixtures(self):
        progress = '[{"course_id":"course-sales-ops","progress":0,"status":"in_progress","current_lesson":null}]'
        with self.store.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    id, username, email, full_name, role, category_scope, password_hash,
                    avatar_initials, gradient_start, gradient_end, is_active, pal_score,
                    pal_completion_pct, pal_quiz_avg, pal_time_spent_hours,
                    pal_task_completion_pct, streak_days, courses_completed, total_courses,
                    cohort_rank, enrollment_type, current_course_id, course_progress_json,
                    created_at, last_login, organization_id, org_id, is_platform_admin, status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "user-org2-admin",
                    "org2admin",
                    "org2admin@telite.io",
                    "Org Two Admin",
                    "super_admin",
                    None,
                    self.store.hash_password("Admin@1234"),
                    "OA",
                    "#7C3AED",
                    "#2563EB",
                    1,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    None,
                    None,
                    None,
                    "[]",
                    self.store.now_local(),
                    None,
                    2,
                    2,
                    0,
                    "active",
                ),
            )
            conn.execute(
                """
                INSERT INTO categories (
                    id, name, slug, description, status, accent_color, admin_user_id,
                    planned_courses, avg_pal_target, moodle_category_id, org_type,
                    organization_id, org_id, created_at, archived_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "cat-sales",
                    "Sales",
                    "sales",
                    "Sales enablement",
                    "active",
                    "#0891B2",
                    "user-org2-admin",
                    1,
                    0,
                    None,
                    "company",
                    2,
                    2,
                    self.store.now_local(),
                    None,
                ),
            )
            conn.execute(
                """
                INSERT INTO courses (
                    id, moodle_course_id, category_slug, name, slug, description, tier, status,
                    module_count, modules_json, lessons_count, hours, enrolled_count,
                    completion_rate, completion_count, avg_quiz_score, prerequisite_course_id, created_at, org_id
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "course-sales-ops",
                    201,
                    "sales",
                    "Sales Ops",
                    "sales-ops",
                    "Sales foundations",
                    "Core",
                    "published",
                    2,
                    "[]",
                    4,
                    8,
                    1,
                    0,
                    0,
                    0,
                    None,
                    self.store.now_local(),
                    2,
                ),
            )
            conn.execute(
                """
                INSERT INTO users (
                    id, username, email, full_name, role, category_scope, password_hash,
                    avatar_initials, gradient_start, gradient_end, is_active, pal_score,
                    pal_completion_pct, pal_quiz_avg, pal_time_spent_hours,
                    pal_task_completion_pct, streak_days, courses_completed, total_courses,
                    cohort_rank, enrollment_type, current_course_id, course_progress_json,
                    created_at, last_login, organization_id, org_id, is_platform_admin, status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "user-org2-learner",
                    "org2learner",
                    "org2learner@telite.io",
                    "Org Two Learner",
                    "learner",
                    "sales",
                    self.store.hash_password("Learner@1234"),
                    "OL",
                    "#2563EB",
                    "#7C3AED",
                    1,
                    82,
                    70,
                    75,
                    10,
                    65,
                    3,
                    1,
                    1,
                    1,
                    "manual",
                    "course-sales-ops",
                    progress,
                    self.store.now_local(),
                    None,
                    2,
                    2,
                    0,
                    "active",
                ),
            )
            conn.commit()

    def test_health_and_login(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["api"], "running")
        self.assertEqual(body["moodle_mode"], "mock")
        self.assertEqual(body["students_loaded"], 42)
        self.assertEqual(body["faculty_loaded"], 4)
        self.assertEqual(body["pending_enrollment_requests"], 4)

        login = self.login("globaladmin", "Global@1234")
        self.assertEqual(login["role"], "super_admin")
        self.assertEqual(login["name"], "Global Admin")
        self.assertTrue(login["is_platform_admin"])
        self.assertEqual(login["org_id"], 1)

        me = self.client.get("/auth/me", headers={"Authorization": f"Bearer {login['access_token']}"})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], "globaladmin@telite.io")
        self.assertEqual(me.json()["org_id"], 1)
        self.assertTrue(me.json()["is_platform_admin"])

        super_admin = self.login("superadmin", "Super@1234")
        self.assertEqual(super_admin["role"], "super_admin")
        self.assertEqual(super_admin["name"], "Rajan Mehra")
        self.assertFalse(super_admin["is_platform_admin"])

    def test_super_admin_dashboard_counts(self):
        headers = self.auth_headers("superadmin", "Super@1234")
        response = self.client.get("/dashboard/super-admin", headers=headers)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["kpis"]["total_categories"], 3)
        self.assertEqual(body["kpis"]["total_courses"], 14)
        self.assertEqual(body["kpis"]["total_learners"], 42)
        self.assertEqual(body["kpis"]["pending_approvals"], 4)
        self.assertEqual(len(body["categories"]), 3)
        self.assertEqual(body["categories"][0]["name"], "ATS")

    def test_approve_batch_enrollment_updates_pending_count(self):
        headers = self.auth_headers("superadmin", "Super@1234")
        before = self.client.get("/dashboard/super-admin", headers=headers).json()
        self.assertEqual(before["kpis"]["pending_approvals"], 4)

        response = self.client.post(
            "/enrol/requests/approve-batch",
            json={"request_ids": ["req-karan-rawat", "req-priya-subramanian"]},
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["approved"], 2)

        after = self.client.get("/dashboard/super-admin", headers=headers).json()
        self.assertEqual(after["kpis"]["pending_approvals"], 2)

        users = self.client.get(
            "/users",
            params={"role": "learner", "category_slug": "ats"},
            headers=headers,
        ).json()
        emails = {user["email"] for user in users["users"]}
        self.assertIn("karan@telite.io", emails)
        self.assertIn("priya.subramanian@telite.io", emails)

    def test_create_task_and_list_it(self):
        headers = self.auth_headers("anika", "Admin@1234")
        response = self.client.post(
            "/tasks",
            json={
                "title": "API schema review",
                "description": "Review the ATS backend response schema.",
                "assigned_label": "Rahul Singh",
                "assigned_to_user_id": "user-rahul-singh",
                "assignment_scope": "individual",
                "category_slug": "ats",
                "due_at": "2026-05-06",
                "status": "pending",
                "notes": "Focus on PAL and enrollment payloads.",
                "is_cross_category": False,
            },
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        task = response.json()
        self.assertEqual(task["title"], "API schema review")

        task_list = self.client.get("/tasks", params={"category_slug": "ats"}, headers=headers)
        self.assertEqual(task_list.status_code, 200)
        titles = {item["title"] for item in task_list.json()["tasks"]}
        self.assertIn("API schema review", titles)

    def test_learner_dashboard_and_launch(self):
        headers = self.auth_headers("rahul", "Learner@1234")
        dashboard = self.client.get("/dashboard/learner", headers=headers)
        self.assertEqual(dashboard.status_code, 200)
        body = dashboard.json()
        self.assertEqual(body["profile"]["full_name"], "Rahul Singh")
        self.assertEqual(body["hero"]["pal_score"], 94.0)
        self.assertEqual(body["stats"]["courses_completed"], 5)

        launch = self.client.get("/courses/course-advanced-postgresql/launch", headers=headers)
        self.assertEqual(launch.status_code, 200)
        self.assertIn("/course/view.php?id=12", launch.json()["launch_url"])

    def test_platform_admin_can_override_org_scope(self):
        self.seed_org2_fixtures()
        headers = self.auth_headers("globaladmin", "Global@1234")

        users = self.client.get("/users", params={"orgId": 2}, headers=headers)
        self.assertEqual(users.status_code, 200)
        emails = {user["email"] for user in users.json()["users"]}
        self.assertIn("org2admin@telite.io", emails)
        self.assertIn("org2learner@telite.io", emails)
        self.assertNotIn("rajan@telite.io", emails)

        categories = self.client.get("/categories", params={"orgId": 2}, headers=headers)
        self.assertEqual(categories.status_code, 200)
        self.assertEqual([category["slug"] for category in categories.json()["categories"]], ["sales"])

        dashboard = self.client.get("/dashboard/super-admin", params={"orgId": 2}, headers=headers)
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["kpis"]["total_categories"], 1)
        self.assertEqual(dashboard.json()["kpis"]["total_courses"], 1)
        self.assertEqual(dashboard.json()["kpis"]["total_learners"], 1)

    def test_tenant_super_admin_is_limited_to_own_org(self):
        self.seed_org2_fixtures()
        headers = self.auth_headers("org2admin", "Admin@1234")

        users = self.client.get("/users", headers=headers)
        self.assertEqual(users.status_code, 200)
        emails = {user["email"] for user in users.json()["users"]}
        self.assertEqual(emails, {"org2admin@telite.io", "org2learner@telite.io"})

        forbidden = self.client.get("/users", params={"orgId": 1}, headers=headers)
        self.assertEqual(forbidden.status_code, 403)

        dashboard = self.client.get("/dashboard/super-admin", headers=headers)
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["kpis"]["total_categories"], 1)
        self.assertEqual(dashboard.json()["kpis"]["total_courses"], 1)
        self.assertEqual(dashboard.json()["kpis"]["total_learners"], 1)

    def test_accept_invitation_creates_session_and_super_admin_access(self):
        self.seed_org2_fixtures()
        invitation = self.store.create_invitation(
            org_id=2,
            email="neworg2admin@telite.io",
            role="company_super_admin",
            invited_by="user-org2-admin",
        )

        response = self.client.post(
            "/api/platform/invitations/accept",
            json={
                "token": invitation["token"],
                "full_name": "New Org Two Admin",
                "password": "Invite@1234",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["role"], "super_admin")
        self.assertEqual(body["org_id"], 2)
        self.assertFalse(body["is_platform_admin"])

        me = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["role"], "super_admin")
        self.assertEqual(me.json()["org_id"], 2)

        dashboard = self.client.get(
            "/dashboard/super-admin",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["kpis"]["total_categories"], 1)
        self.assertEqual(dashboard.json()["kpis"]["total_courses"], 1)

        with self.store.get_conn() as conn:
            row = conn.execute(
                "SELECT accepted_at FROM org_invitations WHERE token = ?",
                (invitation["token"],),
            ).fetchone()
            self.assertIsNotNone(row["accepted_at"])

    def test_forgot_and_reset_password_updates_login_credentials(self):
        forgot = self.client.post("/auth/forgot-password", json={"email": "rajan@telite.io"})
        self.assertEqual(forgot.status_code, 200)
        self.assertEqual(forgot.json()["status"], "ok")

        with self.store.get_conn() as conn:
            row = conn.execute(
                """
                SELECT token
                FROM password_reset_tokens prt
                JOIN users u ON u.id = prt.user_id
                WHERE lower(u.email) = lower(?)
                ORDER BY prt.id DESC
                LIMIT 1
                """,
                ("rajan@telite.io",),
            ).fetchone()
            self.assertIsNotNone(row)
            token = row["token"]

        reset = self.client.post(
            "/auth/reset-password",
            json={"token": token, "password": "SuperReset@1234"},
        )
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.json()["status"], "password_updated")

        old_login = self.client.post(
            "/auth/login",
            data={"username": "superadmin", "password": "Super@1234"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(old_login.status_code, 401)

        new_login = self.client.post(
            "/auth/login",
            data={"username": "superadmin", "password": "SuperReset@1234"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(new_login.status_code, 200)

    def test_signup_student_role_is_counted_by_learner_filters(self):
        headers = self.auth_headers("superadmin", "Super@1234")
        register = self.client.post(
            "/signup/register",
            json={
                "domain_type": "college",
                "role_name": "student",
                "email": "student.one@telite.edu",
                "full_name": "Student One",
                "password": "Student@1234",
                "organization_name": "Telite University",
                "phone": "9999999999",
                "id_number": "STU-001",
                "program": "B.Tech",
                "branch": "CSE",
                "captcha": "12",
            },
        )
        self.assertEqual(register.status_code, 200)
        verification_id = register.json()["verification_id"]

        approve = self.client.post(
            f"/admin/verifications/{verification_id}/approve",
            headers=headers,
        )
        self.assertEqual(approve.status_code, 200)
        self.assertEqual(approve.json()["system_role"], "learner")

        users = self.client.get(
            "/users",
            params={"role": "learner", "query": "student.one", "page_size": 100},
            headers=headers,
        )
        self.assertEqual(users.status_code, 200)
        emails = {user["email"] for user in users.json()["users"]}
        self.assertIn("student.one@telite.edu", emails)

        dashboard = self.client.get("/dashboard/super-admin", headers=headers)
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["kpis"]["total_learners"], 43)

        student_login = self.login("student.one@telite.edu", "Student@1234")
        self.assertEqual(student_login["role"], "learner")


if __name__ == "__main__":
    unittest.main()
