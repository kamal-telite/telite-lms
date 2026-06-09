import sys
import json
import requests
sys.path.append('.')
from app.api.auth import create_access_token
from app.services.store import get_conn

with get_conn() as conn:
    user = conn.execute("SELECT * FROM users WHERE role='super_admin' LIMIT 1").fetchone()

token = create_access_token({'sub': user['id'], 'role': user['role']})
url = 'http://localhost:8001/enrol/manual'
headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
payload = {
    'full_name': 'shivam',
    'email': 'kamalpandey12345coc25@gmail.com',
    'category_slug': 'iot',
    'course_ids': ['iot_test-1'],
    'enrollment_type': 'manual',
    'note': 'this is learner 1'
}
response = requests.post(url, headers=headers, json=payload)
print(f'Status: {response.status_code}')
print(f'Response: {response.text}')
