import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "telite-backend")))

from app.db.engine import get_tenant_session
from app.models.user import User
from app.models.category import Category
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.lesson_block import LessonBlock
from app.models.notification import Notification
from app.api.auth import TokenData
from app.api.routes.assignments import submit_assignment, grade_submission, approve_submission, reject_submission
from app.api.routes.assignments import GradeRequest, ReviewRequest
import time
import asyncio
from fastapi import Request

class FakeRequest:
    def __init__(self, text="Test submission"):
        self._text = text
        self.headers = {"content-type": "multipart/form-data"}
    async def form(self):
        class Form:
            def __init__(self, outer):
                self.outer = outer
            def get(self, key):
                if key == "submission_text": return self.outer._text
                return None
            def getlist(self, key):
                return []
            def values(self):
                return []
        return Form(self)

def run_verification():
    org_id = 1
    
    with get_tenant_session(org_id) as db:
        admin = db.query(User).filter(User.role == "super_admin").first()
        learner = db.query(User).filter(User.role == "learner").first()
        
        learner_token = TokenData(
            id=learner.id,
            email=learner.email,
            full_name=learner.full_name or "Test Learner",
            role=learner.role,
            org_id=org_id,
            category_scope=None
        )
        
        admin_token = TokenData(
            id=admin.id,
            email=admin.email,
            full_name=admin.full_name or "Test Admin",
            role=admin.role,
            org_id=org_id,
            category_scope=admin.category_scope
        )
        
        # 1. Create a dummy block
        # We need a course, module, block
        course = db.query(Course).first()
        module = db.query(CourseModule).filter(CourseModule.course_id == course.id).first()
        if not module:
            module = CourseModule(course_id=course.id, title="Test Module", slug="test-mod", sort_order=1)
            db.add(module)
            db.commit()
            
        block = LessonBlock(
            module_id=module.id, 
            org_id=org_id,
            block_type="assignment", 
            content="Test Assignment Block",
            sort_order=1
        )
        db.add(block)
        db.commit()
        
        block_id = block.id
        print(f"Created assignment block: {block_id}")
        
        # Add enrollment for learner
        from app.models.course_progress import CourseProgress
        progress = db.query(CourseProgress).filter(CourseProgress.user_id == learner.id, CourseProgress.course_id == course.id).first()
        if not progress:
            progress = CourseProgress(user_id=learner.id, course_id=course.id, org_id=org_id, status="in_progress")
            db.add(progress)
            db.commit()

        # Submit
        print("1. Submitting assignment...")
        req = FakeRequest("My submission text")
        try:
            result = asyncio.run(submit_assignment(block_id, req, db, learner_token))
            submission_id = result["submission"]["id"]
            print(f"Submitted: {submission_id}")
        except Exception as e:
            print(f"Submit failed: {e}")
            return
            
        submit_notif = db.query(Notification).filter(
            Notification.user_id == learner.id,
            Notification.source_id == str(submission_id),
            Notification.type == "assignment_submitted"
        ).first()
        print(f"Submit Learner Notif: {'FOUND' if submit_notif else 'MISSING'}")
        
        # Grade
        print("2. Grading assignment...")
        grade_req = GradeRequest(grade=85.0, feedback="Good job", returned=False)
        try:
            grade_submission(submission_id, grade_req, db, admin_token)
        except Exception as e:
            print(f"Grade failed: {e}")
            
        grade_notif = db.query(Notification).filter(
            Notification.user_id == learner.id,
            Notification.source_id == str(submission_id),
            Notification.type == "assignment_graded"
        ).first()
        print(f"Grade Learner Notif: {'FOUND' if grade_notif else 'MISSING'}")
        
        # Approve
        print("3. Approving assignment...")
        print("3a. Submitting another assignment for approval...")
        from app.api.routes.assignments import resubmit_assignment
        try:
            result2 = asyncio.run(resubmit_assignment(block_id, req, db, learner_token))
            submission_id2 = result2["submission"]["id"]
        except Exception as e:
            print(f"Submit 2 failed: {e}")
            return

        approve_req = ReviewRequest(feedback="Approved!")
        try:
            approve_submission(submission_id2, approve_req, db, admin_token)
        except Exception as e:
            print(f"Approve failed: {e}")
            
        approve_notif = db.query(Notification).filter(
            Notification.user_id == learner.id,
            Notification.source_id == str(submission_id2),
            Notification.title == "Assignment Approved"
        ).first()
        print(f"Approve Learner Notif: {'FOUND' if approve_notif else 'MISSING'}")
        
if __name__ == "__main__":
    run_verification()
