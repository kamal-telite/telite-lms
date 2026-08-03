"""
Test script to reproduce the learner progression bugs.
Tests the three APIs that are reportedly returning HTTP 500:
1. POST /api/v1/learner/progress
2. POST /api/v1/learner/learning-sessions/heartbeat
3. GET /api/v1/learner/courses/{courseId}
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_login():
    """Test login to get auth cookies"""
    print("=" * 80)
    print("TEST 1: Login")
    print("=" * 80)
    
    login_data = {
        "username": "globaladmin",
        "password": "GlobalAdmin@1234"
    }
    
    try:
        session = requests.Session()
        response = session.post(f"{BASE_URL}/auth/login", data=login_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            print("[OK] Login successful")
            return session
        else:
            print("[FAIL] Login failed")
            return None
    except Exception as e:
        print(f"[FAIL] Login error: {e}")
        return None

def test_get_learner_courses(session):
    """Test GET /api/v1/learner/courses"""
    print("\n" + "=" * 80)
    print("TEST 2: GET /api/v1/learner/courses")
    print("=" * 80)
    
    try:
        response = session.get(f"{BASE_URL}/api/v1/learner/courses")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            print("[OK] GET learner/courses successful")
            return response.json()
        else:
            print("[FAIL] GET learner/courses failed")
            return None
    except Exception as e:
        print(f"[FAIL] GET learner/courses error: {e}")
        return None

def test_get_learner_course(session, course_id):
    """Test GET /api/v1/learner/courses/{id}"""
    print("\n" + "=" * 80)
    print(f"TEST 3: GET /api/v1/learner/courses/{course_id}")
    print("=" * 80)
    
    try:
        response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            print("[OK] GET learner/courses/{id} successful")
            return response.json()
        else:
            print("[FAIL] GET learner/courses/{id} failed")
            return None
    except Exception as e:
        print(f"[FAIL] GET learner/courses/{id} error: {e}")
        return None

def test_post_progress(session, course_id, module_id):
    """Test POST /api/v1/learner/progress"""
    print("\n" + "=" * 80)
    print("TEST 4: POST /api/v1/learner/progress")
    print("=" * 80)
    
    progress_data = {
        "course_id": course_id,
        "module_updates": [
            {
                "module_id": module_id,
                "status": "completed"
            }
        ]
    }
    
    try:
        response = session.post(f"{BASE_URL}/api/v1/learner/progress", json=progress_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            print("[OK] POST learner/progress successful")
            return response.json()
        else:
            print("[FAIL] POST learner/progress failed")
            return None
    except Exception as e:
        print(f"[FAIL] POST learner/progress error: {e}")
        return None

def test_start_learning_session(session, course_id, module_id):
    """Test POST /api/v1/learner/learning-sessions/start"""
    print("\n" + "=" * 80)
    print("TEST 5: POST /api/v1/learner/learning-sessions/start")
    print("=" * 80)
    
    session_data = {
        "course_id": course_id,
        "module_id": module_id
    }
    
    try:
        response = session.post(f"{BASE_URL}/api/v1/learner/learning-sessions/start", json=session_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            print("[OK] POST learning-sessions/start successful")
            return response.json()
        else:
            print("[FAIL] POST learning-sessions/start failed")
            return None
    except Exception as e:
        print(f"[FAIL] POST learning-sessions/start error: {e}")
        return None

def test_heartbeat_learning_session(session, session_id, course_id, module_id):
    """Test POST /api/v1/learner/learning-sessions/heartbeat"""
    print("\n" + "=" * 80)
    print("TEST 6: POST /api/v1/learner/learning-sessions/heartbeat")
    print("=" * 80)
    
    heartbeat_data = {
        "session_id": session_id,
        "course_id": course_id,
        "module_id": module_id,
        "active_seconds": 30
    }
    
    try:
        response = session.post(f"{BASE_URL}/api/v1/learner/learning-sessions/heartbeat", json=heartbeat_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            print("[OK] POST learning-sessions/heartbeat successful")
            return response.json()
        else:
            print("[FAIL] POST learning-sessions/heartbeat failed")
            return None
    except Exception as e:
        print(f"[FAIL] POST learning-sessions/heartbeat error: {e}")
        return None

def test_get_section_progress(session, course_id):
    """Test GET /api/v1/learner/courses/{course_id}/section-progress"""
    print("\n" + "=" * 80)
    print(f"TEST 7: GET /api/v1/learner/courses/{course_id}/section-progress")
    print("=" * 80)
    
    try:
        response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}/section-progress")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            print("[OK] GET section-progress successful")
            return response.json()
        else:
            print("[FAIL] GET section-progress failed")
            return None
    except Exception as e:
        print(f"[FAIL] GET section-progress error: {e}")
        return None

def main():
    print("REPRODUCING LEARNER PROGRESSION BUGS")
    print("=" * 80)
    
    # Test 1: Login
    session = test_login()
    if not session:
        print("\nCannot proceed without login")
        sys.exit(1)
    
    # Test 2: Get learner courses
    courses = test_get_learner_courses(session)
    if not courses or len(courses) == 0:
        print("\nNo courses available for testing")
        sys.exit(1)
    
    course_id = courses[0]["id"]
    print(f"\nUsing course_id: {course_id}")
    
    # Test 3: Get specific course details
    course_data = test_get_learner_course(session, course_id)
    if not course_data:
        print("\nCannot get course details")
        sys.exit(1)
    
    # Find a module to test with
    modules = []
    if "sections" in course_data:
        for section in course_data["sections"]:
            if "modules" in section:
                modules.extend(section["modules"])
    elif "modules_json" in course_data:
        modules = course_data["modules_json"]
    
    if not modules:
        print("\nNo modules found in course")
        sys.exit(1)
    
    module_id = modules[0]["id"]
    print(f"Using module_id: {module_id}")
    
    # Test 4: Post progress
    progress_result = test_post_progress(session, course_id, module_id)
    
    # Test 5: Start learning session
    session_result = test_start_learning_session(session, course_id, module_id)
    
    if session_result and "session" in session_result:
        session_id = session_result["session"]["id"]
        print(f"Using session_id: {session_id}")
        
        # Test 6: Heartbeat learning session
        heartbeat_result = test_heartbeat_learning_session(session, session_id, course_id, module_id)
    else:
        print("\nCannot test heartbeat without session")
    
    # Test 7: Get section progress
    section_progress = test_get_section_progress(session, course_id)
    
    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
