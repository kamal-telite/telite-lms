"""
Test API endpoints directly to identify HTTP 500 errors
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_api_endpoints():
    print("=" * 80)
    print("TESTING API ENDPOINTS DIRECTLY")
    print("=" * 80)
    
    # Login
    print("\n1. Login...")
    session = requests.Session()
    login_data = {
        "username": "globaladmin",
        "password": "GlobalAdmin@1234"
    }
    
    try:
        response = session.post(f"{BASE_URL}/auth/login", data=login_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   [OK] Login successful")
        else:
            print(f"   [FAIL] Login failed: {response.text}")
            return
    except Exception as e:
        print(f"   [FAIL] Login error: {e}")
        return
    
    # Get learner courses
    print("\n2. GET /api/v1/learner/courses...")
    try:
        response = session.get(f"{BASE_URL}/api/v1/learner/courses")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   [OK] GET learner/courses successful")
            courses = response.json()
            if courses and len(courses) > 0:
                course_id = courses[0]["id"]
                print(f"   Using course_id: {course_id}")
            else:
                print("   [FAIL] No courses available")
                return
        else:
            print(f"   [FAIL] GET learner/courses failed: {response.text}")
            return
    except Exception as e:
        print(f"   [FAIL] GET learner/courses error: {e}")
        return
    
    # Get specific course
    print(f"\n3. GET /api/v1/learner/courses/{course_id}...")
    try:
        response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   [OK] GET learner/courses/{id} successful")
            course_data = response.json()
            print(f"   Course name: {course_data.get('name')}")
            
            # Get a module for testing
            sections = course_data.get('sections', [])
            if sections and len(sections) > 0:
                modules = sections[0].get('modules', [])
                if modules and len(modules) > 0:
                    module_id = modules[0]['id']
                    print(f"   Using module_id: {module_id}")
                else:
                    print("   [FAIL] No modules found in first section")
                    return
            else:
                print("   [FAIL] No sections found")
                return
        else:
            print(f"   [FAIL] GET learner/courses/{id} failed: {response.text}")
            return
    except Exception as e:
        print(f"   [FAIL] GET learner/courses/{id} error: {e}")
        return
    
    # POST /api/v1/learner/progress
    print(f"\n4. POST /api/v1/learner/progress...")
    try:
        progress_data = {
            "course_id": course_id,
            "module_updates": [
                {
                    "module_id": module_id,
                    "status": "completed"
                }
            ]
        }
        response = session.post(f"{BASE_URL}/api/v1/learner/progress", json=progress_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   [OK] POST learner/progress successful")
        else:
            print(f"   [FAIL] POST learner/progress failed: {response.text}")
    except Exception as e:
        print(f"   [FAIL] POST learner/progress error: {e}")
    
    # POST /api/v1/learner/learning-sessions/start
    print(f"\n5. POST /api/v1/learner/learning-sessions/start...")
    try:
        session_data = {
            "course_id": course_id,
            "module_id": module_id
        }
        response = session.post(f"{BASE_URL}/api/v1/learner/learning-sessions/start", json=session_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   [OK] POST learning-sessions/start successful")
            session_result = response.json()
            session_id = session_result.get('session', {}).get('id')
            print(f"   Session ID: {session_id}")
        else:
            print(f"   [FAIL] POST learning-sessions/start failed: {response.text}")
            session_id = None
    except Exception as e:
        print(f"   [FAIL] POST learning-sessions/start error: {e}")
        session_id = None
    
    # POST /api/v1/learner/learning-sessions/heartbeat
    if session_id:
        print(f"\n6. POST /api/v1/learner/learning-sessions/heartbeat...")
        try:
            heartbeat_data = {
                "session_id": session_id,
                "course_id": course_id,
                "module_id": module_id,
                "active_seconds": 30
            }
            response = session.post(f"{BASE_URL}/api/v1/learner/learning-sessions/heartbeat", json=heartbeat_data)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   [OK] POST learning-sessions/heartbeat successful")
            else:
                print(f"   [FAIL] POST learning-sessions/heartbeat failed: {response.text}")
        except Exception as e:
            print(f"   [FAIL] POST learning-sessions/heartbeat error: {e}")
    
    # GET /api/v1/learner/courses/{course_id}/section-progress
    print(f"\n7. GET /api/v1/learner/courses/{course_id}/section-progress...")
    try:
        response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}/section-progress")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   [OK] GET section-progress successful")
            section_progress = response.json()
            print(f"   Section progress: {json.dumps(section_progress, indent=2)[:500]}")
        else:
            print(f"   [FAIL] GET section-progress failed: {response.text}")
    except Exception as e:
        print(f"   [FAIL] GET section-progress error: {e}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_api_endpoints()
