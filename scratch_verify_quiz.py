import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "telite-backend")))

from app.db.engine import get_tenant_session
from app.models.user import User
from app.models.quiz_models import QuizDefinition
from app.models.quiz_attempt import QuizAttempt
from app.models.notification import Notification
from app.api.auth import TokenData
from app.api.routes.quiz_execution import start_attempt, submit_attempt
from app.api.routes.quiz_grading import apply_manual_grade, ManualGradeRequest
from fastapi import HTTPException
import asyncio

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
        
        # 1. Create a dummy quiz
        quiz = QuizDefinition(
            org_id=org_id,
            title="Test Quiz",
            settings_json={"passing_score": 50, "questions": [{"points": 10}]}
        )
        db.add(quiz)
        db.commit()
        
        quiz_id = quiz.id
        print(f"Created quiz: {quiz_id}")
        
        # Start Attempt
        print("1. Starting quiz attempt...")
        try:
            result = start_attempt(quiz_id, db, learner_token)
            attempt_id = result["attempt_id"]
            print(f"Started Attempt: {attempt_id}")
        except Exception as e:
            print(f"Start attempt failed: {e}")
            return

        # Submit Attempt
        print("2. Submitting quiz attempt...")
        try:
            submit_result = submit_attempt(attempt_id, db, learner_token)
            print(f"Submitted: {submit_result}")
        except Exception as e:
            print(f"Submit failed: {e}")
            return
            
        submit_notif = db.query(Notification).filter(
            Notification.user_id == learner.id,
            Notification.source_id == str(attempt_id),
            Notification.type == "info",
            Notification.title == "Quiz Submitted"
        ).first()
        print(f"Submit Learner Notif: {'FOUND' if submit_notif else 'MISSING'}")
        
        # If the quiz was not auto-graded (because there are no actual answers/questions matched),
        # the status will be needs_manual_grading. Let's manually grade it.
        attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()
        print(f"Attempt Status: {attempt.status}")
        
        if attempt.status == "needs_manual_grading":
            print("3. Manual Grading...")
            # We need a quiz answer for this attempt to manually grade it.
            from app.models.quiz_answer import QuizAnswer
            answer = QuizAnswer(attempt_id=attempt.id, question_version_id=1, response_json={})
            db.add(answer)
            db.commit()
            
            try:
                apply_manual_grade(attempt_id, answer.id, ManualGradeRequest(new_score=10), db, admin_token)
            except Exception as e:
                print(f"Manual grade failed: {e}")
                
        grade_notif = db.query(Notification).filter(
            Notification.user_id == learner.id,
            Notification.source_id == str(attempt_id),
            Notification.type == "info",
            Notification.title == "Quiz Graded"
        ).first()
        print(f"Grade Learner Notif: {'FOUND' if grade_notif else 'MISSING'}")

if __name__ == "__main__":
    run_verification()
