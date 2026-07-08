import os
import sqlite3
from app.core.runtime import get_environment, is_development, is_production_like
from app.db.init_db import _use_alembic_migrations, _allow_legacy_schema_bootstrap, run_phase3_init
from app.db.engine import dispose_engine

print('ENV', get_environment())
print('dev', is_development())
print('prod_like', is_production_like())
print('use_alembic', _use_alembic_migrations())
print('allow_legacy', _allow_legacy_schema_bootstrap())
dispose_engine()
run_phase3_init()
conn = sqlite3.connect(r'c:/Users/lt22c/AppData/Local/Temp/test_quiz_engine.db')
print(conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall())
conn.close()
