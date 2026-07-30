from app.db.engine import db_session
from app.api.routes.learner.courses import get_learner_course
from app.api.routes.learner.progress import update_progress, heartbeat, heartbeat_learning_session
from app.api.auth import TokenData
from app.models.user import User
from app.models.course_progress import CourseProgress
from app.models.section_progress import SectionProgress
from app.models.module_progress import ModuleProgress
from app.models.course_section import CourseSection
from app.models.course_module import CourseModule
from app.models.learning_session import LearningSession
import json

db = next(db_session())
# find a learner user
from sqlalchemy import text
db.execute(text("SET app.bypass_rls = 'on'"))

# Find a user with actual progress data
user_with_progress = db.query(User).join(CourseProgress).filter(User.org_id == 1).first()
if not user_with_progress:
    # Fall back to any learner
    user_with_progress = db.query(User).filter(User.role == 'learner', User.org_id == 1).first()
if not user_with_progress:
    print("No learner user found")
    exit(1)

print(f"Using user: {user_with_progress.email}, id: {user_with_progress.id}, org: {user_with_progress.org_id}")

# Check what courses this user has progress for
progress_records = db.query(CourseProgress).filter(CourseProgress.user_id == user_with_progress.id).all()
print(f"\nUser has progress for {len(progress_records)} courses:")
for cp in progress_records:
    print(f"  - {cp.course_id}: status={cp.status}, completion={cp.completion_percentage}%")

if not progress_records:
    print("No progress records found, cannot test")
    db.close()
    exit(1)

course_id = progress_records[0].course_id
print(f"\nTesting with course: {course_id}")

current_user = TokenData(id=user_with_progress.id, email=user_with_progress.email, org_id=user_with_progress.org_id, role=user_with_progress.role, full_name=user_with_progress.full_name)

# Test 1: GET learner course
print("\n=== Test 1: GET /learner/courses/{id} ===")
try:
    res = get_learner_course(course_id, db=db, current_user=current_user)
    print(f"SUCCESS: Got course with {len(res.get('sections', []))} sections")
except Exception as e:
    import traceback
    print(f"FAILED: {e}")
    traceback.print_exc()

# Test 2: Check section progress
print("\n=== Test 2: Check section progress ===")
sections = db.query(CourseSection).filter(CourseSection.course_id == course_id, CourseSection.org_id == user_with_progress.org_id).all()
print(f"Course has {len(sections)} sections")
for section in sections:
    sp = db.query(SectionProgress).filter(
        SectionProgress.user_id == user_with_progress.id,
        SectionProgress.section_id == section.id
    ).first()
    print(f"  Section {section.id} ({section.title}): progress={sp.status if sp else 'None'}, time_spent={sp.time_spent_seconds if sp else 0}s, min_time={section.minimum_time_seconds}s")

# Test 3: Check module progress
print("\n=== Test 3: Check module progress ===")
modules = db.query(CourseModule).filter(CourseModule.course_id == course_id, CourseModule.org_id == user_with_progress.org_id).all()
print(f"Course has {len(modules)} modules")
for module in modules[:5]:  # Show first 5
    mp = db.query(ModuleProgress).filter(
        ModuleProgress.user_id == user_with_progress.id,
        ModuleProgress.module_id == module.id
    ).first()
    print(f"  Module {module.id} ({module.title}): progress={mp.status if mp else 'None'}")

# Test 4: Check learning sessions
print("\n=== Test 4: Check learning sessions ===")
sessions = db.query(LearningSession).filter(
    LearningSession.user_id == user_with_progress.id,
    LearningSession.course_id == course_id
    ).all()
print(f"User has {len(sessions)} learning sessions")
for session in sessions[-3:]:  # Show last 3
    print(f"  Session {session.id}: status={session.status}, active_seconds={session.active_seconds}")

# Test 5: Check progression rules
print("\n=== Test 5: Check progression rules ===")
from app.models.progression_rule import ProgressionRule
rules = db.query(ProgressionRule).filter(ProgressionRule.org_id == user_with_progress.org_id).all()
print(f"Org has {len(rules)} progression rules")
for rule in rules:
    print(f"  Rule {rule.id}: type={rule.rule_type}, target={rule.target_type}:{rule.target_id}, active={rule.is_active}")

db.close()
