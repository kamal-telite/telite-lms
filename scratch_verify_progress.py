import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "telite-backend")))

from app.db.engine import get_tenant_session
from app.models.user import User
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.notification import Notification
from app.api.auth import TokenData
from app.api.routes.learner.progress import update_progress
from app.api.routes.learner.schemas import ProgressMutationRequest, ModuleProgressUpdate
from app.models.course_progress import CourseProgress
from app.models.module_progress import ModuleProgress
import asyncio
from datetime import datetime
from fastapi import BackgroundTasks

def run_verification():
    org_id = 1
    
    with get_tenant_session(org_id) as db:
        learner = db.query(User).filter(User.role == "learner").first()
        
        learner_token = TokenData(
            id=learner.id,
            email=learner.email,
            full_name=learner.full_name or "Test Learner",
            role=learner.role,
            org_id=org_id,
            category_scope=None
        )
        
        # Get a course and module
        course = db.query(Course).first()
        module = db.query(CourseModule).filter(CourseModule.course_id == course.id).first()
        
        if not module:
            print("No module found for course. Cannot test.")
            return

        print(f"Testing with Course: {course.id}, Module: {module.id}")
        
        # We need to enroll the learner first
        progress = db.query(CourseProgress).filter(CourseProgress.user_id == learner.id, CourseProgress.course_id == course.id).first()
        if not progress:
            progress = CourseProgress(user_id=learner.id, course_id=course.id, org_id=org_id, status="in_progress")
            db.add(progress)
        
        # Set module status to not complete
        mod_prog = db.query(ModuleProgress).filter(ModuleProgress.user_id == learner.id, ModuleProgress.module_id == module.id).first()
        if mod_prog:
            mod_prog.status = "in_progress"
            mod_prog.completed_at = None
        
        db.commit()

        # Build request to mark module as completed
        req = ProgressMutationRequest(
            course_id=course.id,
            module_updates=[ModuleProgressUpdate(module_id=module.id, status="completed", last_block_id=None)]
        )
        
        print("1. Updating progress...")
        try:
            update_progress(req, BackgroundTasks(), db, learner_token)
            db.commit()
            print("Progress updated successfully.")
        except Exception as e:
            print(f"Update failed: {e}")
            return
            
        module_notif = db.query(Notification).filter(
            Notification.user_id == learner.id,
            Notification.type == "info",
            Notification.title == "Module Completed",
            Notification.source_id == str(module.id)
        ).first()
        print(f"Module Completed Notif: {'FOUND' if module_notif else 'MISSING'}")
        
        course_notif = db.query(Notification).filter(
            Notification.user_id == learner.id,
            Notification.type == "info",
            Notification.title == "Course Completed",
            Notification.source_id == str(course.id)
        ).first()
        print(f"Course Completed Notif: {'FOUND' if course_notif else 'MISSING'}")

if __name__ == "__main__":
    run_verification()
