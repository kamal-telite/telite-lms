"""Pytest configuration for Telite LMS backend."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("TELITE_DB_BACKEND", "sqlite")
os.environ.setdefault("TELITE_DB_PATH", "data/ci_test_telite_lms.db")
os.environ.setdefault("TELITE_AUTH_SECRET", "ci-test-auth-secret-not-for-production-use")
os.environ.setdefault("TELITE_PASSWORD_SALT", "ci-test-password-salt")
os.environ.setdefault("REDIS_ENABLED", "false")
os.environ.setdefault("TELITE_USE_ALEMBIC", "false")

from app.models.base import Base


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


@pytest.fixture(scope="session")
def engine():
    # Use manual local postgres instance on port 55432
    db_url = os.getenv(
        "TELITE_TEST_DATABASE_URL",
        "postgresql+psycopg://postgres@localhost:55432/test_telite_backend",
    )
    engine = create_engine(db_url)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Teardown
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(engine):
    """Create a new database session for a test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
