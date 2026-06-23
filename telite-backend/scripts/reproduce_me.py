import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8001"

def login():
    login_data = {
        "username": "kt_category_admin",
        "password": "KTCategory@1234"
    }
    resp = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if resp.status_code != 200:
        print("Login failed!", resp.text)
        sys.exit(1)
    return resp.json()["access_token"]

def manual_enroll(token, full_name, email, course_ids):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "full_name": full_name,
        "email": email,
        "course_ids": course_ids,
        "enrollment_type": "manual"
    }
    resp = requests.post(f"{BASE_URL}/api/v1/enrol/manual", headers=headers, json=payload)
    return resp

def main():
    token = login()
    print("--- Reproducing ME-003: New Learner Creation ---")
    resp3 = manual_enroll(token, "New Learner 003", "me003@test.local", ["course-python"])
    print(f"ME-003 Status: {resp3.status_code}")
    print(f"ME-003 Response: {resp3.text}")
    print("\n-------------------------------------------------\n")

    print("--- Reproducing ME-004: Existing Learner Enrollment into Course B (Different Category) ---")
    resp4 = manual_enroll(token, "KT Learner 1", "learner1@ktlearn.local", ["course-docker"])
    print(f"ME-004 Status: {resp4.status_code}")
    print(f"ME-004 Response: {resp4.text}")

if __name__ == "__main__":
    main()
