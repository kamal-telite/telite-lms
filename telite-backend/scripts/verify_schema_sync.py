import os
import sys
import subprocess
import ast
import glob
from sqlalchemy import create_engine, inspect, text
from app.models.base import Base
import app.models  # ensure all models are registered

def main():
    db_url = os.getenv(
        "TELITE_TEST_DATABASE_URL",
        "postgresql+psycopg://postgres:postgres123@localhost:55432/test_telite_schema_sync"
    )
    
    # 1. Ensure DB is fresh and upgraded to head
    print("Initializing fresh database for audit...")
    sys_engine = create_engine("postgresql+psycopg://postgres:postgres123@localhost:55432/postgres", isolation_level="AUTOCOMMIT")
    db_name = db_url.split("/")[-1]
    with sys_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {db_name} WITH (FORCE);"))
        conn.execute(text(f"CREATE DATABASE {db_name};"))
    
    env = os.environ.copy()
    env["TELITE_DATABASE_URL"] = db_url
    try:
        subprocess.run(["alembic", "upgrade", "head"], env=env, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to run alembic upgrade head: {e}")
        sys.exit(1)
        
    engine = create_engine(db_url)
    inspector = inspect(engine)
    
    physical_tables = set(inspector.get_table_names())
    physical_tables.discard('alembic_version')
    
    orm_tables = set(Base.metadata.tables.keys())
    
    orphaned_physical = physical_tables - orm_tables
    orphaned_orm = orm_tables - physical_tables
    
    # Distinguish True Orphans vs Registration Defects
    registration_defects = []
    true_orphans = []
    
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'app', 'models')
    all_tablenames_in_code = set()
    for py_file in glob.glob(os.path.join(models_dir, '*.py')):
        with open(py_file, 'r', encoding='utf-8') as f:
            try:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name) and target.id == '__tablename__':
                                        if isinstance(item.value, ast.Constant):
                                            all_tablenames_in_code.add(item.value.value)
            except Exception:
                pass

    for t in orphaned_physical:
        if t in all_tablenames_in_code:
            registration_defects.append(t)
        else:
            true_orphans.append(t)
            
    # Check Missing ORM Foreign Keys
    missing_orm_fks = []
    stale_physical_fks = []
    for t in physical_tables:
        fks = inspector.get_foreign_keys(t)
        for fk in fks:
            constrained_columns = tuple(fk['constrained_columns'])
            referred_table = fk['referred_table']
            referred_columns = tuple(fk['referred_columns'])
            
            # Check for stale foreign keys pointing to missing tables
            if referred_table not in physical_tables:
                stale_physical_fks.append(f"{t}.{constrained_columns} -> {referred_table}.{referred_columns} (Referred table is missing in physical DB)")
            elif referred_table not in orm_tables:
                stale_physical_fks.append(f"{t}.{constrained_columns} -> {referred_table}.{referred_columns} (Referred table is missing in ORM)")

            if t in orm_tables:
                orm_table = Base.metadata.tables[t]
                found = False
                for orm_fk in orm_table.foreign_keys:
                    # Match by constrained column name and referred table name
                    if orm_fk.parent.name in constrained_columns and orm_fk.column.table.name == referred_table:
                        found = True
                        break
                
                if not found:
                    missing_orm_fks.append(f"{t}.{constrained_columns} -> {referred_table}.{referred_columns}")
                    
    has_drift = False
    
    print("\n--- SCHEMA DRIFT AUDIT RESULTS ---\n")
    
    if true_orphans:
        print("[ERROR] True Orphans (Physical Tables missing in ORM and not defined in any model file):")
        for t in sorted(true_orphans):
            print(f"  - {t}")
        has_drift = True
        
    if registration_defects:
        print("\n[ERROR] Registration Defects (Models defined in code but missing from __init__.py registry):")
        for t in sorted(registration_defects):
            print(f"  - {t}")
        has_drift = True
        
    if orphaned_orm:
        print("\n[ERROR] Orphaned ORM Models (Exist in ORM, Missing in DB / Missing Migration):")
        for t in sorted(orphaned_orm):
            print(f"  - {t}")
        has_drift = True
        
    if missing_orm_fks:
        print("\n[ERROR] ORM Metadata Drift - Missing ORM Foreign Keys:")
        for fk in sorted(missing_orm_fks):
            print(f"  - {fk}")
        has_drift = True
        
    if stale_physical_fks:
        print("\n[ERROR] Stale Physical Foreign Keys:")
        for fk in sorted(stale_physical_fks):
            print(f"  - {fk}")
        has_drift = True
        
    if has_drift:
        print("\nSCHEMA DRIFT DETECTED! Please synchronize ORM and Alembic migrations.")
        sys.exit(1)
    else:
        print("Schema is perfectly synchronized! No drift detected.")
        sys.exit(0)

if __name__ == "__main__":
    main()
