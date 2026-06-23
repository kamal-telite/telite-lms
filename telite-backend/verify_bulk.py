import os
import sys
import json
from io import BytesIO

# Set environment
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/telite_db"
# If necessary, seed or bypass DB for the test client.
# Let's use the same session setup the tests use, or just create a mock client.

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import SessionLocal
from app.models.user import User
from app.models.course import Course
from app.api.auth import TokenData

# We can mock the get_db Depends, and require_admin Depends if needed,
# or we can use the test database if it's already seeded.

# The prompt asks for actual DB evidence, which means we should use a real DB session.
client = TestClient(app)

print('Test client initialized.')
