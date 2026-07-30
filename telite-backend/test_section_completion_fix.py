"""
Test the section completion fix
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_section_completion():
    print("Testing section completion fix...")
    
    # Login as learner
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
    
    # Get courses
    print("2. Get courses...")
    response = session.get(f"{BASE_URL}/api/v1/learner/courses")
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   Failed: {response.text}")
        return
    
    courses = response.json()
    print(f"   Available courses: {len(courses)}")
    
    # Find the React course with time requirements
    react_course = None
    for course in courses:
        if 'React' in course.get('name', ''):
            react_course = course
            break
    
    if not react_course:
        print("   React course not found")
        return
    
    course_id = react_course["id"]
    print(f"   Using course: {react_course['name']} ({course_id})")
    
    # Get course details
    print(f"3. Get course details...")
    response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}")
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   Failed: {response.text}")
        return
    
    course_data = response.json()
    sections = course_data.get('sections', [])
    print(f"   Sections: {len(sections)}")
    
    # Find a section with time requirements
    target_section = None
    target_module = None
    for section in sections:
        if section.get('minimum_time_seconds', 0) > 0:
            modules = section.get('modules', [])
            if modules:
                target_section = section
                target_module = modules[0]
                break
    
    if not target_section:
        print("   No section with time requirements found")
        return
    
    section_id = target_section['id']
    module_id = target_module['id']
    min_time = target_section['minimum_time_seconds']
    print(f"   Target section: {target_section['title']} (ID: {section_id})")
    print(f"   Minimum time: {min_time}s")
    print(f"   Target module: {target_module['title']} (ID: {module_id})")
    
    # Get current section progress
    print(f"4. Get current section progress...")
    response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}/section-progress")
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   Failed: {response.text}")
        return
    
    section_progress = response.json()
    current_section_progress = section_progress.get(str(section_id)) or section_progress.get(section_id)
    print(f"   Current section progress: {current_section_progress}")
    
    # Simulate spending time in the section by sending heartbeat
    print(f"5. Simulate time spent via heartbeat...")
    
    # Start learning session
    session_response = session.post(f"{BASE_URL}/api/v1/learner/learning-sessions/start", json={
        "course_id": course_id,
        "module_id": module_id
    })
    print(f"   Start session status: {session_response.status_code}")
    
    if session_response.status_code == 200:
        session_data = session_response.json()
        learning_session_id = session_data.get('session', {}).get('id')
        print(f"   Learning session ID: {learning_session_id}")
        
        # Send heartbeat with enough time to meet requirement
        heartbeat_response = session.post(f"{BASE_URL}/api/v1/learner/learning-sessions/heartbeat", json={
            "session_id": learning_session_id,
            "course_id": course_id,
            "module_id": module_id,
            "active_seconds": min_time + 10  # Add some buffer
        })
        print(f"   Heartbeat status: {heartbeat_response.status_code}")
        
        if heartbeat_response.status_code == 200:
            print("   Heartbeat successful")
            
            # Check section progress again
            print(f"6. Check section progress after heartbeat...")
            response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}/section-progress")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                new_section_progress = response.json()
                new_current_section_progress = new_section_progress.get(str(section_id)) or new_section_progress.get(section_id)
                print(f"   New section progress: {new_current_section_progress}")
                
                # Check if section is now marked as completed
                if new_current_section_progress.get('status') == 'completed':
                    print("   [OK] Section marked as completed (FIX WORKING)")
                else:
                    print("   [FAIL] Section not marked as completed (FIX NOT WORKING)")
            else:
                print(f"   Failed: {response.text}")
        else:
            print(f"   Heartbeat failed: {heartbeat_response.text}")
    else:
        print(f"   Start session failed: {session_response.text}")
    
    print("Test complete")

if __name__ == "__main__":
    test_section_completion()
