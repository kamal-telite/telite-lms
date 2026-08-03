"""
Test API access with globaladmin user
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_api_access():
    print("=" * 80)
    print("TESTING API ACCESS WITH GLOBALADMIN")
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
    print("\n2. Get learner courses...")
    try:
        response = session.get(f"{BASE_URL}/api/v1/learner/courses")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   [OK] Get learner courses successful")
            courses = response.json()
            if courses and len(courses) > 0:
                course_id = courses[0]["id"]
                print(f"   Using course_id: {course_id}")
            else:
                print("   [FAIL] No courses available")
                return
        else:
            print(f"   [FAIL] Get learner courses failed: {response.text}")
            return
    except Exception as e:
        print(f"   [FAIL] Get learner courses error: {e}")
        return
    
    # Get specific course
    print(f"\n3. Get specific course ({course_id})...")
    try:
        response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   [OK] Get specific course successful")
            course_data = response.json()
            print(f"   Course name: {course_data.get('name')}")
            print(f"   Sections: {len(course_data.get('sections', []))}")
            
            # Check for sections with minimum_time_seconds
            for section in course_data.get('sections', []):
                min_time = section.get('minimum_time_seconds')
                if min_time and min_time > 0:
                    print(f"   Section '{section.get('title')}' has minimum_time_seconds: {min_time}")
        else:
            print(f"   [FAIL] Get specific course failed: {response.text}")
            return
    except Exception as e:
        print(f"   [FAIL] Get specific course error: {e}")
        return
    
    # Get section progress
    print(f"\n4. Get section progress...")
    try:
        response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}/section-progress")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   [OK] Get section progress successful")
            section_progress = response.json()
            print(f"   Section progress data: {json.dumps(section_progress, indent=2)[:500]}")
        else:
            print(f"   [FAIL] Get section progress failed: {response.text}")
    except Exception as e:
        print(f"   [FAIL] Get section progress error: {e}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_api_access()
