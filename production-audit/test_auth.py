import requests
import json
import sys

BASE_URL = "http://localhost:8001"

print("--- Testing Auth API ---")

# 1. Test Login
login_data = {
    "username": "globaladmin",
    "password": "GlobalAdmin@1234"
}
try:
    res = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if res.status_code == 200:
        token = res.json().get("access_token")
        print("Login successful. Received token.")
    else:
        print(f"Login failed! Status: {res.status_code}, Response: {res.text}")
        sys.exit(1)
        
    # 2. Test Get Me (Validate Token)
    headers = {"Authorization": f"Bearer {token}"}
    res_me = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    if res_me.status_code == 200:
        user_data = res_me.json()
        print(f"Token validated. User: {user_data.get('email')} (Role: {user_data.get('system_role')})")
    else:
        print(f"/auth/me failed! Status: {res_me.status_code}, Response: {res_me.text}")
        
except Exception as e:
    print(f"Exception occurred: {str(e)}")
