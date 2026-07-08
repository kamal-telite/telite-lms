from fastapi.testclient import TestClient

from app.api.auth import TokenData, get_current_user
from app.db.engine import db_session
from app.main import create_app


class FakeAssignmentService:
    calls = []

    def __init__(self, _db):
        self.db = _db

    def get_learner_submission(self, block_id, user):
        self.calls.append(("get_learner_submission", block_id, user.id))
        return {"submission": None}

    async def save_draft(self, block_id, user, submission_text):
        self.calls.append(("save_draft", block_id, user.id, submission_text))
        return {"submission": {"block_id": block_id, "status": "draft", "submission_text": submission_text}}

    async def submit(self, block_id, user, submission_text, files, *, resubmit=False):
        self.calls.append(("submit", block_id, user.id, submission_text, len(files), resubmit))
        return {
            "submission": {
                "block_id": block_id,
                "status": "resubmitted" if resubmit else "submitted",
                "submission_text": submission_text,
            }
        }

    def list_submissions(self, block_id, user):
        self.calls.append(("list_submissions", block_id, user.id))
        return {"assignment": {"block_id": block_id}, "submissions": []}

    def list_verification_queue(self, category_slug, user, *, status_filter=None, course_id=None, learner_id=None, search=None):
        self.calls.append(("list_verification_queue", category_slug, user.id, status_filter, course_id, learner_id, search))
        return {
            "stats": {"pending": 1, "approved": 0, "rejected": 0, "total": 1},
            "submissions": [{"id": 99, "status": "pending_verification"}],
        }

    def get_admin_submission(self, submission_id, user):
        self.calls.append(("get_admin_submission", submission_id, user.id))
        return {"submission": {"id": submission_id}}

    def grade(self, submission_id, user, *, grade, feedback, returned=False):
        self.calls.append(("grade", submission_id, user.id, grade, feedback, returned))
        return {"submission": {"id": submission_id, "grade": grade, "feedback": feedback, "status": "returned" if returned else "graded"}}

    def review(self, submission_id, user, *, approved, feedback=None):
        self.calls.append(("review", submission_id, user.id, approved, feedback))
        return {"submission": {"id": submission_id, "feedback": feedback, "status": "approved" if approved else "rejected"}}


class FakeDb:
    def execute(self, *_args, **_kwargs):
        return None


def make_client(monkeypatch, user):
    from app.api.routes import assignments

    app = create_app()
    FakeAssignmentService.calls = []
    monkeypatch.setattr(assignments, "AssignmentService", FakeAssignmentService)

    def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[db_session] = lambda: FakeDb()
    return TestClient(app)


def test_learner_assignment_api_contract_accepts_json_submit_and_draft(monkeypatch):
    user = TokenData(id="learner-1", email="learner@example.com", full_name="Learner", role="learner", org_id=1)
    client = make_client(monkeypatch, user)

    draft = client.patch("/api/v1/learner/assignments/10/draft", json={"submission_text": "draft text"})
    assert draft.status_code == 200
    assert draft.json()["submission"]["status"] == "draft"

    submit = client.post("/api/v1/learner/assignments/10/submit", json={"submission_text": "final text"})
    assert submit.status_code == 200
    assert submit.json()["submission"]["status"] == "submitted"

    resubmit = client.post("/api/v1/learner/assignments/10/resubmit", json={"submission_text": "revised"})
    assert resubmit.status_code == 200
    assert resubmit.json()["submission"]["status"] == "resubmitted"

    assert ("save_draft", 10, "learner-1", "draft text") in FakeAssignmentService.calls
    assert ("submit", 10, "learner-1", "final text", 0, False) in FakeAssignmentService.calls
    assert ("submit", 10, "learner-1", "revised", 0, True) in FakeAssignmentService.calls


def test_admin_assignment_api_contract_lists_and_grades(monkeypatch):
    user = TokenData(id="admin-1", email="admin@example.com", full_name="Admin", role="category_admin", org_id=1)
    client = make_client(monkeypatch, user)

    listing = client.get("/api/v1/admin/assignments/10/submissions")
    assert listing.status_code == 200
    assert listing.json()["assignment"]["block_id"] == 10

    detail = client.get("/api/v1/admin/submissions/99")
    assert detail.status_code == 200
    assert detail.json()["submission"]["id"] == 99

    graded = client.post(
        "/api/v1/admin/submissions/99/grade",
        json={"grade": 88, "feedback": "Good", "returned": False},
    )
    assert graded.status_code == 200
    assert graded.json()["submission"]["status"] == "graded"
    assert ("grade", 99, "admin-1", 88.0, "Good", False) in FakeAssignmentService.calls


def test_admin_assignment_verification_contract_lists_approves_and_rejects(monkeypatch):
    user = TokenData(id="admin-1", email="admin@example.com", full_name="Admin", role="category_admin", org_id=1)
    client = make_client(monkeypatch, user)

    queue = client.get(
        "/api/v1/admin/categories/ats/assignment-verifications",
        params={"status": "pending_verification", "course_id": "course-1", "search": "learner"},
    )
    assert queue.status_code == 200
    assert queue.json()["stats"]["pending"] == 1
    assert (
        "list_verification_queue",
        "ats",
        "admin-1",
        "pending_verification",
        "course-1",
        None,
        "learner",
    ) in FakeAssignmentService.calls

    approved = client.post("/api/v1/admin/submissions/99/approve", json={"feedback": "Looks good"})
    assert approved.status_code == 200
    assert approved.json()["submission"]["status"] == "approved"

    rejected = client.post("/api/v1/admin/submissions/100/reject", json={"feedback": "Please revise"})
    assert rejected.status_code == 200
    assert rejected.json()["submission"]["status"] == "rejected"
    assert ("review", 99, "admin-1", True, "Looks good") in FakeAssignmentService.calls
    assert ("review", 100, "admin-1", False, "Please revise") in FakeAssignmentService.calls
