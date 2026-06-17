import os
import sys
from sqlalchemy import create_engine, text
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv
load_dotenv()
DB_URL = os.getenv("TELITE_DATABASE_URL") or os.getenv("DATABASE_URL")
engine = create_engine(DB_URL)
with engine.connect() as conn:
    orgs = conn.execute(text("SELECT count(*) FROM organizations")).scalar()
    users = conn.execute(text("SELECT count(*) FROM users")).scalar()
    cats = conn.execute(text("SELECT count(*) FROM categories")).scalar()
    crs = conn.execute(text("SELECT count(*) FROM courses")).scalar()
    secs = conn.execute(text("SELECT count(*) FROM course_sections")).scalar()
    mods = conn.execute(text("SELECT count(*) FROM course_modules")).scalar()
    blks = conn.execute(text("SELECT count(*) FROM lesson_blocks")).scalar()
    enrs = conn.execute(text("SELECT count(*) FROM enrollment_requests")).scalar()
    print(f"Orgs: {orgs}, Users: {users}, Categories: {cats}, Courses: {crs}, Sections: {secs}, Modules: {mods}, Blocks: {blks}, Enrollments: {enrs}")
