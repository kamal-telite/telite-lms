import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.repositories.course_repo import CourseRepository


class FakeSession:
    def __init__(self):
        self.added = []
        self.flush_count = 0

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flush_count += 1


def test_create_course_accepts_explicit_status_values_once():
    for status in ("draft", "active", "published"):
        session = FakeSession()
        repo = CourseRepository(session)

        course = repo.create_course(
            name=f"{status.title()} Course",
            category_slug="kt-foundations",
            org_id=1,
            description="Course creation regression test",
            tier="Advanced",
            status=status,
            modules=["Intro", "Practice"],
        )

        assert course.status == status
        assert json.loads(course.modules_json) == ["Intro", "Practice"]
        assert session.added == [course]
        assert session.flush_count == 1

