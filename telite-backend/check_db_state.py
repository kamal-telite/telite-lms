from app.db.engine import get_db_session
from app.models.course_section import CourseSection
from app.models.section_progress import SectionProgress
from app.models.course_progress import CourseProgress

with get_db_session() as db:
    # Check sections
    sections = db.query(CourseSection).limit(5).all()
    print("SECTIONS:")
    for s in sections:
        print(f"  ID: {s.id}, Title: {s.title}, minimum_time_seconds: {s.minimum_time_seconds}")
    
    # Check section progress
    section_progress = db.query(SectionProgress).limit(5).all()
    print("\nSECTION PROGRESS:")
    for sp in section_progress:
        print(f"  User: {sp.user_id}, Section: {sp.section_id}, Status: {sp.status}, Time: {sp.time_spent_seconds}s")
    
    # Check course progress
    course_progress = db.query(CourseProgress).limit(5).all()
    print("\nCOURSE PROGRESS:")
    for cp in course_progress:
        print(f"  User: {cp.user_id}, Course: {cp.course_id}, Status: {cp.status}, Time: {cp.time_spent_seconds}s")
