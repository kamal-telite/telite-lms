import subprocess
import sys
import os

def test_schema_synchronization():
    """
    Runs the verify_schema_sync.py script to ensure no schema drift exists between
    the Alembic migrations (physical database) and the SQLAlchemy ORM models.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'verify_schema_sync.py')
    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
    assert result.returncode == 0, f"Schema drift detected!\n{result.stdout}\n{result.stderr}"
