import sys
import os
sys.path.append('.')

from alembic.config import Config
from alembic import command
from app.db.init_db import (
    create_all_tables,
    apply_rls_if_postgres,
    ensure_default_organization,
    backfill_course_modules_from_courses,
    verify_connection
)

def main():
    print("Creating all ORM-mapped tables...")
    create_all_tables()
    
    print("Stamping database schema to Alembic head...")
    alembic_cfg = Config("alembic.ini")
    command.stamp(alembic_cfg, "head")
    
    print("Applying PostgreSQL Row-Level Security (RLS) policies...")
    apply_rls_if_postgres()
    
    print("Ensuring default organization (id=1)...")
    ensure_default_organization()
    
    print("Backfilling course modules from modules_json...")
    backfill_course_modules_from_courses()
    
    if verify_connection():
        print("Database initialisation complete and healthy.")
    else:
        print("Database connectivity check FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
