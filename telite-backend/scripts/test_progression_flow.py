"""Test the learner progression flow end-to-end."""
import sys
sys.path.insert(0, 'c:\\Users\\lt22c\\OneDrive\\Desktop\\telite-lms\\telite-backend')

from app.db.engine import db_session
from app.api.routes.learner.utils import apply_active_seconds
from app.api.auth import TokenData
from app.models.user import User
from app.models.course_progress import CourseProgress
from app.models.section_progress import SectionProgress
from app.models.module_progress import ModuleProgress
from app.models.course_section import CourseSection
from app.models.course_module import CourseModule
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

# Find a course with sections
course_id = "course-1967f74ec7"
sections = db.query(CourseSection).filter(
    CourseSection.course_id == course_id,
    CourseSection.org_id == user.org_id,
    CourseSection.deleted_at.is_(None)
).order_by(CourseSection.sort_order.asc()).all()

if not sections:
    print("No sections found in course")
    db.close()
    exit(1)

print(f"\nCourse has {len(sections)} sections")

# Get first section and its first module
first_section = sections[0]
first_module = db.query(CourseModule).filter(
    CourseModule.section_id == first_section.id,
    CourseModule.org_id == user.org_id,
    CourseModule.deleted_at.is_(None)
).first()

if not first_module:
    print("No modules found in first section")
    db.close()
    exit(1)

print(f"First section: {first_section.title} (id: {first_section.id}, min_time: {first_section.minimum_time_seconds}s)")
print(f"First module: {first_module.title} (id: {first_module.id})")

current_user = TokenData(
    id=user.id,
    email=user.email,
    org_id=user.org_id,
    role=user.role,
    full_name=user.full_name
)

# Simulate learner spending time in the section
print("\n=== Simulating learner spending 60 seconds in section ===")
apply_active_seconds(
    db,
    current_user=current_user,
    course_id=course_id,
    module_id=first_module.id,
    block_id=None,
    active_seconds=60
)
db.commit()

# Check section progress
sp = db.query(SectionProgress).filter(
    SectionProgress.user_id == user.id,
    SectionProgress.section_id == first_section.id
).first()

if sp:
    print(f"Section progress created:")
    print(f"  - status: {sp.status}")
    print(f"  - time_spent_seconds: {sp.time_spent_seconds}")
    print(f"  - completion_percentage: {sp.completion_percentage}")
else:
    print("ERROR: Section progress was NOT created!")

# Check module progress
mp = db.query(ModuleProgress).filter(
    ModuleProgress.user_id == user.id,
    ModuleProgress.module_id == first_module.id
).first()

if mp:
    print(f"\nModule progress created:")
    print(f"  - status: {mp.status}")
    print(f"  - time_spent_seconds: {mp.time_spent_seconds}")
else:
    print("ERROR: Module progress was NOT created!")

# Simulate completing the module
print("\n=== Simulating module completion ===")
from app.api.routes.learner.progress import update_progress
from app.api.routes.learner.schemas import ProgressMutationRequest

req = ProgressMutationRequest(
    course_id=course_id,
    module_updates=[{"module_id": first_module.id, "status": "completed"}]
)

try:
    update_progress(req, background_tasks=None, db=db, current_user=current_user)
    db.commit()
    print("Module marked as completed")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

# Check section progress after module completion
sp = db.query(SectionProgress).filter(
    SectionProgress.user_id == user.id,
    SectionProgress.section_id == first_section.id
).first()

if sp:
    print(f"\nSection progress after module completion:")
    print(f"  - status: {sp.status}")
    print(f"  - time_spent_seconds: {sp.time_spent_seconds}")
    print(f"  - completion_percentage: {sp.completion_percentage}")
    print(f"  - completed_at: {sp.completed_at}")

db.close()
print("\n=== Test complete ===")
