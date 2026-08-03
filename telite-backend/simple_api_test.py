"""
Simple API test to identify HTTP 500 errors
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def simple_test():
    print("Starting simple API test...")
    
    # Login as learner directly
    session = requests.Session()
    learner_data = {
        "username": "kt_learner_1",
        "password": "KTLearner@1234"
    }
    
    print("1. Login as learner...")
    response = session.post(f"{BASE_URL}/auth/login", data=learner_data)
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   Login failed: {response.text}")
        return
    
    print("   Login successful")
    
    # Get courses as learner
    print("2. Get courses as learner...")
    response = session.get(f"{BASE_URL}/api/v1/learner/courses")
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   Failed: {response.text}")
        return
    
    learner_courses = response.json()
    print(f"   Learner courses: {len(learner_courses)}")
    if not learner_courses:
        print("   No courses available")
        return
    
    learner_course_id = learner_courses[0]["id"]
    print(f"   Using course: {learner_course_id}")
    
    # Get specific course
    print(f"3. Get course {learner_course_id}...")
    response = session.get(f"{BASE_URL}/api/v1/learner/courses/{learner_course_id}")
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   Failed: {response.text}")
        return
    
    print("   Course access successful")
    course_data = response.json()
    print(f"   Course: {course_data.get('name')}")
    
    # Try to post progress
    print("4. Test POST progress...")
    sections = course_data.get('sections', [])
    if sections:
        modules = sections[0].get('modules', [])
        if modules:
            module_id = modules[0]['id']
            print(f"   Using module_id: {module_id}")
            progress_data = {
                "course_id": learner_course_id,
                "module_updates": [{"module_id": module_id, "status": "completed"}]
            }
            response = session.post(f"{BASE_URL}/api/v1/learner/progress", json=progress_data)
            print(f"   Status: {response.status_code}")
            if response.status_code != 200:
                print(f"   Failed: {response.text}")
            else:
                print("   POST progress successful")
                
                # Test section progress
                print("5. Test GET section-progress...")
                response = session.get(f"{BASE_URL}/api/v1/learner/courses/{learner_course_id}/section-progress")
                print(f"   Status: {response.status_code}")
                if response.status_code != 200:
                    print(f"   Failed: {response.text}")
                else:
                    print("   GET section-progress successful")
                    section_progress = response.json()
                    print(f"   Section progress keys: {list(section_progress.keys())[:5]}")
        else:
            print("   No modules in first section")
    else:
        print("   No sections in course")
    
    print("Test complete")

if __name__ == "__main__":
    simple_test()
