import importlib
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# ── Test credentials — set via env so no hardcoded passwords in source ────────
# These are only used in the test environment (TELITE_DB_BACKEND=sqlite).
TEST_ADMIN_PASSWORD = os.getenv("TELITE_SEED_ADMIN_PASSWORD", "Dev-Admin-2024!")
TEST_LEARNER_PASSWORD = os.getenv("TELITE_SEED_LEARNER_PASSWORD", "Dev-Learner-2024!")


class TeliteApiTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["TELITE_DB_BACKEND"] = "sqlite"
        os.environ["TELITE_DB_PATH"] = os.path.join(self.tempdir.name, "test_telite_lms.db")
        os.environ.pop("TELITE_DATABASE_URL", None)
        os.environ.pop("TELITE_SQLITE_SOURCE_PATH", None)
        os.environ["MOODLE_MODE"] = "mock"
        os.environ["SMTP_USER"] = ""
        os.environ["SMTP_PASSWORD"] = ""
        # Ensure test uses the same seed passwords
        os.environ["TELITE_SEED_ADMIN_PASSWORD"] = TEST_ADMIN_PASSWORD
        os.environ["TELITE_SEED_LEARNER_PASSWORD"] = TEST_LEARNER_PASSWORD
        # Disable Redis for tests — use in-memory rate limiting
        os.environ["REDIS_ENABLED"] = "false"
        main = importlib.import_module("main")
        importlib.reload(main)
        self.store = importlib.import_module("telite_store")
        importlib.reload(self.store)
        from app.core import rate_limiter
        rate_limiter.clear_all_attempts()
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
                    self.store.hash_password(TEST_ADMIN_PASSWORD),
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
                    self.store.hash_password(TEST_LEARNER_PASSWORD),
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

        login = self.login("globaladmin", TEST_ADMIN_PASSWORD)
        self.assertEqual(login["role"], "super_admin")
        self.assertEqual(login["name"], "Global Admin")
        self.assertTrue(login["is_platform_admin"])
        self.assertEqual(login["org_id"], 1)

        me = self.client.get("/auth/me", headers={"Authorization": f"Bearer {login['access_token']}"})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], "globaladmin@telite.io")
        self.assertEqual(me.json()["org_id"], 1)
        self.assertTrue(me.json()["is_platform_admin"])

        super_admin = self.login("superadmin", TEST_ADMIN_PASSWORD)
        self.assertEqual(super_admin["role"], "super_admin")
        self.assertEqual(super_admin["name"], "Rajan Mehra")
        self.assertFalse(super_admin["is_platform_admin"])

    def test_super_admin_dashboard_counts(self):
        headers = self.auth_headers("superadmin", TEST_ADMIN_PASSWORD)
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
        headers = self.auth_headers("superadmin", TEST_ADMIN_PASSWORD)
        before = self.client.get("/dashboard/super-admin", headers=headers).json()
        self.assertEqual(before["kpis"]["pending_approvals"], 4)

        response = self.client.post(
            "/enrol/requests/approve-batch",
            json={"request_ids": ["req-karan-rawat", "req-priya-subramanian"]},
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        batch_body = response.json()
        self.assertEqual(batch_body["approved"], 2)
        self.assertIn("job_id", batch_body)
        self.assertEqual(batch_body["failed"], 0)
        self.assertEqual(batch_body["requested"], 2)

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

        with self.store.get_conn() as conn:
            audit_row = conn.execute(
                """
                SELECT action, target_id, result
                FROM audit_log
                WHERE action = 'enrol.approve_batch' AND target_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (batch_body["job_id"],),
            ).fetchone()
            self.assertIsNotNone(audit_row)
            self.assertEqual(audit_row["result"], "success")

    def test_create_task_and_list_it(self):
        headers = self.auth_headers("anika", TEST_ADMIN_PASSWORD)
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
        headers = self.auth_headers("rahul", TEST_LEARNER_PASSWORD)
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
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

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

    def test_platform_org_detail_returns_refresh_ready_sections(self):
        self.seed_org2_fixtures()
        self.store.upsert_moodle_tenant(2, 2201)
        self.store.update_moodle_tenant_sync(2, status="successful")
        self.store.create_moodle_sync_log(
            org_id=2,
            event_type="tenant_sync",
            status="successful",
            message="Org 2 tenant sync completed",
            moodle_tenant_id=2201,
        )
        self.store.create_invitation(
            org_id=2,
            email="pending-admin@org2.telite.io",
            role="super_admin",
            invited_by="user-global-admin",
        )
        self.store.write_platform_audit(
            action="org.refresh_test",
            actor_id="user-global-admin",
            actor_name="Global Admin",
            org_id=2,
            target_type="org",
            target_id="2",
            message="Prepared org 2 refresh payload",
        )

        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        response = self.client.get("/api/platform/organizations/2", headers=headers)
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["id"], 2)
        self.assertEqual(body["user_count"], 2)
        self.assertEqual(body["course_count"], 1)
        self.assertEqual(body["stats"]["total_users"], 2)
        self.assertEqual(body["stats"]["admin_users"], 1)
        self.assertEqual(body["stats"]["learner_users"], 1)
        self.assertEqual(body["stats"]["pending_invitations"], 1)
        self.assertEqual(body["sync_summary"]["sync_status"], "successful")
        self.assertTrue(body["sync_summary"]["tenant_connected"])
        self.assertEqual(len(body["recent_sync_logs"]), 1)
        self.assertEqual(body["recent_sync_logs"][0]["message"], "Org 2 tenant sync completed")
        self.assertEqual(len(body["pending_invitations"]), 1)
        self.assertEqual(body["pending_invitations"][0]["email"], "pending-admin@org2.telite.io")
        self.assertTrue(body["recent_audit"])
        self.assertEqual(body["recent_audit"][0]["action"], "org.refresh_test")
        self.assertEqual(body["super_admin"]["id"], "user-org2-admin")
        self.assertTrue(body["refreshed_at"])

    def test_platform_org_update_normalizes_values(self):
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        response = self.client.patch(
            "/api/platform/organizations/2",
            json={
                "name": "  Telite Systems International  ",
                "domain": "  NewDomain.Example.COM  ",
                "slug": "  Telite Systems Enterprise  ",
                "logo_url": "  https://cdn.telite.io/logo.svg  ",
            },
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["name"], "Telite Systems International")
        self.assertEqual(body["domain"], "newdomain.example.com")
        self.assertEqual(body["slug"], "telite-systems-enterprise")
        self.assertEqual(body["logo_url"], "https://cdn.telite.io/logo.svg")

    def test_platform_org_update_rejects_duplicate_domain(self):
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        response = self.client.patch(
            "/api/platform/organizations/2",
            json={"domain": "telite.edu"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("already in use", response.json()["detail"])

    def test_platform_org_create_rolls_back_when_invitation_setup_fails(self):
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        store_module = importlib.import_module("app.services.store")
        with mock.patch.object(
            store_module,
            "_insert_org_invitation",
            side_effect=ValueError("Invitation creation failed inside transaction"),
        ):
            response = self.client.post(
                "/api/platform/organizations",
                json={
                    "name": "Rollback Org",
                    "type": "company",
                    "domain": "rollback.example.com",
                    "slug": "rollback-org",
                    "super_admin_email": "owner@rollback.example.com",
                    "moodle_setup": "manual",
                },
                headers=headers,
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "Invitation creation failed inside transaction")

        with self.store.get_conn() as conn:
            org_row = conn.execute(
                "SELECT id FROM organizations WHERE lower(domain) = lower(?)",
                ("rollback.example.com",),
            ).fetchone()
            self.assertIsNone(org_row)

            tenant_row = conn.execute(
                """
                SELECT mt.org_id
                FROM moodle_tenants mt
                JOIN organizations o ON o.id = mt.org_id
                WHERE lower(o.domain) = lower(?)
                """,
                ("rollback.example.com",),
            ).fetchone()
            self.assertIsNone(tenant_row)

    def test_platform_moodle_logs_endpoint_returns_filtered_rows(self):
        self.seed_org2_fixtures()
        self.store.upsert_moodle_tenant(2, 2201)
        self.store.create_moodle_sync_log(
            org_id=2,
            event_type="sync.complete",
            status="successful",
            message="Sales tenant sync completed",
            moodle_tenant_id=2201,
            category_identifier="CAT-200",
            duration_ms=1200,
            metadata={"source": "manual"},
        )
        self.store.create_moodle_sync_log(
            org_id=2,
            event_type="sync.fail",
            status="failed",
            message="Sales tenant sync failed",
            moodle_tenant_id=2201,
            category_identifier="CAT-200",
            duration_ms=30000,
        )
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.get(
            "/api/platform/moodle/logs",
            params={"org_id": 2, "status": "successful", "query": "sales"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(len(body["logs"]), 1)

        log = body["logs"][0]
        self.assertEqual(log["org_id"], 2)
        self.assertEqual(log["tenant"], "Telite Systems")
        self.assertEqual(log["event"], "sync.complete")
        self.assertEqual(log["status_label"], "completed")
        self.assertEqual(log["catId"], "CAT-200")
        self.assertEqual(log["duration_label"], "1.2s")
        self.assertEqual(log["metadata"]["source"], "manual")
        self.assertEqual(log["tenant_sync_status"], "pending")
        self.assertTrue(log["ts"])

    def test_platform_org_sync_returns_job_summary_and_persists_lifecycle(self):
        self.seed_org2_fixtures()
        self.store.upsert_moodle_tenant(2, 2201)
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.post("/api/platform/moodle/sync/2", headers=headers)
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["org_id"], 2)
        self.assertEqual(body["org_name"], "Telite Systems")
        self.assertEqual(body["tenant"]["org_id"], 2)
        self.assertEqual(body["tenant"]["sync_status"], "successful")
        self.assertIn("job_id", body["sync_job"])
        self.assertEqual(body["sync_job"]["status"], "successful")
        self.assertEqual(body["sync_job"]["category_identifier"], "ORG-002")
        self.assertEqual(body["sync_job"]["counts"]["users_lms"], 2)
        self.assertEqual(body["sync_job"]["counts"]["users_moodle"], 2)
        self.assertEqual(body["sync_job"]["counts"]["courses"], 1)
        self.assertEqual(body["sync_job"]["counts"]["enrollments"], 0)

        with self.store.get_conn() as conn:
            tenant_row = conn.execute(
                "SELECT sync_status, total_users_lms, total_users_moodle, total_courses, total_enrollments FROM moodle_tenants WHERE org_id = ?",
                (2,),
            ).fetchone()
            self.assertIsNotNone(tenant_row)
            self.assertEqual(tenant_row["sync_status"], "successful")
            self.assertEqual(tenant_row["total_users_lms"], 2)
            self.assertEqual(tenant_row["total_users_moodle"], 2)
            self.assertEqual(tenant_row["total_courses"], 1)
            self.assertEqual(tenant_row["total_enrollments"], 0)

            log_rows = conn.execute(
                """
                SELECT event_type, status, metadata_json
                FROM moodle_sync_logs
                WHERE org_id = ?
                ORDER BY id ASC
                """,
                (2,),
            ).fetchall()
            self.assertEqual([(row["event_type"], row["status"]) for row in log_rows], [
                ("sync.start", "in_progress"),
                ("sync.complete", "successful"),
            ])
            self.assertIn(body["sync_job"]["job_id"], log_rows[0]["metadata_json"])
            self.assertIn(body["sync_job"]["job_id"], log_rows[1]["metadata_json"])

            audit_row = conn.execute(
                """
                SELECT action, target_id
                FROM audit_log
                WHERE action = 'moodle.sync' AND target_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                ("2",),
            ).fetchone()
            self.assertIsNotNone(audit_row)
            self.assertEqual(audit_row["action"], "moodle.sync")
            self.assertEqual(audit_row["target_id"], "2")

    def test_platform_sync_all_returns_batch_summary_and_audit(self):
        self.seed_org2_fixtures()
        self.store.upsert_moodle_tenant(1, 1101)
        self.store.upsert_moodle_tenant(2, 2201)
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.post("/api/platform/moodle/sync-all", headers=headers)
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertIn("job_id", body)
        self.assertEqual(body["triggered"], 2)
        self.assertEqual(body["successful"], 2)
        self.assertEqual(body["failed"], 0)
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["results"][0]["status"], "successful")
        self.assertIn("sync_job", body["results"][0])
        self.assertIn("job_id", body["results"][0]["sync_job"])
        self.assertGreaterEqual(body["duration_ms"], 0)

        with self.store.get_conn() as conn:
            audit_row = conn.execute(
                """
                SELECT action, target_id, metadata_json
                FROM audit_log
                WHERE action = 'moodle.sync_all' AND target_id = 'all'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            self.assertIsNotNone(audit_row)
            self.assertEqual(audit_row["action"], "moodle.sync_all")
            self.assertEqual(audit_row["target_id"], "all")
            self.assertIn(body["job_id"], audit_row["metadata_json"])

            sync_complete_rows = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM moodle_sync_logs
                WHERE event_type = 'sync.complete'
                """
            ).fetchone()
            self.assertGreaterEqual(sync_complete_rows["count"], 2)

    def test_platform_moodle_report_summary_returns_kpis_and_health_rows(self):
        self.seed_org2_fixtures()
        self.store.upsert_moodle_tenant(2, 2201)
        self.store.create_moodle_sync_log(
            org_id=2,
            event_type="sync.complete",
            status="successful",
            message="First sync completed",
            category_identifier="CAT-200",
            duration_ms=1000,
        )
        self.store.create_moodle_sync_log(
            org_id=2,
            event_type="sync.fail",
            status="failed",
            message="Second sync failed",
            category_identifier="CAT-200",
            duration_ms=3000,
        )
        self.store.create_moodle_sync_log(
            org_id=2,
            event_type="sync.complete",
            status="successful",
            message="Third sync completed",
            category_identifier="CAT-200",
            duration_ms=2000,
        )
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.get("/api/platform/moodle/reports/summary", params={"days": 30}, headers=headers)
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["window_days"], 30)
        self.assertEqual(body["kpis"]["total_syncs"], 3)
        self.assertEqual(body["kpis"]["failed_syncs"], 1)
        self.assertEqual(body["kpis"]["successful_syncs"], 2)
        self.assertEqual(body["kpis"]["avg_duration_ms"], 2000.0)
        self.assertEqual(body["kpis"]["avg_duration_label"], "2.0s")
        self.assertEqual(body["kpis"]["success_rate"], 66.7)
        self.assertTrue(body["trend"])
        self.assertEqual(body["trend"][0]["total"], 3)
        self.assertEqual(body["trend"][0]["success_rate"], 66.7)
        self.assertTrue(body["health_rows"])
        self.assertEqual(body["health_rows"][0]["category_identifier"], "CAT-200")
        self.assertEqual(body["health_rows"][0]["tenant"], "Telite Systems")
        self.assertEqual(body["health_rows"][0]["total_syncs"], 3)
        self.assertEqual(body["health_rows"][0]["success_rate"], 66.7)
        self.assertEqual(body["health_rows"][0]["avg_duration_label"], "2.0s")

    def test_tenant_super_admin_is_limited_to_own_org(self):
        self.seed_org2_fixtures()
        headers = self.auth_headers("org2admin", TEST_ADMIN_PASSWORD)

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

    def test_platform_admin_invite_tracks_delivery_failure_state(self):
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        response = self.client.post(
            "/api/platform/admins/invite",
            json={
                "org_id": 2,
                "email": "delivery-check@telite.io",
                "role": "super_admin",
            },
            headers=headers,
        )
        self.assertEqual(response.status_code, 201)
        invitation = response.json()["invitation"]
        self.assertEqual(invitation["email"], "delivery-check@telite.io")
        self.assertEqual(invitation["delivery_status"], "failed")
        self.assertEqual(
            invitation["delivery_error"],
            "SMTP not configured or invitation email delivery failed",
        )
        self.assertIsNotNone(invitation["delivery_attempted_at"])

        with self.store.get_conn() as conn:
            row = conn.execute(
                """
                SELECT delivery_status, delivery_error, delivery_attempted_at
                FROM org_invitations
                WHERE id = ?
                """,
                (invitation["id"],),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["delivery_status"], "failed")
            self.assertEqual(
                row["delivery_error"],
                "SMTP not configured or invitation email delivery failed",
            )
            self.assertIsNotNone(row["delivery_attempted_at"])

    def test_platform_admin_can_resend_pending_invitation(self):
        invitation = self.store.create_invitation(
            org_id=2,
            email="resend-check@telite.io",
            role="super_admin",
            invited_by="user-global-admin",
        )
        old_last_sent_at = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M")
        with self.store.get_conn() as conn:
            conn.execute(
                "UPDATE org_invitations SET last_sent_at = ? WHERE id = ?",
                (old_last_sent_at, invitation["id"]),
            )
            conn.commit()

        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        with mock.patch("app.api.routes.platform.send_invitation_email", return_value=True):
            response = self.client.post(
                f"/api/platform/admins/invitations/{invitation['id']}/resend",
                headers=headers,
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()["invitation"]
        self.assertEqual(body["id"], invitation["id"])
        self.assertEqual(body["email"], "resend-check@telite.io")
        self.assertEqual(body["resend_count"], 1)
        self.assertEqual(body["delivery_status"], "delivered")
        self.assertIsNotNone(body["last_resent_at"])
        self.assertIsNotNone(body["delivery_attempted_at"])
        self.assertIsNotNone(body["delivered_at"])

        with self.store.get_conn() as conn:
            invitation_row = conn.execute(
                """
                SELECT resend_count, last_resent_at, delivery_status
                FROM org_invitations
                WHERE id = ?
                """,
                (invitation["id"],),
            ).fetchone()
            self.assertIsNotNone(invitation_row)
            self.assertEqual(invitation_row["resend_count"], 1)
            self.assertIsNotNone(invitation_row["last_resent_at"])
            self.assertEqual(invitation_row["delivery_status"], "delivered")

            audit_row = conn.execute(
                """
                SELECT action, target_id
                FROM audit_log
                WHERE action = 'invite.resend' AND target_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (str(invitation["id"]),),
            ).fetchone()
            self.assertIsNotNone(audit_row)
            self.assertEqual(audit_row["action"], "invite.resend")

    def test_platform_admin_resend_invitation_is_rate_limited(self):
        invitation = self.store.create_invitation(
            org_id=2,
            email="rate-limit-resend@telite.io",
            role="super_admin",
            invited_by="user-global-admin",
        )
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.post(
            f"/api/platform/admins/invitations/{invitation['id']}/resend",
            headers=headers,
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("already sent recently", response.json()["detail"])

        with self.store.get_conn() as conn:
            invitation_row = conn.execute(
                "SELECT resend_count, last_resent_at FROM org_invitations WHERE id = ?",
                (invitation["id"],),
            ).fetchone()
            self.assertIsNotNone(invitation_row)
            self.assertEqual(invitation_row["resend_count"], 0)
            self.assertIsNone(invitation_row["last_resent_at"])

    def test_platform_admin_can_revoke_pending_invitation(self):
        invitation = self.store.create_invitation(
            org_id=2,
            email="revoke-check@telite.io",
            role="super_admin",
            invited_by="user-global-admin",
        )
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.delete(
            f"/api/platform/admins/invitations/{invitation['id']}",
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()["invitation"]
        self.assertEqual(body["id"], invitation["id"])
        self.assertEqual(body["email"], "revoke-check@telite.io")
        self.assertEqual(body["revoked_by"], "user-global-admin")
        self.assertIsNotNone(body["revoked_at"])
        self.assertEqual(body["org_name"], "Telite Systems")

        admins_response = self.client.get("/api/platform/admins", headers=headers)
        self.assertEqual(admins_response.status_code, 200)
        pending_emails = {item["email"] for item in admins_response.json()["pending_invitations"]}
        self.assertNotIn("revoke-check@telite.io", pending_emails)

        with self.store.get_conn() as conn:
            invitation_row = conn.execute(
                """
                SELECT revoked_at, revoked_by
                FROM org_invitations
                WHERE id = ?
                """,
                (invitation["id"],),
            ).fetchone()
            self.assertIsNotNone(invitation_row)
            self.assertIsNotNone(invitation_row["revoked_at"])
            self.assertEqual(invitation_row["revoked_by"], "user-global-admin")

            audit_row = conn.execute(
                """
                SELECT action, target_id
                FROM audit_log
                WHERE action = 'invite.revoke' AND target_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (str(invitation["id"]),),
            ).fetchone()
            self.assertIsNotNone(audit_row)
            self.assertEqual(audit_row["action"], "invite.revoke")

    def test_platform_admin_cannot_revoke_invitation_twice(self):
        invitation = self.store.create_invitation(
            org_id=2,
            email="revoke-twice@telite.io",
            role="super_admin",
            invited_by="user-global-admin",
        )
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        first_response = self.client.delete(
            f"/api/platform/admins/invitations/{invitation['id']}",
            headers=headers,
        )
        self.assertEqual(first_response.status_code, 200)

        second_response = self.client.delete(
            f"/api/platform/admins/invitations/{invitation['id']}",
            headers=headers,
        )
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(second_response.json()["detail"], "Invitation has already been revoked.")

    def test_platform_admin_can_delete_admin_and_revoke_sessions(self):
        admin_login = self.login("superadmin", TEST_ADMIN_PASSWORD)
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
                    "user-org1-admin-backup",
                    "org1backupadmin",
                    "org1backup@telite.io",
                    "Org One Backup Admin",
                    "super_admin",
                    None,
                    self.store.hash_password(TEST_ADMIN_PASSWORD),
                    "OB",
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
                    1,
                    1,
                    0,
                    "active",
                ),
            )
            conn.commit()
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.delete(
            "/api/platform/admins/user-rajan-mehra",
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["deleted"])
        self.assertEqual(body["user"]["id"], "user-rajan-mehra")
        self.assertFalse(body["user"]["is_active"])
        self.assertGreaterEqual(body["revoked_sessions"], 1)

        with self.store.get_conn() as conn:
            user_row = conn.execute(
                "SELECT is_active, status FROM users WHERE id = ?",
                ("user-rajan-mehra",),
            ).fetchone()
            self.assertIsNotNone(user_row)
            self.assertEqual(user_row["is_active"], 0)
            self.assertEqual(user_row["status"], "inactive")

            session_row = conn.execute(
                """
                SELECT revoked_at
                FROM auth_sessions
                WHERE user_id = ? AND refresh_token = ?
                LIMIT 1
                """,
                ("user-rajan-mehra", admin_login["refresh_token"]),
            ).fetchone()
            self.assertIsNotNone(session_row)
            self.assertIsNotNone(session_row["revoked_at"])

            audit_row = conn.execute(
                """
                SELECT action, target_id
                FROM audit_log
                WHERE action = 'admin.delete' AND target_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                ("user-rajan-mehra",),
            ).fetchone()
            self.assertIsNotNone(audit_row)
            self.assertEqual(audit_row["action"], "admin.delete")

    def test_platform_admin_cannot_delete_own_account(self):
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.delete(
            "/api/platform/admins/user-global-admin",
            headers=headers,
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "You cannot delete your own platform admin account",
        )

    def test_platform_admin_cannot_delete_last_active_org_admin(self):
        self.seed_org2_fixtures()
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.delete(
            "/api/platform/admins/user-org2-admin",
            headers=headers,
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "Cannot delete the last active admin for this organization",
        )

    def test_platform_admin_list_supports_filters_and_admin_pagination(self):
        self.seed_org2_fixtures()
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
                    "user-org2-category-admin",
                    "org2categoryadmin",
                    "ops-admin@org2.telite.io",
                    "Ops Admin",
                    "category_admin",
                    "sales",
                    self.store.hash_password(TEST_ADMIN_PASSWORD),
                    "OA",
                    "#2563EB",
                    "#0891B2",
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
                    "suspended",
                ),
            )
            conn.commit()
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.get(
            "/api/platform/admins",
            params={
                "role": "category_admin",
                "status": "suspended",
                "org_id": 2,
                "query": "ops",
                "page": 1,
                "limit": 1,
            },
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["admins"]), 1)
        self.assertEqual(body["admins"][0]["id"], "user-org2-category-admin")
        self.assertEqual(body["pending_invitations"], [])
        self.assertEqual(body["filters"]["role"], "category_admin")
        self.assertEqual(body["filters"]["status"], "suspended")
        self.assertEqual(body["filters"]["org_id"], 2)
        self.assertEqual(body["pagination"]["admins"]["total"], 1)
        self.assertEqual(body["pagination"]["admins"]["page"], 1)
        self.assertEqual(body["pagination"]["admins"]["limit"], 1)
        self.assertEqual(body["pagination"]["admins"]["total_pages"], 1)
        self.assertEqual(body["pagination"]["pending_invitations"]["total"], 0)

    def test_platform_admin_list_supports_pending_invitation_pagination(self):
        self.seed_org2_fixtures()
        self.store.create_invitation(
            org_id=2,
            email="pending-admin-one@org2.telite.io",
            role="super_admin",
            invited_by="user-global-admin",
        )
        self.store.create_invitation(
            org_id=2,
            email="pending-admin-two@org2.telite.io",
            role="category_admin",
            invited_by="user-global-admin",
        )
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.get(
            "/api/platform/admins",
            params={
                "status": "pending",
                "org_id": 2,
                "query": "pending-admin",
                "page": 2,
                "limit": 1,
            },
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["admins"], [])
        self.assertEqual(len(body["pending_invitations"]), 1)
        self.assertEqual(body["filters"]["status"], "pending")
        self.assertEqual(body["pagination"]["admins"]["total"], 0)
        self.assertEqual(body["pagination"]["pending_invitations"]["total"], 2)
        self.assertEqual(body["pagination"]["pending_invitations"]["page"], 2)
        self.assertEqual(body["pagination"]["pending_invitations"]["limit"], 1)
        self.assertEqual(body["pagination"]["pending_invitations"]["total_pages"], 2)
        returned_email = body["pending_invitations"][0]["email"]
        self.assertIn(returned_email, {"pending-admin-one@org2.telite.io", "pending-admin-two@org2.telite.io"})

    def test_platform_analytics_export_returns_csv_and_audit_log(self):
        self.seed_org2_fixtures()
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.get(
            "/api/platform/analytics/export",
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        self.assertIn("attachment;", response.headers["content-disposition"])
        csv_text = response.text
        self.assertIn("section,metric,value", csv_text)
        self.assertIn("overview,total_orgs", csv_text)
        self.assertIn("section,org_id,org_name,org_type,user_count", csv_text)
        self.assertIn("Telite Systems", csv_text)
        self.assertIn("section,created_at,actor_name,action,target_type,target_id,message", csv_text)

        with self.store.get_conn() as conn:
            audit_row = conn.execute(
                """
                SELECT action, target_id
                FROM audit_log
                WHERE action = 'analytics.export' AND target_id = 'platform_overview'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            self.assertIsNotNone(audit_row)
            self.assertEqual(audit_row["action"], "analytics.export")

    def test_platform_audit_export_returns_filtered_csv_and_audit_log(self):
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        self.store.write_platform_audit(
            action="invite.resend",
            actor_id="user-global-admin",
            actor_name="Global Admin",
            org_id=2,
            target_type="invitation",
            target_id="invite-123",
            message="Resent invitation to org 2 admin",
            severity="INFO",
            metadata={"email": "pending-admin@org2.telite.io"},
        )
        self.store.write_platform_audit(
            action="feature.toggle",
            actor_id="user-global-admin",
            actor_name="Global Admin",
            org_id=1,
            target_type="feature",
            target_id="analytics_dashboard",
            message="Enabled analytics dashboard",
            severity="WARN",
        )

        response = self.client.get(
            "/api/platform/audit/export",
            params={"org_id": 2, "action": "invite", "severity": "INFO"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        self.assertIn("attachment;", response.headers["content-disposition"])
        csv_text = response.text
        self.assertIn("created_at,severity,org_id,actor_user_id,actor_name,action,target_type,target_id,result,message,ip_address,metadata_json", csv_text)
        self.assertIn("invite.resend", csv_text)
        self.assertIn("Resent invitation to org 2 admin", csv_text)
        self.assertNotIn("feature.toggle", csv_text)

        with self.store.get_conn() as conn:
            audit_row = conn.execute(
                """
                SELECT action, target_id, metadata_json
                FROM audit_log
                WHERE action = 'audit.export' AND target_id = 'platform_audit_log'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            self.assertIsNotNone(audit_row)
            self.assertEqual(audit_row["action"], "audit.export")
            self.assertIn('"row_count": 1', audit_row["metadata_json"])
            self.assertIn('"severity": "INFO"', audit_row["metadata_json"])

    def test_platform_audit_list_supports_expanded_filters_and_query(self):
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        self.store.write_platform_audit(
            action="admin.delete",
            actor_id="user-global-admin",
            actor_name="Global Admin",
            org_id=2,
            target_type="user",
            target_id="user-org2-admin",
            message="Removed duplicate org admin account",
            severity="WARN",
            result="success",
            ip_address="10.20.30.40",
            metadata={"reason": "duplicate cleanup"},
        )
        self.store.write_platform_audit(
            action="feature.toggle",
            actor_id="user-global-admin",
            actor_name="Global Admin",
            org_id=1,
            target_type="feature",
            target_id="analytics_dashboard",
            message="Enabled analytics dashboard",
            severity="INFO",
            result="success",
            ip_address="10.20.30.41",
        )

        response = self.client.get(
            "/api/platform/audit",
            params={
                "actor_name": "global",
                "target_type": "user",
                "target_id": "org2-admin",
                "result": "SUCCESS",
                "query": "duplicate cleanup",
                "severity": "WARN",
            },
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(len(body["logs"]), 1)
        log = body["logs"][0]
        self.assertEqual(log["action"], "admin.delete")
        self.assertEqual(log["target_type"], "user")
        self.assertEqual(log["target_id"], "user-org2-admin")
        self.assertEqual(log["result"], "success")
        self.assertEqual(log["ip_address"], "10.20.30.40")

    def test_platform_org_analytics_detail_returns_expanded_sections(self):
        self.seed_org2_fixtures()
        self.store.upsert_moodle_tenant(2, 2201)
        self.store.update_moodle_tenant_sync(
            2,
            status="successful",
            total_users_lms=2,
            total_users_moodle=2,
            total_courses=1,
            total_enrollments=0,
        )
        self.store.create_moodle_sync_log(
            org_id=2,
            event_type="sync.complete",
            status="successful",
            message="Org 2 analytics sync completed",
            moodle_tenant_id=2201,
            duration_ms=1800,
        )
        self.store.write_platform_audit(
            action="analytics.detail_test",
            actor_id="user-global-admin",
            actor_name="Global Admin",
            org_id=2,
            target_type="analytics",
            target_id="2",
            message="Prepared analytics detail payload",
        )
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.get(
            "/api/platform/analytics/org/2",
            params={"days": 30},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["org_id"], 2)
        self.assertEqual(body["org_name"], "Telite Systems")
        self.assertEqual(body["window_days"], 30)
        self.assertEqual(body["kpis"]["total_users"], 2)
        self.assertEqual(body["kpis"]["admin_users"], 1)
        self.assertEqual(body["kpis"]["learner_users"], 1)
        self.assertEqual(body["kpis"]["course_count"], 1)
        self.assertIn("storage", body)
        self.assertIn("session_analytics", body)
        self.assertIn("sync_summary", body)
        self.assertEqual(body["sync_summary"]["status"], "successful")
        self.assertEqual(body["sync_summary"]["successful_syncs"], 1)
        self.assertTrue(body["users_by_role"])
        self.assertTrue(body["recent_activity"])
        self.assertEqual(body["recent_activity"][0]["action"], "analytics.detail_test")
        self.assertIsNotNone(body["moodle_tenant"])
        self.assertIn(body["health"], {"excellent", "stable", "warning"})

    def test_platform_admin_can_create_analytics_alert_rule(self):
        self.seed_org2_fixtures()
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.post(
            "/api/platform/analytics/alerts",
            json={
                "org_id": 2,
                "metric": "storage_used_pct",
                "threshold": 85,
                "channel": "email",
            },
            headers=headers,
        )

        self.assertEqual(response.status_code, 201)
        rule = response.json()["rule"]
        self.assertEqual(rule["org_id"], 2)
        self.assertEqual(rule["metric"], "storage_used_pct")
        self.assertEqual(rule["threshold"], 85)
        self.assertEqual(rule["channel"], "email")
        self.assertEqual(rule["created_by"], "user-global-admin")

        detail = self.client.get(
            "/api/platform/analytics/org/2",
            headers=headers,
        )
        self.assertEqual(detail.status_code, 200)
        detail_body = detail.json()
        self.assertTrue(detail_body["alert_rules"])
        self.assertEqual(detail_body["alert_rules"][0]["metric"], "storage_used_pct")

        with self.store.get_conn() as conn:
            audit_row = conn.execute(
                """
                SELECT action, target_id
                FROM audit_log
                WHERE action = 'analytics.alert.create'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            self.assertIsNotNone(audit_row)
            self.assertEqual(audit_row["action"], "analytics.alert.create")

    def test_platform_admin_can_update_existing_analytics_alert_rule(self):
        self.seed_org2_fixtures()
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        first = self.client.post(
            "/api/platform/analytics/alerts",
            json={
                "org_id": 2,
                "metric": "storage_used_pct",
                "threshold": 85,
                "channel": "email",
            },
            headers=headers,
        )
        self.assertEqual(first.status_code, 201)
        first_rule_id = first.json()["rule"]["id"]

        second = self.client.post(
            "/api/platform/analytics/alerts",
            json={
                "org_id": 2,
                "metric": "storage_used_pct",
                "threshold": 92,
                "channel": "email",
            },
            headers=headers,
        )
        self.assertEqual(second.status_code, 201)
        second_rule = second.json()["rule"]
        self.assertEqual(second_rule["id"], first_rule_id)
        self.assertEqual(second_rule["threshold"], 92)

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
            data={"username": "superadmin", "password": TEST_ADMIN_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(old_login.status_code, 401)

        new_login = self.client.post(
            "/auth/login",
            data={"username": "superadmin", "password": "SuperReset@1234"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(new_login.status_code, 200)

    def test_forgot_password_tracks_delivery_failure_state(self):
        response = self.client.post("/auth/forgot-password", json={"email": "rajan@telite.io"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

        with self.store.get_conn() as conn:
            row = conn.execute(
                """
                SELECT delivery_status, delivery_error, delivery_attempted_at
                FROM password_reset_tokens prt
                JOIN users u ON u.id = prt.user_id
                WHERE lower(u.email) = lower(?)
                ORDER BY prt.id DESC
                LIMIT 1
                """,
                ("rajan@telite.io",),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["delivery_status"], "failed")
            self.assertEqual(
                row["delivery_error"],
                "SMTP not configured or password reset email delivery failed",
            )
            self.assertIsNotNone(row["delivery_attempted_at"])

    def test_platform_admin_can_trigger_admin_password_reset(self):
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        response = self.client.post(
            "/api/platform/admins/user-rajan-mehra/reset-password",
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "reset_requested")
        self.assertEqual(response.json()["user_id"], "user-rajan-mehra")
        self.assertEqual(response.json()["delivery_status"], "failed")
        self.assertEqual(
            response.json()["delivery_error"],
            "SMTP not configured or password reset email delivery failed",
        )
        self.assertIsNotNone(response.json()["delivery_attempted_at"])

        with self.store.get_conn() as conn:
            token_row = conn.execute(
                """
                SELECT prt.token, prt.delivery_status, prt.delivery_error, prt.delivery_attempted_at
                FROM password_reset_tokens prt
                JOIN users u ON u.id = prt.user_id
                WHERE u.id = ?
                ORDER BY prt.id DESC
                LIMIT 1
                """,
                ("user-rajan-mehra",),
            ).fetchone()
            self.assertIsNotNone(token_row)
            self.assertEqual(token_row["delivery_status"], "failed")
            self.assertEqual(
                token_row["delivery_error"],
                "SMTP not configured or password reset email delivery failed",
            )
            self.assertIsNotNone(token_row["delivery_attempted_at"])

            audit_row = conn.execute(
                """
                SELECT action, target_id
                FROM audit_log
                WHERE action = 'admin.password_reset' AND target_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                ("user-rajan-mehra",),
            ).fetchone()
            self.assertIsNotNone(audit_row)
            self.assertEqual(audit_row["action"], "admin.password_reset")
            self.assertEqual(audit_row["target_id"], "user-rajan-mehra")

    def test_login_rate_limit_blocks_repeated_failed_attempts(self):
        for _ in range(5):
            failed = self.client.post(
                "/auth/login",
                data={"username": "superadmin", "password": "wrong-password"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            self.assertEqual(failed.status_code, 401)

        limited = self.client.post(
            "/auth/login",
            data={"username": "superadmin", "password": "wrong-password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.json()["detail"], "Too many requests. Please try again later.")
        self.assertIn("Retry-After", limited.headers)

    def test_forgot_password_rate_limit_blocks_repeated_requests(self):
        for _ in range(3):
            response = self.client.post(
                "/auth/forgot-password",
                json={"email": "rajan@telite.io"},
            )
            self.assertEqual(response.status_code, 200)

        limited = self.client.post(
            "/auth/forgot-password",
            json={"email": "rajan@telite.io"},
        )
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.json()["detail"], "Too many requests. Please try again later.")
        self.assertIn("Retry-After", limited.headers)

    def test_platform_sync_all_rate_limit_blocks_repeated_requests(self):
        self.seed_org2_fixtures()
        self.store.upsert_moodle_tenant(1, 1101)
        self.store.upsert_moodle_tenant(2, 2201)
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        for _ in range(2):
            response = self.client.post("/api/platform/moodle/sync-all", headers=headers)
            self.assertEqual(response.status_code, 200)

        limited = self.client.post("/api/platform/moodle/sync-all", headers=headers)
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.json()["detail"], "Too many requests. Please try again later.")
        self.assertIn("Retry-After", limited.headers)

    def test_enrollment_batch_approve_rate_limit_blocks_repeated_requests(self):
        headers = self.auth_headers("superadmin", TEST_ADMIN_PASSWORD)

        for _ in range(5):
            response = self.client.post(
                "/enrol/requests/approve-batch",
                json={"request_ids": []},
                headers=headers,
            )
            self.assertEqual(response.status_code, 200)

        limited = self.client.post(
            "/enrol/requests/approve-batch",
            json={"request_ids": []},
            headers=headers,
        )
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.json()["detail"], "Too many requests. Please try again later.")
        self.assertIn("Retry-After", limited.headers)

    def test_request_id_is_generated_for_successful_requests(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        request_id = response.headers.get("X-Request-ID")
        self.assertIsNotNone(request_id)
        self.assertEqual(len(request_id), 12)

    def test_request_id_is_preserved_on_error_responses(self):
        response = self.client.get(
            "/auth/me",
            headers={"X-Request-ID": "req-test-401"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get("X-Request-ID"), "req-test-401")

    def test_suspending_admin_revokes_sessions_and_blocks_existing_tokens(self):
        admin_login = self.login("superadmin", TEST_ADMIN_PASSWORD)
        platform_headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        suspend = self.client.patch(
            "/api/platform/admins/user-rajan-mehra/status",
            json={"status": "suspended"},
            headers=platform_headers,
        )
        self.assertEqual(suspend.status_code, 200)
        self.assertEqual(suspend.json()["status"], "suspended")
        self.assertEqual(suspend.json()["user_id"], "user-rajan-mehra")
        self.assertGreaterEqual(suspend.json()["revoked_sessions"], 1)

        me = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {admin_login['access_token']}"},
        )
        self.assertEqual(me.status_code, 401)
        self.assertEqual(me.json()["detail"], "User is inactive")

        refresh = self.client.post(
            "/auth/refresh",
            json={"refresh_token": admin_login["refresh_token"]},
        )
        self.assertEqual(refresh.status_code, 401)
        self.assertEqual(refresh.json()["detail"], "Refresh token has been revoked")

        with self.store.get_conn() as conn:
            revoked_row = conn.execute(
                """
                SELECT revoked_at
                FROM auth_sessions
                WHERE user_id = ? AND refresh_token = ?
                LIMIT 1
                """,
                ("user-rajan-mehra", admin_login["refresh_token"]),
            ).fetchone()
            self.assertIsNotNone(revoked_row)
            self.assertIsNotNone(revoked_row["revoked_at"])

    def test_signup_student_role_is_counted_by_learner_filters(self):
        headers = self.auth_headers("superadmin", TEST_ADMIN_PASSWORD)
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

    def test_signup_admin_review_writes_approve_and_reject_audits(self):
        headers = self.auth_headers("superadmin", TEST_ADMIN_PASSWORD)

        approve_register = self.client.post(
            "/signup/register",
            json={
                "domain_type": "college",
                "role_name": "student",
                "email": "audit.approve@telite.edu",
                "full_name": "Audit Approve",
                "password": "Student@1234",
                "organization_name": "Telite University",
                "phone": "9999999999",
                "id_number": "STU-101",
                "program": "B.Tech",
                "branch": "CSE",
                "captcha": "12",
            },
        )
        self.assertEqual(approve_register.status_code, 200)
        approve_id = approve_register.json()["verification_id"]

        reject_register = self.client.post(
            "/signup/register",
            json={
                "domain_type": "college",
                "role_name": "student",
                "email": "audit.reject@telite.edu",
                "full_name": "Audit Reject",
                "password": "Student@1234",
                "organization_name": "Telite University",
                "phone": "9999999998",
                "id_number": "STU-102",
                "program": "B.Tech",
                "branch": "ECE",
                "captcha": "12",
            },
        )
        self.assertEqual(reject_register.status_code, 200)
        reject_id = reject_register.json()["verification_id"]

        approve = self.client.post(
            f"/admin/verifications/{approve_id}/approve",
            headers=headers,
        )
        self.assertEqual(approve.status_code, 200)

        reject = self.client.post(
            f"/admin/verifications/{reject_id}/reject",
            json={"reason": "Incomplete documents"},
            headers=headers,
        )
        self.assertEqual(reject.status_code, 200)

        with self.store.get_conn() as conn:
            approve_audit = conn.execute(
                """
                SELECT action, target_id, result
                FROM audit_log
                WHERE action = 'signup.approve' AND target_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (approve_id,),
            ).fetchone()
            self.assertIsNotNone(approve_audit)
            self.assertEqual(approve_audit["result"], "approved")

            reject_audit = conn.execute(
                """
                SELECT action, target_id, result
                FROM audit_log
                WHERE action = 'signup.reject' AND target_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (reject_id,),
            ).fetchone()
            self.assertIsNotNone(reject_audit)
            self.assertEqual(reject_audit["result"], "rejected")

    def test_signup_bulk_review_writes_summary_audit(self):
        headers = self.auth_headers("superadmin", TEST_ADMIN_PASSWORD)

        first_register = self.client.post(
            "/signup/register",
            json={
                "domain_type": "college",
                "role_name": "student",
                "email": "bulk.keep@telite.edu",
                "full_name": "Bulk Keep",
                "password": "Student@1234",
                "organization_name": "Telite University",
                "phone": "9999999997",
                "id_number": "STU-201",
                "program": "B.Tech",
                "branch": "CSE",
                "captcha": "12",
            },
        )
        self.assertEqual(first_register.status_code, 200)

        second_register = self.client.post(
            "/signup/register",
            json={
                "domain_type": "college",
                "role_name": "student",
                "email": "bulk.reject@telite.edu",
                "full_name": "Bulk Reject",
                "password": "Student@1234",
                "organization_name": "Telite University",
                "phone": "9999999996",
                "id_number": "STU-202",
                "program": "B.Tech",
                "branch": "ME",
                "captcha": "12",
            },
        )
        self.assertEqual(second_register.status_code, 200)

        csv_bytes = b"email\nbulk.keep@telite.edu\n"
        response = self.client.post(
            "/admin/verifications/bulk-upload",
            params={"orgId": 1},
            headers=headers,
            files={"file": ("approved.csv", csv_bytes, "text/csv")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["processed"]["approved"], 1)
        self.assertEqual(response.json()["processed"]["rejected"], 1)

        with self.store.get_conn() as conn:
            audit_row = conn.execute(
                """
                SELECT action, target_id, result, metadata_json
                FROM audit_log
                WHERE action = 'signup.bulk_review' AND target_id = 'approved.csv'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            self.assertIsNotNone(audit_row)
            self.assertEqual(audit_row["result"], "success")
            self.assertIn('"approved": 1', audit_row["metadata_json"])
            self.assertIn('"rejected": 1', audit_row["metadata_json"])


if __name__ == "__main__":
    unittest.main()
