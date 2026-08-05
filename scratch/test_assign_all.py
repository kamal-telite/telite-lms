import requests

# Login as superadmin to get session cookie
s = requests.Session()
login_data = {"username": "kt_superadmin", "password": "password"}
s.post("http://localhost:8000/api/v1/auth/login", data=login_data)

# Get CSRF token
csrf_token = s.cookies.get("telite_csrf_token")
if not csrf_token:
    print("Failed to get CSRF token")
    exit(1)

# Create a task assigned to all learners
payload = {
    "title": "Welcome to Telite LMS",
    "description": "Please complete your profile setup.",
    "assigned_label": "All learners",
    "assigned_to_user_id": None,
    "assignment_scope": "all",
    "category_slug": "global",
    "due_at": "2026-12-31T23:59:59Z",
    "status": "pending",
    "type": "admin_task"
}

resp = s.post(
    "http://localhost:8000/api/v1/tasks",
    json=payload,
    headers={"X-CSRF-Token": csrf_token}
)
print("Create Task Response:", resp.status_code)
print(resp.json())
