import pytest
from app.services.bulk_enrollment_service import BulkEnrollmentService, BulkPreviewRow
from app.services.enrollment_service import EnrollmentPermissionError, EnrollmentServiceError
from app.api.auth import TokenData
from app.models.user import User
from app.models.course import Course

class DummyTokenData(TokenData):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class DummyUser:
    def __init__(self, email, org_id):
        self.email = email
        self.org_id = org_id

class DummyCourse:
    def __init__(self, id, org_id, status, category_slug):
        self.id = id
        self.org_id = org_id
        self.status = status
        self.category_slug = category_slug

class MockUserRepo:
    def __init__(self, existing_users):
        self.existing_users = {u.email: u for u in existing_users}
    def get_by_email(self, email):
        return self.existing_users.get(email)

class MockCourseRepo:
    def __init__(self, existing_courses):
        self.existing_courses = {c.id: c for c in existing_courses}
    def list_by_ids_for_org(self, course_ids, org_id):
        return [c for c in self.existing_courses.values() if c.id in course_ids and c.org_id == org_id]

class MockEnrollmentService:
    ALLOWED_ACTOR_ROLES = {"platform_admin", "super_admin", "category_admin"}
    LEARNER_VISIBLE_COURSE_STATUSES = {"active", "published"}

    def __init__(self):
        self.calls = []

    def manual_enroll(self, **kwargs):
        email = kwargs.get("email")
        course_ids = kwargs.get("course_ids")
        # simulate duplicate prevention exception or cross org if we wanted, 
        # but the service layer usually handles it silently or raises.
        # for this test we just record the call.
        if "fail" in email:
            raise EnrollmentServiceError("Failed")
        self.calls.append(kwargs)

def test_parse_and_validate_csv_valid_data():
    service = BulkEnrollmentService(db=None)
    service.user_repo = MockUserRepo([DummyUser("exist@example.com", 1)])
    service.course_repo = MockCourseRepo([DummyCourse("c1", 1, "published", "slug1")])
    service.enrollment_service = MockEnrollmentService()

    csv_content = "email,full_name,course_id\nnew@example.com,New User,c1\nexist@example.com,Exist User,c1"
    token = DummyTokenData(id="1", role="platform_admin", is_platform_admin=True, org_id=1, email="admin@example.com", full_name="Admin")
    
    rows = service.parse_and_validate_csv(csv_content, token)
    
    assert len(rows) == 2
    assert rows[0].email == "new@example.com"
    assert rows[0].is_valid is True
    assert rows[0].is_new_user is True
    
    assert rows[1].email == "exist@example.com"
    assert rows[1].is_valid is True
    assert rows[1].is_new_user is False

def test_parse_and_validate_csv_invalid_email():
    service = BulkEnrollmentService(db=None)
    service.user_repo = MockUserRepo([])
    service.course_repo = MockCourseRepo([DummyCourse("c1", 1, "published", "slug1")])
    service.enrollment_service = MockEnrollmentService()

    csv_content = "email,full_name,course_id\nbademail,New User,c1"
    token = DummyTokenData(id="1", role="platform_admin", is_platform_admin=True, org_id=1, email="admin@example.com", full_name="Admin")
    
    rows = service.parse_and_validate_csv(csv_content, token)
    assert len(rows) == 1
    assert rows[0].is_valid is False
    assert "Invalid email format" in rows[0].errors

def test_parse_and_validate_csv_invalid_course():
    service = BulkEnrollmentService(db=None)
    service.user_repo = MockUserRepo([])
    service.course_repo = MockCourseRepo([DummyCourse("c1", 1, "published", "slug1")])
    service.enrollment_service = MockEnrollmentService()

    csv_content = "email,full_name,course_id\nnew@example.com,New User,c_wrong"
    token = DummyTokenData(id="1", role="platform_admin", is_platform_admin=True, org_id=1, email="admin@example.com", full_name="Admin")
    
    rows = service.parse_and_validate_csv(csv_content, token)
    assert len(rows) == 1
    assert rows[0].is_valid is False
    assert any("invalid" in e.lower() for e in rows[0].errors)

def test_parse_and_validate_csv_cross_org_rejection():
    service = BulkEnrollmentService(db=None)
    # User belongs to org 2
    service.user_repo = MockUserRepo([DummyUser("cross@example.com", 2)])
    # Course belongs to org 1
    service.course_repo = MockCourseRepo([DummyCourse("c1", 1, "published", "slug1")])
    service.enrollment_service = MockEnrollmentService()

    csv_content = "email,full_name,course_id\ncross@example.com,Cross Org User,c1"
    token = DummyTokenData(id="1", role="platform_admin", is_platform_admin=True, org_id=1, email="admin@example.com", full_name="Admin")
    
    rows = service.parse_and_validate_csv(csv_content, token)
    assert rows[0].is_valid is False
    assert any("different organization" in e.lower() for e in rows[0].errors)

def test_execute_batch_success():
    service = BulkEnrollmentService(db=None)
    mock_enrol = MockEnrollmentService()
    service.enrollment_service = mock_enrol
    # Add a mock db with commit/rollback
    class MockDB:
        def commit(self): pass
        def rollback(self): pass
    service.db = MockDB()

    rows = [{"email": "u1@example.com", "full_name": "U 1", "course_id": "c1"}]
    token = DummyTokenData(id="1", role="platform_admin", is_platform_admin=True, org_id=1, email="admin@example.com", full_name="Admin")
    
    result = service.execute_batch(rows, token)
    
    assert result["success_count"] == 1
    assert result["failure_count"] == 0
    assert len(mock_enrol.calls) == 1
    assert mock_enrol.calls[0]["email"] == "u1@example.com"
