import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8001"

def test_global_admin():
    print("Testing Global Admin Access...")
    
    # 1. Login as global admin
    login_data = {
        "username": "globaladmin",
        "password": "GlobalAdmin@1234"
    }
    
    try:
        print(f"Logging in to {BASE_URL}/auth/login...")
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data, timeout=5)
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the backend server. Is it running on port 8001?")
        sys.exit(1)
        
    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        print(response.text)
        sys.exit(1)
        
    print("Login successful! Status code: 200")
    
    token = response.json().get("access_token")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 2. Check current user profile (shows platform admin flags)
    print("\nFetching current user profile...")
    me_resp = requests.get(f"{BASE_URL}/users/me", headers=headers)
    if me_resp.status_code == 200:
        user_data = me_resp.json()
        print(f"User Role: {user_data.get('role')}")
        print(f"Is Platform Admin: {user_data.get('is_platform_admin')}")
    else:
        print("Failed to fetch profile:", me_resp.text)
        
    # 3. Test a platform-admin only endpoint (e.g., listing all organizations)
    # The Global Admin has no org scope limitation
    print("\nTesting platform-admin capabilities (fetching organizations)...")
    orgs_resp = requests.get(f"{BASE_URL}/platform/organizations", headers=headers)
    if orgs_resp.status_code == 200:
        orgs = orgs_resp.json()
        print(f"Successfully fetched {len(orgs)} organizations globally!")
        for org in orgs:
            print(f" - {org.get('name')} (Plan: {org.get('plan')})")
    elif orgs_resp.status_code == 404:
         print("Platform endpoint not found, falling back to standard list...")
    elif orgs_resp.status_code in [401, 403]:
        print("Access denied! This user is not recognized as a platform admin.")
    else:
        print(f"Organizations fetch returned {orgs_resp.status_code}: {orgs_resp.text}")

if __name__ == "__main__":
    test_global_admin()
