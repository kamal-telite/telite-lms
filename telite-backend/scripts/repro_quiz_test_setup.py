import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.engine import dispose_engine, get_session_factory
from app.models.organization import Organization
from app.repositories.user_repo import UserRepository

os.environ['TELITE_DB_BACKEND'] = 'sqlite'
db_path = r'c:/Users/lt22c/AppData/Local/Temp/test_quiz_engine_repro2.db'
os.environ['TELITE_DB_PATH'] = db_path
os.environ['TELITE_DATABASE_URL'] = f'sqlite:///{db_path}'
os.environ['MOODLE_MODE'] = 'mock'
os.environ['TELITE_SEED_ADMIN_PASSWORD'] = 'TeliteQuiz12345678'
os.environ['TELITE_SEED_LEARNER_PASSWORD'] = 'TeliteQuiz12345678'
os.environ['REDIS_ENABLED'] = 'false'

session_factory = get_session_factory()
print('before dispose engine from', session_factory.kw['bind'].url)
dispose_engine()
main = importlib.import_module('main')
importlib.reload(main)
from app.core import rate_limiter
SessionFactory = get_session_factory()
rate_limiter.clear_all_attempts()
client = TestClient(main.create_app())
client.__enter__()

db = SessionFactory()
db.execute(text('PRAGMA foreign_keys=OFF'))
db.commit()
print('tables before query', db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='organizations'")).fetchone())
org = db.query(Organization).filter_by(id=1).first()
print('org', org)

db.close()
client.__exit__(None, None, None)
