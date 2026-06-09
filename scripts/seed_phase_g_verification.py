import os
import sys
from datetime import datetime, timezone
import uuid
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../telite-backend/.env'))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../telite-backend')))

from app.db.engine import get_db_session
from app.core.password_utils import hash_password
from app.models.organization import Organization
from app.models.user import User
from app.models.membership import Membership
from app.models.category import Category
from app.models.course import Course
from app.models.course_section import CourseSection
from app.models.course_module import CourseModule
from app.models.lesson_block import LessonBlock
from app.models.quiz_attempt import QuizAttempt
from app.models.certificate import Certificate
from app.models.learner_event import LearnerEvent
from app.models.course_progress import CourseProgress
from app.models.module_progress import ModuleProgress
from app.models.learning_path import LearningPath

def seed_db():
    with get_db_session() as session:
        for model in [Certificate, QuizAttempt, ModuleProgress, CourseProgress, LearnerEvent, LessonBlock, CourseModule, CourseSection, LearningPath, Course, Category, Membership, User, Organization]:
            session.query(model).delete()

        tenant_a = Organization(name="Tenant A", domain="tenant-a.com", type="company", status="active")
        tenant_b = Organization(name="Tenant B", domain="tenant-b.com", type="company", status="active")
        session.add_all([tenant_a, tenant_b])
        session.flush()

        pw_hash = hash_password("password")
        
        for tenant in [tenant_a, tenant_b]:
            t_name = tenant.name.replace(" ", "").lower()
            
            sa = User(id=f"sa_{t_name}", username=f"sa_{t_name}", email=f"superadmin@{t_name}.com", full_name=f"SA {tenant.name}", role="super_admin", password_hash=pw_hash, org_id=tenant.id, avatar_initials="SA", gradient_start="#000", gradient_end="#fff", is_active=True, status="active")
            ca = User(id=f"ca_{t_name}", username=f"ca_{t_name}", email=f"categoryadmin@{t_name}.com", full_name=f"CA {tenant.name}", role="category_admin", password_hash=pw_hash, org_id=tenant.id, avatar_initials="CA", gradient_start="#000", gradient_end="#fff", is_active=True, status="active")
            lr = User(id=f"lr_{t_name}", username=f"lr_{t_name}", email=f"learner@{t_name}.com", full_name=f"Learner {tenant.name}", role="learner", password_hash=pw_hash, org_id=tenant.id, avatar_initials="LR", gradient_start="#000", gradient_end="#fff", is_active=True, status="active")
            session.add_all([sa, ca, lr])
            session.flush()

            mem_sa = Membership(user_id=sa.id, org_id=tenant.id, role="super_admin")
            mem_ca = Membership(user_id=ca.id, org_id=tenant.id, role="category_admin")
            mem_lr = Membership(user_id=lr.id, org_id=tenant.id, role="learner")
            session.add_all([mem_sa, mem_ca, mem_lr])

            cat = Category(id=f"cat_{t_name}", name="Default Category", slug=f"default-{t_name}", org_id=tenant.id)
            session.add(cat)
            session.flush()

            course_a = Course(id=f"course_a_{t_name}", org_id=tenant.id, name="Course A", slug=f"course-a-{t_name}", category_slug=cat.slug, description="A", status="published")
            course_b = Course(id=f"course_b_{t_name}", org_id=tenant.id, name="Course B", slug=f"course-b-{t_name}", category_slug=cat.slug, description="B", status="published")
            session.add_all([course_a, course_b])
            session.flush()

            section = CourseSection(course_id=course_a.id, org_id=tenant.id, title="Section 1", sort_order=0)
            session.add(section)
            session.flush()
            
            mod_video = CourseModule(course_id=course_a.id, org_id=tenant.id, section_id=section.id, title="Video Mod", module_type="video", sort_order=0)
            mod_pdf = CourseModule(course_id=course_a.id, org_id=tenant.id, section_id=section.id, title="PDF Mod", module_type="document", sort_order=1)
            mod_quiz = CourseModule(course_id=course_a.id, org_id=tenant.id, section_id=section.id, title="Quiz Mod", module_type="quiz", sort_order=2)
            mod_text = CourseModule(course_id=course_a.id, org_id=tenant.id, section_id=section.id, title="Text Mod", module_type="interactive", sort_order=3)
            session.add_all([mod_video, mod_pdf, mod_quiz, mod_text])
            session.flush()

            path_a = LearningPath(org_id=tenant.id, title="Path A")
            session.add(path_a)
            session.flush()

            from app.models.quiz_models import QuizDefinition
            quiz_def = QuizDefinition(org_id=tenant.id, module_id=mod_quiz.id, title="Quiz Mod", passing_score=50)
            session.add(quiz_def)
            session.flush()

            qa_pass = QuizAttempt(quiz_id=quiz_def.id, org_id=tenant.id, user_id=lr.id, total_score=100.0, passed=True, status="completed", started_at=datetime.now(timezone.utc), submitted_at=datetime.now(timezone.utc))
            qa_fail = QuizAttempt(quiz_id=quiz_def.id, org_id=tenant.id, user_id=lr.id, total_score=40.0, passed=False, status="completed", started_at=datetime.now(timezone.utc), submitted_at=datetime.now(timezone.utc))
            session.add_all([qa_pass, qa_fail])

            c_prog = CourseProgress(org_id=tenant.id, user_id=lr.id, course_id=course_a.id, completion_percentage=100.0, status="completed", time_spent_seconds=3600)
            m_prog = ModuleProgress(org_id=tenant.id, user_id=lr.id, module_id=mod_video.id, status="completed", time_spent_seconds=600)
            session.add_all([c_prog, m_prog])

            cert = Certificate(id=f"cert_{t_name}", user_id=lr.id, course_id=course_a.id, org_id=tenant.id, issued_at=datetime.now(timezone.utc), pdf_s3_key=f"certs/{t_name}_cert.pdf", certificate_hash=f"hash_{t_name}", verification_token=f"tok_{t_name}")
            session.add(cert)

            events = ["MODULE_STARTED", "MODULE_VIEWED", "BLOCK_VIEWED", "VIDEO_STARTED", "VIDEO_PAUSED", "VIDEO_COMPLETED", "QUIZ_STARTED", "QUIZ_SUBMITTED", "MODULE_COMPLETED", "COURSE_COMPLETED", "COURSE_UNLOCKED"]
            for evt in events:
                session.add(LearnerEvent(user_id=lr.id, org_id=tenant.id, event_type=evt, course_id=course_a.id, module_id=mod_video.id))

        session.commit()
        print("Seed data injected successfully!")

if __name__ == "__main__":
    seed_db()
