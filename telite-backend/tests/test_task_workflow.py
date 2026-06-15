import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.task import Task
from app.repositories.task_repo import TaskRepository


class FakeSession:
    def __init__(self):
        self.added = []
        self.flush_count = 0

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flush_count += 1


def make_task():
    return Task(
        id="task-test",
        title="Workflow Task",
        assigned_label="Aarav Sharma",
        assigned_to_user_id="learner-1",
        assignment_scope="individual",
        category_slug="kt-foundations",
        status="pending",
        org_id=1,
    )


def test_task_assignment_lifecycle_transitions():
    session = FakeSession()
    repo = TaskRepository(session)
    task = make_task()

    assignment = repo.create_assignment(task=task, learner_id="learner-1")
    assert assignment.status == "assigned"
    assert assignment.assigned_at is not None

    repo.start_assignment(assignment)
    assert assignment.status == "in_progress"
    assert assignment.started_at is not None

    submission = repo.submit_assignment(
        assignment,
        submission_notes="Done",
        external_url="https://example.com/submission",
    )
    assert assignment.status == "submitted"
    assert assignment.submitted_at is not None
    assert submission.submission_notes == "Done"
    assert submission.external_url == "https://example.com/submission"

    repo._latest_submission = lambda assignment_id: submission
    review = repo.review_assignment(
        assignment,
        review_status="approved",
        review_notes="Looks good",
        reviewed_by="admin-1",
    )
    assert assignment.status == "approved"
    assert assignment.completed_at is not None
    assert review.review_status == "approved"
    assert review.review_notes == "Looks good"


def test_revision_requested_can_be_restarted():
    session = FakeSession()
    repo = TaskRepository(session)
    task = make_task()
    assignment = repo.create_assignment(task=task, learner_id="learner-1")
    assignment.status = "revision_requested"

    repo.start_assignment(assignment)

    assert assignment.status == "in_progress"
