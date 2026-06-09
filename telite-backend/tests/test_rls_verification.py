import requests
import pytest
from dotenv import load_dotenv

load_dotenv()
BASE_URL = "http://127.0.0.1:8000"

def get_token(username, password):
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200, f"Failed to login: {response.text}"
    return response.json()["access_token"]

def test_cross_tenant_isolation_courses():
    # Tenant A Learner
    token_a = get_token("lr_tenanta", "password")
    
    # Tenant B Learner
    token_b = get_token("lr_tenantb", "password")

    # Get Tenant A's courses
    resp_a = requests.get(
        f"{BASE_URL}/api/v1/learner/courses",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert resp_a.status_code == 200
    courses_a = resp_a.json()
    assert any(c["name"] == "Course A" for c in courses_a)
    course_a_id = next(c["id"] for c in courses_a if c["name"] == "Course A")

    # Get Tenant B's courses
    resp_b = requests.get(
        f"{BASE_URL}/api/v1/learner/courses",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp_b.status_code == 200
    courses_b = resp_b.json()
    assert not any(c["id"] == course_a_id for c in courses_b), "Tenant B should not see Tenant A's courses"

    # Tenant B attempts to fetch Tenant A's specific course
    resp_b_direct = requests.get(
        f"{BASE_URL}/api/v1/learner/courses/{course_a_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    # Should be 404 or 403 due to RLS filtering it out (it doesn't exist for Tenant B)
    assert resp_b_direct.status_code in [403, 404], f"Tenant B directly accessed Tenant A's course! Status: {resp_b_direct.status_code}"
