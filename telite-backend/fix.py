from dotenv import load_dotenv
load_dotenv()
from app.db.engine import get_engine
from sqlalchemy import text

engine = get_engine()
with engine.begin() as conn:
    conn.execute(text("UPDATE courses SET category_slug='tenanta' WHERE id='course_a_tenanta'"))
    conn.execute(text("UPDATE courses SET category_slug='tenanta' WHERE id='course_b_tenanta'"))
print("Done")
