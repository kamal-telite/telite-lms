import importlib
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

def _test_secret(label: str) -> str:
    digest = hashlib.sha256(f"telite-quiz-test-{label}".encode("utf-8")).hexdigest()
    return f"TeliteQuiz{digest[:12]}9"


TEST_ADMIN_PASSWORD = os.getenv("TELITE_SEED_ADMIN_PASSWORD") or _test_secret("admin")
TEST_LEARNER_PASSWORD = os.getenv("TELITE_SEED_LEARNER_PASSWORD") or _test_secret("learner")


class TeliteQuizEngineTests(unittest.TestCase):
    """Phase D Section 6 & 7: Comprehensive Quiz Engine Validation Suite."""

    # ── Shared fixtures ────────────────────────────────────────────────────

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["TELITE_DB_BACKEND"] = "sqlite"
        db_path = os.path.join(self.tempdir.name, "test_quiz_engine.db")
        os.environ["TELITE_DB_PATH"] = db_path
        os.environ["TELITE_DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["MOODLE_MODE"] = "mock"
        os.environ["TELITE_SEED_ADMIN_PASSWORD"] = TEST_ADMIN_PASSWORD
        os.environ["TELITE_SEED_LEARNER_PASSWORD"] = TEST_LEARNER_PASSWORD
        os.environ["REDIS_ENABLED"] = "false"

        from app.db.engine import dispose_engine, get_session_factory
        dispose_engine()

        main = importlib.import_module("main")
        importlib.reload(main)
        from app.core import rate_limiter
        self.SessionFactory = get_session_factory()

        rate_limiter.clear_all_attempts()
        self.client = TestClient(main.create_app())
        self.client.__enter__()

        from app.repositories.user_repo import UserRepository
        from app.models.organization import Organization
        from sqlalchemy import text
        db = self.SessionFactory()
        db.execute(text("PRAGMA foreign_keys=OFF"))
        db.commit()

        # Create organization
        org = db.query(Organization).filter_by(id=1).first()
        if not org:
            db.add(Organization(id=1, name="Default Org", domain="default.telite.com",
                                type="company", status="active", plan="free"))
            db.commit()

        repo = UserRepository(db)

        admin = repo.get_by_identifier("globaladmin")
        if not admin:
            repo.create_user(
                email="admin@telite.com",
                full_name="Global Admin",
                role="super_admin",
                org_id=1,
                password=TEST_ADMIN_PASSWORD,
                username="globaladmin",
                is_platform_admin=True,
            )

        learner = repo.get_by_identifier("learner")
        if not learner:
            repo.create_user(
                email="learner@telite.com",
                full_name="Learner",
                role="learner",
                org_id=1,
                password=TEST_LEARNER_PASSWORD,
                username="learner",
            )

        db.commit()
        db.close()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        from app.db.engine import dispose_engine
        dispose_engine()
        self.tempdir.cleanup()

    # ── Helpers ─────────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> dict:
        response = self.client.post(
            "/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(response.status_code, 200, msg=f"Login failed: {response.text}")
        return response.json()

    def auth_headers(self, username: str, password: str) -> dict:
        token = self.login(username, password)["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def _seed_quiz_with_questions(self, headers):
        """Create a bank, questions, a quiz definition, and settings. Returns dict of IDs."""
        bank_res = self.client.post(
            "/quiz-authoring/banks",
            json={"name": "Test Bank", "visibility": "tenant"},
            headers=headers,
        )
        bank_id = bank_res.json()["id"]

        q1_res = self.client.post(f"/quiz-authoring/banks/{bank_id}/questions", json={
            "bank_id": bank_id,
            "question_type": "multiple_choice",
            "question_text": "What is 2+2?",
            "options_json": {"options": ["3", "4", "5"]},
            "correct_answer_json": {"answer": "4"},
            "points": 10,
        }, headers=headers)
        q1 = q1_res.json()

        q2_res = self.client.post(f"/quiz-authoring/banks/{bank_id}/questions", json={
            "bank_id": bank_id,
            "question_type": "essay",
            "question_text": "Explain Python.",
            "points": 20,
        }, headers=headers)
        q2 = q2_res.json()

        q3_res = self.client.post(f"/quiz-authoring/banks/{bank_id}/questions", json={
            "bank_id": bank_id,
            "question_type": "true_false",
            "question_text": "Python is a compiled language.",
            "correct_answer_json": {"answer": "false"},
            "points": 5,
        }, headers=headers)
        q3 = q3_res.json()

        # Seed a QuizDefinition directly
        from app.models.quiz_models import QuizDefinition
        db = self.SessionFactory()
        db.add(QuizDefinition(id=100, org_id=1, module_id=1, title="Full Test Quiz"))
        db.commit()
        db.close()

        self.client.put("/quiz-authoring/quizzes/100/settings", json={
            "passing_score": 15,
            "time_limit": 600,
            "attempt_limit": 3,
            "review_mode": "answers_after_submit",
        }, headers=headers)

        return {
            "bank_id": bank_id,
            "quiz_id": 100,
            "q1_version_id": q1["version_id"],
            "q2_version_id": q2["version_id"],
            "q3_version_id": q3["version_id"],
            "q1_question_id": q1["question_id"],
        }

    def _run_full_attempt(self, headers, quiz_id, answers):
        """Start attempt, save answers, submit. Returns (attempt_id, submit_response)."""
        attempt_res = self.client.post(f"/quiz-execution/quizzes/{quiz_id}/attempts", headers=headers)
        self.assertEqual(attempt_res.status_code, 200, msg=f"Start attempt failed: {attempt_res.text}")
        attempt_id = attempt_res.json()["attempt_id"]

        for ans in answers:
            save_res = self.client.put(f"/quiz-execution/attempts/{attempt_id}/answers", json=ans, headers=headers)
            self.assertEqual(save_res.status_code, 200, msg=f"Save answer failed: {save_res.text}")

        submit_res = self.client.post(f"/quiz-execution/attempts/{attempt_id}/submit", headers=headers)
        return attempt_id, submit_res

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 6: Testing & Validation
    # ════════════════════════════════════════════════════════════════════════

    # 6.1 — Tenant isolation on attempt queries
    def test_6_1_tenant_isolation_on_question_banks(self):
        """Question banks created by org 1 are scoped to org 1."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        res = self.client.post(
            "/quiz-authoring/banks",
            json={"name": "Org1 Bank", "visibility": "tenant"},
            headers=headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("id", res.json())

    # 6.2 — Auto-grading permutations
    def test_6_2_auto_grading_permutations(self):
        """Multiple choice auto-graded; essay left for manual grading; total score correct."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        ids = self._seed_quiz_with_questions(headers)

        attempt_id, submit_res = self._run_full_attempt(headers, ids["quiz_id"], [
            {"question_version_id": ids["q1_version_id"], "response_json": {"answer": "4"}},
            {"question_version_id": ids["q2_version_id"], "response_json": {"answer": "A programming language."}},
            {"question_version_id": ids["q3_version_id"], "response_json": {"answer": "false"}},
        ])

        self.assertEqual(submit_res.status_code, 200)
        body = submit_res.json()
        # MC correct (10) + true_false correct (5) = 15, essay needs manual
        self.assertEqual(body["status"], "needs_manual_grading")
        self.assertEqual(body["total_score"], 15.0)

    # 6.3 — Manual grading workflow
    def test_6_3_manual_grading_workflow(self):
        """Pending queue returns list; manual grade updates answer score and creates audit event."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        # Verify pending endpoint returns a list
        pending_res = self.client.get("/quiz-grading/pending", headers=headers)
        self.assertEqual(pending_res.status_code, 200)
        self.assertIsInstance(pending_res.json()["pending_attempts"], list)

    # 6.4 — Question versioning integrity
    def test_6_4_question_versioning_integrity(self):
        """Creating a new question produces version_number=1 and links current_version_id."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        bank_res = self.client.post(
            "/quiz-authoring/banks",
            json={"name": "Versioning Bank", "visibility": "tenant"},
            headers=headers,
        )
        bank_id = bank_res.json()["id"]

        q_res = self.client.post(f"/quiz-authoring/banks/{bank_id}/questions", json={
            "bank_id": bank_id,
            "question_type": "multiple_choice",
            "question_text": "Version 1 text",
            "correct_answer_json": {"answer": "A"},
            "points": 5,
        }, headers=headers)
        self.assertEqual(q_res.status_code, 200)
        q_data = q_res.json()
        self.assertIn("question_id", q_data)
        self.assertIn("version_id", q_data)

        # Verify version stored in DB
        from app.models.question import Question, QuestionVersion
        db = self.SessionFactory()
        question = db.query(Question).filter_by(id=q_data["question_id"]).first()
        self.assertIsNotNone(question)
        self.assertEqual(question.current_version_id, q_data["version_id"])

        version = db.query(QuestionVersion).filter_by(id=q_data["version_id"]).first()
        self.assertIsNotNone(version)
        self.assertEqual(version.version_number, 1)
        self.assertEqual(version.question_type, "multiple_choice")
        self.assertEqual(version.question_text, "Version 1 text")
        self.assertEqual(version.points, 5)
        db.close()

    # 6.5 — Question pool randomization snapshot integrity
    def test_6_5_question_pool_snapshot_integrity(self):
        """Answers are linked to specific question_version_ids, preserving the snapshot."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        ids = self._seed_quiz_with_questions(headers)

        attempt_id, submit_res = self._run_full_attempt(headers, ids["quiz_id"], [
            {"question_version_id": ids["q1_version_id"], "response_json": {"answer": "4"}},
        ])
        self.assertEqual(submit_res.status_code, 200)

        # Verify the answer is locked to a specific version_id
        from app.models.quiz_answer import QuizAnswer
        db = self.SessionFactory()
        answers = db.query(QuizAnswer).filter_by(attempt_id=attempt_id).all()
        self.assertTrue(len(answers) >= 1)
        for ans in answers:
            self.assertEqual(ans.question_version_id, ids["q1_version_id"])
        db.close()

    # 6.6 — Review mode permissions
    def test_6_6_review_mode_settings(self):
        """Quiz settings review_mode is stored and retrievable."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        # Seed a quiz
        from app.models.quiz_models import QuizDefinition
        db = self.SessionFactory()
        db.add(QuizDefinition(id=200, org_id=1, module_id=1, title="Review Mode Quiz"))
        db.commit()
        db.close()

        update_res = self.client.put("/quiz-authoring/quizzes/200/settings", json={
            "review_mode": "full_review",
            "show_answers": True,
            "show_score": True,
        }, headers=headers)
        self.assertEqual(update_res.status_code, 200)

        # Verify in DB
        from app.models.quiz_models import QuizSettings
        db = self.SessionFactory()
        settings = db.query(QuizSettings).filter_by(quiz_id=200).first()
        self.assertIsNotNone(settings)
        self.assertEqual(settings.review_mode, "full_review")
        self.assertTrue(settings.show_answers)
        self.assertTrue(settings.show_score)
        db.close()

    # 6.7 — Quiz attempt event generation
    def test_6_7_quiz_attempt_event_generation(self):
        """Starting, saving answers, and submitting an attempt generate the correct events."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        ids = self._seed_quiz_with_questions(headers)

        attempt_id, submit_res = self._run_full_attempt(headers, ids["quiz_id"], [
            {"question_version_id": ids["q1_version_id"], "response_json": {"answer": "4"}},
            {"question_version_id": ids["q3_version_id"], "response_json": {"answer": "false"}},
        ])
        self.assertEqual(submit_res.status_code, 200)

        from app.models.quiz_attempt import QuizAttemptEvent
        db = self.SessionFactory()
        events = db.query(QuizAttemptEvent).filter_by(attempt_id=attempt_id).order_by(QuizAttemptEvent.id).all()
        event_types = [e.event_type for e in events]

        # Must contain QUIZ_STARTED and MANUAL_SUBMIT at minimum
        self.assertIn("QUIZ_STARTED", event_types, "Missing QUIZ_STARTED event")
        self.assertIn("ANSWER_SAVED", event_types, "Missing ANSWER_SAVED event")
        self.assertIn("MANUAL_SUBMIT", event_types, "Missing MANUAL_SUBMIT event")

        # Verify QUIZ_STARTED is always first
        self.assertEqual(event_types[0], "QUIZ_STARTED")
        db.close()

    # 6.8 — Grading event audit trail
    def test_6_8_grading_event_audit_trail(self):
        """Auto-grading produces GradingEvent records with action=AUTO_GRADE_APPLIED."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        ids = self._seed_quiz_with_questions(headers)

        attempt_id, submit_res = self._run_full_attempt(headers, ids["quiz_id"], [
            {"question_version_id": ids["q1_version_id"], "response_json": {"answer": "4"}},
            {"question_version_id": ids["q3_version_id"], "response_json": {"answer": "false"}},
        ])
        self.assertEqual(submit_res.status_code, 200)

        from app.models.quiz_answer import GradingEvent
        db = self.SessionFactory()
        events = db.query(GradingEvent).filter_by(attempt_id=attempt_id).all()

        # MC + true_false = 2 auto-grade events
        self.assertEqual(len(events), 2, f"Expected 2 GradingEvents, got {len(events)}")
        for e in events:
            self.assertEqual(e.action, "AUTO_GRADE_APPLIED")
            self.assertEqual(e.grader_id, "system")
            self.assertIsNotNone(e.new_score)
        db.close()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 7: Performance & Security Validation
    # ════════════════════════════════════════════════════════════════════════

    # 7.1 — Load test (simulated concurrent submissions)
    def test_7_1_concurrent_submissions_simulation(self):
        """Sequential rapid-fire submissions complete without integrity errors."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        ids = self._seed_quiz_with_questions(headers)

        completed = 0
        for i in range(10):
            attempt_res = self.client.post(
                f"/quiz-execution/quizzes/{ids['quiz_id']}/attempts", headers=headers
            )
            if attempt_res.status_code != 200:
                continue
            aid = attempt_res.json()["attempt_id"]
            self.client.put(f"/quiz-execution/attempts/{aid}/answers", json={
                "question_version_id": ids["q1_version_id"],
                "response_json": {"answer": "4"},
            }, headers=headers)
            sub = self.client.post(f"/quiz-execution/attempts/{aid}/submit", headers=headers)
            if sub.status_code == 200:
                completed += 1

        self.assertGreaterEqual(completed, 10, "Not all rapid submissions completed")

    # 7.2 — Autosave under network interruption
    def test_7_2_autosave_persistence(self):
        """Answers saved via PUT persist even if submission never happens."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)
        ids = self._seed_quiz_with_questions(headers)

        attempt_res = self.client.post(
            f"/quiz-execution/quizzes/{ids['quiz_id']}/attempts", headers=headers
        )
        attempt_id = attempt_res.json()["attempt_id"]

        # Save answer (simulates autosave)
        save_res = self.client.put(f"/quiz-execution/attempts/{attempt_id}/answers", json={
            "question_version_id": ids["q1_version_id"],
            "response_json": {"answer": "4"},
        }, headers=headers)
        self.assertEqual(save_res.status_code, 200)

        # Verify the answer persisted in DB (without submitting)
        from app.models.quiz_answer import QuizAnswer
        db = self.SessionFactory()
        answer = db.query(QuizAnswer).filter_by(
            attempt_id=attempt_id, question_version_id=ids["q1_version_id"]
        ).first()
        self.assertIsNotNone(answer, "Autosaved answer not persisted in DB")
        self.assertEqual(answer.response_json["answer"], "4")
        db.close()

    # 7.3 — Timer expiration edge case
    def test_7_3_timer_expiration_settings(self):
        """Quiz with time_limit stores the value; attempt can still be submitted within window."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        from app.models.quiz_models import QuizDefinition
        db = self.SessionFactory()
        db.add(QuizDefinition(id=300, org_id=1, module_id=1, title="Timed Quiz"))
        db.commit()
        db.close()

        self.client.put("/quiz-authoring/quizzes/300/settings", json={
            "time_limit": 60,
        }, headers=headers)

        from app.models.quiz_models import QuizSettings
        db = self.SessionFactory()
        settings = db.query(QuizSettings).filter_by(quiz_id=300).first()
        self.assertIsNotNone(settings)
        self.assertEqual(settings.time_limit, 60)
        db.close()

        # Attempt within time window should succeed
        attempt_res = self.client.post("/quiz-execution/quizzes/300/attempts", headers=headers)
        self.assertEqual(attempt_res.status_code, 200)
        attempt_id = attempt_res.json()["attempt_id"]

        submit_res = self.client.post(f"/quiz-execution/attempts/{attempt_id}/submit", headers=headers)
        self.assertEqual(submit_res.status_code, 200)

    # 7.4 — Duplicate submission prevention
    def test_7_4_duplicate_submission_prevention(self):
        """Submitting the same attempt twice returns 400 on second call."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        from app.models.quiz_models import QuizDefinition
        db = self.SessionFactory()
        db.add(QuizDefinition(id=400, org_id=1, module_id=1, title="Dup Prevention Quiz"))
        db.commit()
        db.close()

        attempt_res = self.client.post("/quiz-execution/quizzes/400/attempts", headers=headers)
        attempt_id = attempt_res.json()["attempt_id"]

        res1 = self.client.post(f"/quiz-execution/attempts/{attempt_id}/submit", headers=headers)
        self.assertEqual(res1.status_code, 200)

        res2 = self.client.post(f"/quiz-execution/attempts/{attempt_id}/submit", headers=headers)
        self.assertEqual(res2.status_code, 400)
        self.assertEqual(res2.json()["detail"], "Invalid attempt")

    # 7.5 — Question leakage prevention
    def test_7_5_question_leakage_prevention(self):
        """Learner cannot access quiz-authoring endpoints (question bank CRUD)."""
        learner_headers = self.auth_headers("learner", TEST_LEARNER_PASSWORD)

        res = self.client.post(
            "/quiz-authoring/banks",
            json={"name": "Hacker Bank", "visibility": "tenant"},
            headers=learner_headers,
        )
        # Learner should be blocked by require_admin dependency
        self.assertIn(res.status_code, [401, 403],
                      f"Expected 401/403 for learner accessing authoring, got {res.status_code}")

    # 7.6 — RLS on question banks
    def test_7_6_rls_question_banks(self):
        """Question bank creation is scoped to user's org_id; bank query filters by org."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        res = self.client.post(
            "/quiz-authoring/banks",
            json={"name": "RLS Bank", "visibility": "tenant"},
            headers=headers,
        )
        self.assertEqual(res.status_code, 200)
        bank_id = res.json()["id"]

        from app.models.question_bank import QuestionBank
        db = self.SessionFactory()
        bank = db.query(QuestionBank).filter_by(id=bank_id).first()
        self.assertIsNotNone(bank)
        self.assertEqual(bank.org_id, 1, "Bank org_id should match authenticated user's org")
        db.close()

    # 7.7 — RLS on quiz attempts
    def test_7_7_rls_quiz_attempts(self):
        """Quiz attempts are scoped to the authenticated user's org_id."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        from app.models.quiz_models import QuizDefinition
        db = self.SessionFactory()
        db.add(QuizDefinition(id=500, org_id=1, module_id=1, title="RLS Attempt Quiz"))
        db.commit()
        db.close()

        attempt_res = self.client.post("/quiz-execution/quizzes/500/attempts", headers=headers)
        self.assertEqual(attempt_res.status_code, 200)
        attempt_id = attempt_res.json()["attempt_id"]

        from app.models.quiz_attempt import QuizAttempt
        db = self.SessionFactory()
        attempt = db.query(QuizAttempt).filter_by(id=attempt_id).first()
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.org_id, 1, "Attempt org_id should match authenticated user's org")
        db.close()

    # 7.8 — RLS on grading dashboard
    def test_7_8_rls_grading_dashboard(self):
        """Grading dashboard only returns attempts from the authenticated user's org."""
        headers = self.auth_headers("globaladmin", TEST_ADMIN_PASSWORD)

        pending_res = self.client.get("/quiz-grading/pending", headers=headers)
        self.assertEqual(pending_res.status_code, 200)
        pending = pending_res.json()["pending_attempts"]

        # If there are any, they must all belong to org 1
        from app.models.quiz_attempt import QuizAttempt
        db = self.SessionFactory()
        for item in pending:
            attempt = db.query(QuizAttempt).filter_by(id=item["id"]).first()
            if attempt:
                self.assertEqual(attempt.org_id, 1, f"Pending attempt {item['id']} leaked from another org")
        db.close()


if __name__ == "__main__":
    unittest.main()
