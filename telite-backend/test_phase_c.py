import sys
import os
import uuid
from sqlalchemy.orm import Session
from app.models.organization import Organization
from app.models.user import User
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.course_section import CourseSection
from app.models.course_version import CourseVersion
from app.models.lesson_block import LessonBlock
from app.models.media_asset import MediaAsset
from app.models.learning_path import LearningPath, LearningPathCourse
from app.api.auth import TokenData
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def setup_db(db: Session):
    # Setup Tenant A
    org_a = Organization(name="Tenant A", type="Enterprise", domain="tenanta.com", status="active", plan="enterprise")
    org_b = Organization(name="Tenant B", type="Enterprise", domain="tenantb.com", status="active", plan="enterprise")
    db.add(org_a)
    db.add(org_b)
    db.commit()
    db.refresh(org_a)
    db.refresh(org_b)
    
    # Setup Admins
    admin_a = User(id="admin_a", username="admin_a", email="admin@tenanta.com", full_name="Admin A", role="platform_admin", org_id=org_a.id, status="active")
    admin_b = User(id="admin_b", username="admin_b", email="admin@tenantb.com", full_name="Admin B", role="platform_admin", org_id=org_b.id, status="active")
    db.add(admin_a)
    db.add(admin_b)
    
    # Setup Course in Tenant A
    course_a = Course(id="course_a", category_slug="default", name="Course A", slug="course-a", tier="free", status="published", org_id=org_a.id)
    db.add(course_a)
    db.commit()
    db.refresh(admin_a)
    db.refresh(admin_b)
    db.refresh(course_a)
    
    return org_a, org_b, admin_a, admin_b, course_a

def get_headers(user: User):
    # Mocking the dependency is harder than just returning a TokenData if we use app.dependency_overrides
    pass

# We will override the get_current_user dependency dynamically in the tests
def run_tests():

    
    # Let's just create a session factory manually
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.engine import _build_dsn
    engine = create_engine(_build_dsn())
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        org_a, org_b, admin_a, admin_b, course_a = setup_db(db)
        
        print("=== PHASE C STAGING VALIDATION REPORT ===")
        
        # Test 1: Media Upload & Storage
        print("\\n1. Media Upload & Storage Verification")
        app.dependency_overrides[TokenData] = lambda: TokenData(user_id=admin_a.id, email=admin_a.email, role=admin_a.role, org_id=admin_a.org_id)
        from app.api.auth import get_current_user, require_admin
        app.dependency_overrides[get_current_user] = lambda: TokenData(user_id=admin_a.id, email=admin_a.email, role=admin_a.role, org_id=admin_a.org_id)
        app.dependency_overrides[require_admin] = lambda: TokenData(user_id=admin_a.id, email=admin_a.email, role=admin_a.role, org_id=admin_a.org_id)
        
        res = client.post("/api/authoring/media/presigned-url", json={"filename": "test.mp4", "mime_type": "video/mp4", "size_bytes": 10000})
        if res.status_code == 200:
            data = res.json()
            print("PASS: Presigned URL generated:", data["upload_url"])
            print("PASS: Media Asset ID mapped:", data["media_asset_id"])
        else:
            print("FAIL:", res.status_code, res.text)
            
        # Test 2: Course Publishing Lifecycle (Versions)
        print("\\n2. Course Publishing Lifecycle")
        res = client.post(f"/api/authoring/courses/{course_a.id}/versions")
        if res.status_code == 200:
            version_id = res.json()["version"]["id"]
            print("PASS: Draft version branched successfully:", version_id)
            
            res_pub = client.post(f"/api/authoring/courses/{course_a.id}/publish")
            if res_pub.status_code == 200:
                print("PASS: Draft published successfully")
            else:
                print("FAIL Publish:", res_pub.status_code, res_pub.text)
        else:
            print("FAIL Version:", res.status_code, res.text)
            
        # Test 3: Structural Endpoints
        print("\\n3. Structural Endpoints (Drag and Drop)")
        res = client.post(f"/api/authoring/courses/{course_a.id}/sections", json={"title": "Section 1", "sort_order": 1})
        if res.status_code == 200:
            section_id = res.json()["id"]
            print("PASS: Course Section created successfully:", section_id)
            
            # Create a module using standard DB (since moodle proxy will fail without Moodle mock)
            # Actually, the authoring proxy to moodle will fail in tests unless mocked.
            print("SKIP: Skipping PUT /structure because Moodle module proxy requires mocking")
        else:
            print("FAIL Section:", res.status_code, res.text)
            
        # Test 4: Learning Paths
        print("\\n4. Learning Paths Validation")
        res = client.post("/api/authoring/learning-paths", json={"title": "Test Path", "description": "Desc"})
        if res.status_code == 200:
            path_id = res.json()["id"]
            print("PASS: Learning Path created:", path_id)
            res_upd = client.put(f"/api/authoring/learning-paths/{path_id}/courses", json=[{"course_id": course_a.id, "sort_order": 1}])
            if res_upd.status_code == 200:
                print("PASS: Courses added to Learning Path")
            else:
                print("FAIL Path Update:", res_upd.status_code, res_upd.text)
        else:
            print("FAIL Path:", res.status_code, res.text)
            
        # Test 5: Tenant Isolation
        print("\\n5. Tenant Isolation Verification")
        # Change to Admin B
        app.dependency_overrides[get_current_user] = lambda: TokenData(user_id=admin_b.id, email=admin_b.email, role=admin_b.role, org_id=admin_b.org_id)
        app.dependency_overrides[require_admin] = lambda: TokenData(user_id=admin_b.id, email=admin_b.email, role=admin_b.role, org_id=admin_b.org_id)
        
        # Try to access Course A (Tenant A) as Admin B
        res = client.post(f"/api/authoring/courses/{course_a.id}/versions")
        if res.status_code == 404:
            print("PASS: Tenant Isolation successful. Admin B got 404 for Tenant A course.")
        else:
            print("FAIL Isolation:", res.status_code, res.text)
            
    except Exception as e:
        print("ERROR:", e)
    finally:
        # Cleanup
        db.query(LearningPathCourse).delete()
        db.query(LearningPath).delete()
        db.query(CourseSection).delete()
        db.query(CourseVersion).delete()
        db.query(MediaAsset).delete()
        db.query(Course).filter(Course.id == "course_a").delete()
        db.query(User).filter(User.id.in_(["admin_a", "admin_b"])).delete()
        db.query(Organization).filter(Organization.name.in_(["Tenant A", "Tenant B"])).delete()
        db.commit()
        db.close()

if __name__ == "__main__":
    run_tests()
