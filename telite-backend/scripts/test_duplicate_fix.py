"""Test the MultipleResultsFound fix."""
import sys
sys.path.insert(0, 'c:\\Users\\lt22c\\OneDrive\\Desktop\\telite-lms\\telite-backend')

from app.db.engine import db_session
from app.api.routes.learner.utils import apply_active_seconds
from app.api.auth import TokenData
from app.models.user import User
from app.models.course_progress import CourseProgress
from sqlalchemy import text

db = next(db_session())
db.execute(text("SET app.bypass_rls = 'on'"))

# Find a learner user
user = db.query(User).filter(User.role == 'learner', User.org_id == 1).first()
if not user:
    print("No learner user found")
    db.close()
    exit(1)

print(f"Using user: {user.email}, id: {user.id}, org: {user.org_id}")

course_id = "course-bb7661285b"
current_user = TokenData(
    id=user.id,
    email=user.email,
    org_id=user.org_id,
    role=user.role,
    full_name=user.full_name
)

# Check for duplicate course progress records
print("\n=== Checking for duplicate CourseProgress records ===")
cp_records = db.query(CourseProgress).filter(
    CourseProgress.user_id == user.id,
    CourseProgress.course_id == course_id,
    CourseProgress.org_id == user.org_id
).all()

print(f"Found {len(cp_records)} CourseProgress records")
for i, cp in enumerate(cp_records):
    print(f"  Record {i+1}: id={cp.id}, created_at={cp.created_at}, status={cp.status}, time_spent={cp.time_spent_seconds}")

# Test apply_active_seconds (heartbeat logic)
print("\n=== Testing apply_active_seconds (heartbeat) ===")
try:
    apply_active_seconds(
        db,
        current_user=current_user,
        course_id=course_id,
        module_id=25,
        block_id=None,
        active_seconds=30
    )
    db.commit()
    print("✓ apply_active_seconds succeeded")
except Exception as e:
    print(f"✗ apply_active_seconds failed: {e}")
    import traceback
    traceback.print_exc()

# Test get_course_progress
print("\n=== Testing get_course_progress ===")
from app.repositories.progress_repo import ProgressRepository
progress_repo = ProgressRepository(db)
try:
    cp = progress_repo.get_course_progress(user.id, course_id, user.org_id)
    print(f"✓ get_course_progress succeeded: status={cp.status if cp else 'None'}")
except Exception as e:
    print(f"✗ get_course_progress failed: {e}")
    import traceback
    traceback.print_exc()

db.close()
print("\n=== Test complete ===")
