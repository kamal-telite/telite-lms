import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.auth import TokenData
from app.db.engine import get_db_session
from app.models.user import User
from app.models.course import Course
from app.models.course_progress import CourseProgress
from app.models.audit_log import AuditLog
from app.api.auth import require_admin
import json

# We will override the require_admin dependency to return a platform admin token
def mock_require_admin():
    return TokenData(id="admin-1", email="admin@example.com", full_name="Admin", role="platform_admin", org_id=1, is_platform_admin=True)

app.dependency_overrides[require_admin] = mock_require_admin
client = TestClient(app)

def test_e2e_bulk_enrollment(db_session, seed_data):
    # db_session and seed_data are fixtures available in the test suite
    org = seed_data['org']
    course = seed_data['course']
    exist_user = seed_data['learner']
    
    print("\n--- 1. Valid CSV Preview ---")
    csv_data = f"email,full_name,course_id\n{exist_user.email},Exist User,{course.id}\nnewbulk@example.com,New Bulk User,{course.id}"
    files = {"file": ("upload.csv", csv_data, "text/csv")}
    response = client.post("/api/v1/enrol/bulk/preview", files=files)
    print("Response Status:", response.status_code)
    print("Response JSON:", json.dumps(response.json(), indent=2))
    
    print("\n--- 2. Invalid Email Preview ---")
    csv_data = f"email,full_name,course_id\nbademail,Bad Email,{course.id}"
    files = {"file": ("upload.csv", csv_data, "text/csv")}
    response = client.post("/api/v1/enrol/bulk/preview", files=files)
    print("Response Status:", response.status_code)
    print("Response JSON:", json.dumps(response.json(), indent=2))
    
    print("\n--- 3. Invalid Course Preview ---")
    csv_data = "email,full_name,course_id\nvalid@example.com,Valid Name,invalid-course-id"
    files = {"file": ("upload.csv", csv_data, "text/csv")}
    response = client.post("/api/v1/enrol/bulk/preview", files=files)
    print("Response Status:", response.status_code)
    print("Response JSON:", json.dumps(response.json(), indent=2))
    
    print("\n--- 4. Cross Org Preview ---")
    # Let's create a cross-org course
    cross_course = Course(id="cross-1", org_id=2, title="Cross", status="published", category_slug="general")
    db_session.add(cross_course)
    db_session.commit()
    csv_data = f"email,full_name,course_id\nvalid@example.com,Valid Name,cross-1"
    files = {"file": ("upload.csv", csv_data, "text/csv")}
    response = client.post("/api/v1/enrol/bulk/preview", files=files)
    print("Response Status:", response.status_code)
    print("Response JSON:", json.dumps(response.json(), indent=2))
    
    print("\n--- 5. Execute Batch ---")
    payload = {
        "rows": [
            {"email": exist_user.email, "full_name": "Exist User", "course_id": course.id},
            {"email": "newbulk@example.com", "full_name": "New Bulk User", "course_id": course.id}
        ]
    }
    response = client.post("/api/v1/enrol/bulk/execute", json=payload)
    print("Response Status:", response.status_code)
    print("Response JSON:", json.dumps(response.json(), indent=2))
    
    print("\n--- 6. Duplicate Execute (Idempotency) ---")
    response = client.post("/api/v1/enrol/bulk/execute", json=payload)
    print("Response Status:", response.status_code)
    print("Response JSON:", json.dumps(response.json(), indent=2))
    
    print("\n--- 7. Database Verification ---")
    new_user = db_session.query(User).filter_by(email="newbulk@example.com").first()
    print("New user created in DB:", new_user is not None)
    
    progress_exist = db_session.query(CourseProgress).filter_by(user_id=exist_user.id, course_id=course.id).first()
    print(f"Progress for existing user (enrolled_version):", getattr(progress_exist, 'enrolled_version', None))
    
    progress_new = db_session.query(CourseProgress).filter_by(user_id=new_user.id if new_user else None, course_id=course.id).first()
    print(f"Progress for new user (enrolled_version):", getattr(progress_new, 'enrolled_version', None))
    
    audit_logs = db_session.query(AuditLog).filter_by(action="enrollment.manual").all()
    print("Audit log count for enrollment.manual:", len(audit_logs))

