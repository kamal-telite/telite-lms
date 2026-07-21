import requests
import json
import sys

BASE_URL = "http://localhost:8001"

def print_result(step, res, expected_status=200):
    if res.status_code == expected_status:
        print(f"SUCCESS: {step} ({res.status_code})")
        return res.json() if res.content else None
    else:
        print(f"FAILED: {step} - Expected {expected_status}, got {res.status_code}")
        print(f"Response: {res.text}")
        return None

print("--- Telite E2E Feature Verification ---")

# 1. AUTH
res = requests.post(f"{BASE_URL}/auth/login", data={"username": "globaladmin", "password": "GlobalAdmin@1234"})
token_data = print_result("Auth Login (GlobalAdmin)", res)
if not token_data: sys.exit(1)
token = token_data.get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# 2. PLATFORM ORGS
orgs = print_result("Get Organizations", requests.get(f"{BASE_URL}/api/platform/organizations", headers=headers))

# 3. PLATFORM CREATE ORG
new_org_data = {
    "name": "Audit Test Org",
    "domain": "audit.test.local",
    "contact_email": "admin@audit.test.local",
    "type": "company"
}
new_org = print_result("Create Organization", requests.post(f"{BASE_URL}/api/platform/organizations", json=new_org_data, headers=headers), expected_status=201)

# 4. MANAGEMENT USERS
users = print_result("Get Users", requests.get(f"{BASE_URL}/users", headers=headers))

# 5. MANAGEMENT CATEGORIES
categories = print_result("Get Categories", requests.get(f"{BASE_URL}/categories", headers=headers))
if categories:
    cat_items = categories if isinstance(categories, list) else categories.get("items", [])
    if cat_items and len(cat_items) > 0:
        cat_slug = cat_items[0].get("slug")
        # Fetch courses for category
        courses = print_result("Get Courses", requests.get(f"{BASE_URL}/categories/{cat_slug}/courses", headers=headers))


print("--- End of Verification ---")
