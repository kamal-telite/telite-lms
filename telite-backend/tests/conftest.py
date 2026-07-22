import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.db.engine import dispose_engine
from app.models.base import Base
import app.models  # ensure all models are registered

TEST_DATABASE_URL = os.getenv(
    "TELITE_TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres123@127.0.0.1:55432/test_telite_backend",
).replace("postgresql+psycopg2://", "postgresql+psycopg://", 1).replace("postgresql://", "postgresql+psycopg://", 1).replace("postgres://", "postgresql+psycopg://", 1)


@pytest.fixture(scope="function")
def client(engine):
    os.environ["TELITE_DATABASE_URL"] = TEST_DATABASE_URL
    dispose_engine()
    with TestClient(create_app()) as test_client:
        yield test_client
    dispose_engine()


@pytest.fixture(scope="session")
def engine():
    os.environ["TELITE_DATABASE_URL"] = TEST_DATABASE_URL
    engine = create_engine(TEST_DATABASE_URL)
    
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
    yield engine
    
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(engine):
    # Re-create tables cleanly for each test using drop_all to avoid dialect cache bugs
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
