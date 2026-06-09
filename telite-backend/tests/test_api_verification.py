import requests
import pytest

BASE_URL = "http://127.0.0.1:8000"

def get_learner_token():
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": "lr_tenanta", "password": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200, f"Failed to login: {response.text}"
    return response.json()["access_token"]

def test_learner_courses():
    token = get_learner_token()
    response = requests.get(
        f"{BASE_URL}/api/v1/learner/courses",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    courses = response.json()
    assert len(courses) > 0
    # verify course A is returned
    course_a = next((c for c in courses if c["name"] == "Course A"), None)
    assert course_a is not None
    assert course_a["completion_rate"] == 0.0 or course_a["completion_rate"] == 100.0

def test_learner_progress():
    token = get_learner_token()
    
    # Let's get courses first
    courses_resp = requests.get(
        f"{BASE_URL}/api/v1/learner/courses",
        headers={"Authorization": f"Bearer {token}"}
    )
    course_a_id = next(c["id"] for c in courses_resp.json() if c["name"] == "Course A")

    from dotenv import load_dotenv
    load_dotenv()
    from app.db.engine import get_engine
    from sqlalchemy.orm import Session
    from app.models.course_module import CourseModule
    engine = get_engine()
    with Session(engine) as session:
        mod = session.query(CourseModule).filter_by(course_id=course_a_id).first()
        module_id = mod.id if mod else 1

    payload = {
        "course_id": course_a_id,
        "module_updates": [
            {
                "module_id": module_id,
                "status": "completed",
                "last_block_id": "blk1",
                "video_position_seconds": 120
            }
        ]
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/learner/progress",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
