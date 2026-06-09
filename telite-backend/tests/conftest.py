import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base

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
