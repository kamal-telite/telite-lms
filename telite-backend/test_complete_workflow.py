"""
Complete learner progression workflow test
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_complete_workflow():
    print("=" * 80)
    print("COMPLETE LEARNER PROGRESSION WORKFLOW TEST")
    print("=" * 80)
    
    # Login as learner
    session = requests.Session()
    learner_data = {
        "username": "kt_learner_1",
        "password": "KTLearner@1234"
    }
    
    print("\n1. Login as learner...")
    response = session.post(f"{BASE_URL}/auth/login", data=learner_data)
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   Login failed: {response.text}")
        return False
    
    print("   [OK] Login successful")
    
    # Get courses
    print("\n2. Get learner courses...")
    response = session.get(f"{BASE_URL}/api/v1/learner/courses")
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   Failed: {response.text}")
        return False
    
    courses = response.json()
    print(f"   [OK] Available courses: {len(courses)}")
    
    # Find React course
    react_course = None
    for course in courses:
        if 'React' in course.get('name', ''):
            react_course = course
            break
    
    if not react_course:
        print("   [FAIL] React course not found")
        return False
    
    course_id = react_course["id"]
    print(f"   Using course: {react_course['name']} ({course_id})")
    
    # Get course details
    print(f"\n3. Get course details...")
    response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}")
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   Failed: {response.text}")
        return False
    
    course_data = response.json()
    sections = course_data.get('sections', [])
    print(f"   [OK] Course sections: {len(sections)}")
    
    # Find a section with time requirements that's not completed
    print(f"\n4. Find target section with time requirements...")
    target_section = None
    target_module = None
    
    response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}/section-progress")
    if response.status_code == 200:
        section_progress = response.json()
        
        for section in sections:
            if section.get('minimum_time_seconds', 0) > 0:
                current_progress = section_progress.get(str(section['id'])) or section_progress.get(section['id'])
                if current_progress and current_progress.get('status') != 'completed':
                    modules = section.get('modules', [])
                    if modules:
                        target_section = section
                        target_module = modules[0]
                        break
    
    if not target_section:
        print("   [INFO] No incomplete section with time requirements found")
        print("   [INFO] Creating a new test scenario...")
        
        # Use the first section with time requirements
        for section in sections:
            if section.get('minimum_time_seconds', 0) > 0:
                modules = section.get('modules', [])
                if modules:
                    target_section = section
                    target_module = modules[0]
                    break
    
    if not target_section:
        print("   [FAIL] No section with time requirements found")
        return False
    
    section_id = target_section['id']
    module_id = target_module['id']
    min_time = target_section['minimum_time_seconds']
    print(f"   [OK] Target section: {target_section['title']} (ID: {section_id})")
    print(f"   [OK] Minimum time: {min_time}s")
    print(f"   [OK] Target module: {target_module['title']} (ID: {module_id})")
    
    # Get initial section progress
    print(f"\n5. Get initial section progress...")
    response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}/section-progress")
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   Failed: {response.text}")
        return False
    
    section_progress = response.json()
    initial_progress = section_progress.get(str(section_id)) or section_progress.get(section_id)
    print(f"   [OK] Initial progress: {initial_progress}")
    
    # Test timer initialization
    print(f"\n6. Test timer initialization...")
    time_spent = initial_progress.get('time_spent_seconds', 0) if initial_progress else 0
    remaining_time = max(0, min_time - time_spent)
    print(f"   [OK] Time spent: {time_spent}s")
    print(f"   [OK] Remaining time: {remaining_time}s")
    print(f"   [OK] Timer should show: {remaining_time // 60}:{remaining_time % 60:02d}")
    
    # Start learning session
    print(f"\n7. Start learning session...")
    session_response = session.post(f"{BASE_URL}/api/v1/learner/learning-sessions/start", json={
        "course_id": course_id,
        "module_id": module_id
    })
    print(f"   Status: {session_response.status_code}")
    
    if session_response.status_code != 200:
        print(f"   Failed: {session_response.text}")
        return False
    
    session_data = session_response.json()
    learning_session_id = session_data.get('session', {}).get('id')
    print(f"   [OK] Learning session ID: {learning_session_id}")
    
    # Simulate time progression with multiple heartbeats
    print(f"\n8. Simulate time progression with heartbeats...")
    total_time_to_add = min_time + 30  # Add buffer
    heartbeat_chunks = 3
    time_per_chunk = total_time_to_add // heartbeat_chunks
    
    for i in range(heartbeat_chunks):
        heartbeat_response = session.post(f"{BASE_URL}/api/v1/learner/learning-sessions/heartbeat", json={
            "session_id": learning_session_id,
            "course_id": course_id,
            "module_id": module_id,
            "active_seconds": time_per_chunk
        })
        print(f"   Heartbeat {i+1}/{heartbeat_chunks} status: {heartbeat_response.status_code}")
        
        if heartbeat_response.status_code != 200:
            print(f"   Failed: {heartbeat_response.text}")
            return False
        
        # Check progress after each heartbeat
        progress_response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}/section-progress")
        if progress_response.status_code == 200:
            new_section_progress = progress_response.json()
            current_progress = new_section_progress.get(str(section_id)) or new_section_progress.get(section_id)
            print(f"   Progress after heartbeat {i+1}: {current_progress.get('time_spent_seconds')}s, status: {current_progress.get('status')}")
    
    print("   [OK] All heartbeats successful")
    
    # Check final section progress
    print(f"\n9. Check final section progress...")
    response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}/section-progress")
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   Failed: {response.text}")
        return False
    
    final_section_progress = response.json()
    final_progress = final_section_progress.get(str(section_id)) or final_section_progress.get(section_id)
    print(f"   [OK] Final progress: {final_progress}")
    
    # Validate section completion
    print(f"\n10. Validate section completion...")
    if final_progress.get('status') == 'completed':
        print("   [OK] Section marked as completed")
    else:
        print(f"   [FAIL] Section not marked as completed: {final_progress.get('status')}")
        return False
    
    # Validate time requirement met
    if final_progress.get('time_spent_seconds', 0) >= min_time:
        print("   [OK] Time requirement met")
    else:
        print(f"   [FAIL] Time requirement not met: {final_progress.get('time_spent_seconds')} < {min_time}")
        return False
    
    # Test progress persistence by logging out and back in
    print(f"\n11. Test progress persistence (logout/login)...")
    logout_response = session.post(f"{BASE_URL}/auth/logout", {})
    print(f"   Logout status: {logout_response.status_code}")
    
    # Login again
    login_response = session.post(f"{BASE_URL}/auth/login", data=learner_data)
    print(f"   Login status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"   Login failed: {login_response.text}")
        return False
    
    print("   [OK] Re-login successful")
    
    # Check if progress persisted
    response = session.get(f"{BASE_URL}/api/v1/learner/courses/{course_id}/section-progress")
    print(f"   Section progress check status: {response.status_code}")
    
    if response.status_code == 200:
        persisted_progress = response.json()
        persisted_section_progress = persisted_progress.get(str(section_id)) or persisted_progress.get(section_id)
        print(f"   [OK] Persisted progress: {persisted_section_progress}")
        
        if persisted_section_progress.get('status') == 'completed':
            print("   [OK] Progress persisted correctly")
        else:
            print(f"   [FAIL] Progress not persisted: {persisted_section_progress.get('status')}")
            return False
    else:
        print(f"   Failed: {response.text}")
        return False
    
    print("\n" + "=" * 80)
    print("ALL TESTS PASSED")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = test_complete_workflow()
    exit(0 if success else 1)
