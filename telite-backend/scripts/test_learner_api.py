from app.db.engine import db_session
from app.api.routes.learner import get_learner_course
from app.api.auth import TokenData
from app.models.user import User
import json

db = next(db_session())
# find a learner user
from sqlalchemy import text
db.execute(text("SET app.bypass_rls = 'on'"))
user = db.query(User).filter(User.email == 'learner1@ktlearn.local').first()
current_user = TokenData(id=user.id, email=user.email, org_id=user.org_id, role=user.role, full_name=user.full_name)

try:
    res = get_learner_course("course-python", db=db, current_user=current_user)
    print(json.dumps(res, indent=2))
except Exception as e:
    import traceback
    traceback.print_exc()
