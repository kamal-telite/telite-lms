import os, sys
os.environ['TELITE_DB_BACKEND'] = 'postgres'
os.environ['TELITE_DATABASE_URL'] = 'postgresql+psycopg://postgres:postgres123@localhost:5432/test_telite_backend'
os.environ['TELITE_PASSWORD_SALT'] = 'ci-test-salt'
from fastapi.testclient import TestClient
from app.main import app
from tests.test_api import TEST_ADMIN_PASSWORD
client = TestClient(app)
resp = client.post('/auth/login', json={'username': 'anika', 'password': TEST_ADMIN_PASSWORD})
headers = {'Authorization': f'Bearer {resp.json()["access_token"]}'}
res = client.post('/tasks', json={'title': 't', 'assigned_label': 'l', 'category_slug': 'ats'}, headers=headers)
print('STATUS:', res.status_code)
print('BODY:', res.json())
