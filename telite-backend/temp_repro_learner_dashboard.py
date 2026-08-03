import os
from pathlib import Path
from sqlalchemy import select
from app.db.engine import get_db_session
from app.models.user import User
from app.repositories.analytics import AnalyticsRepository

# Load env vars from .env for local reproduction
env_path = Path(__file__).resolve().parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ[key.strip()] = value.strip().strip('"').strip("'")

with get_db_session() as db:
    user = db.execute(
        select(User).where(User.role == 'learner').order_by(User.id).limit(1)
    ).scalars().first()
    print('TEST USER', user.id if user else None)
    if not user:
        raise SystemExit('No learner user found')
    try:
        result = AnalyticsRepository(db).get_learner_summary(user.id)
        print('SUCCESS', result)
    except Exception:
        import traceback
        traceback.print_exc()