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
import uuid

def mock_require_admin():
    return TokenData(id="admin-1", email="admin@example.com", full_name="Admin", role="platform_admin", org_id=1, is_platform_admin=True)

app.dependency_overrides[require_admin] = mock_require_admin
client = TestClient(app)
from app.models.organization import Organization

def test_manual_script(db_session):
    # Setup test data
    org1 = Organization(id=1, name="Org 1", plan="Pro", type="b2b", slug="org1", domain="org1.com")
    org2 = Organization(id=2, name="Org 2", plan="Pro", type="b2b", slug="org2", domain="org2.com")
    db_session.add(org1)
    db_session.add(org2)
    db_session.flush()
    
    c_id = str(uuid.uuid4())
    course = Course(id=c_id, org_id=1, name="Test Course", status="published", category_slug="slug", tier="Basic", slug="test")
    db_session.add(course)
    
    u_id = str(uuid.uuid4())
    user = User(
        id=u_id, org_id=1, username="exist", email="exist@example.com", full_name="Exist", is_active=True, role="learner",
        password_hash="hash", avatar_initials="EU", gradient_start="#000", gradient_end="#FFF"
    )
    db_session.add(user)
    
    cross_id = str(uuid.uuid4())
    cross_course = Course(id=cross_id, org_id=2, name="Cross Course", status="published", category_slug="slug", tier="Basic", slug="cross")
    db_session.add(cross_course)
    
    db_session.commit()
    
    # 1. Valid Preview
    csv_data = f"email,full_name,course_id\nexist@example.com,Exist User,{c_id}\nnewbulk@example.com,New Bulk User,{c_id}"
    files = {"file": ("upload.csv", csv_data, "text/csv")}
    r1 = client.post("/api/v1/enrol/bulk/preview", files=files)
    print("PREVIEW 1:", json.dumps(r1.json(), indent=2))
    
    # 2. Invalid Email
    csv_data2 = f"email,full_name,course_id\nbademail,,{c_id}"
    r2 = client.post("/api/v1/enrol/bulk/preview", files={"file": ("upload.csv", csv_data2, "text/csv")})
    print("PREVIEW 2:", json.dumps(r2.json(), indent=2))
    
    # 3. Cross Org Course
    csv_data3 = f"email,full_name,course_id\nvalid@example.com,,{cross_id}"
    r3 = client.post("/api/v1/enrol/bulk/preview", files={"file": ("upload.csv", csv_data3, "text/csv")})
    print("PREVIEW 3:", json.dumps(r3.json(), indent=2))
    
    # 4. Execute
    payload = {"rows": r1.json()["preview"]}
    r4 = client.post("/api/v1/enrol/bulk/execute", json=payload)
    print("EXECUTE 1:", json.dumps(r4.json(), indent=2))
    
    # 5. Execute Duplicate
    r5 = client.post("/api/v1/enrol/bulk/execute", json=payload)
    print("EXECUTE DUPLICATE:", json.dumps(r5.json(), indent=2))
    
    # 6. DB check
    new_user = db_session.query(User).filter_by(email="newbulk@example.com").first()
    print("NEW USER CREATED:", new_user is not None)
    
    audits = db_session.query(AuditLog).filter(AuditLog.action=="enrollment.manual").all()
    print("AUDIT COUNT:", len(audits))

