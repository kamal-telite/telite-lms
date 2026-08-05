"""Service to evaluate Learning Path unlock rules based on learner progress."""

from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.learning_path import LearningPath
from app.models.learning_path import LearningPathCourse
from app.models.learning_path_progress import LearningPathProgress
from app.models.learner_event import LearnerEvent
from app.models.notification import NotificationType
from app.repositories.notification_repo import NotificationRepository
from app.repositories.learning_path_progress_repo import LearningPathProgressRepository
from app.services.completion_policy_service import CompletionPolicyService
from app.core.notification_payloads import (
    learning_path_completed_idempotency_key,
    learning_path_completed_metadata,
    learning_path_unlocked_idempotency_key,
    learning_path_unlocked_metadata,
)

class LearningPathUnlockService:
    def __init__(self, session: Session):
        self.session = session
        self.path_progress_repo = LearningPathProgressRepository(session)
        self.notification_repo = NotificationRepository(session)
        self.completion_policy = CompletionPolicyService(session)

    def _path_courses(self, path_id: int, org_id: int) -> list[LearningPathCourse]:
        return (
            self.session.query(LearningPathCourse)
            .filter(
                LearningPathCourse.path_id == path_id,
                LearningPathCourse.org_id == org_id,
            )
            .order_by(LearningPathCourse.sort_order)
            .all()
        )

    def _has_unlock_event(self, user_id: str, path_id: int, course_id: str, org_id: int) -> bool:
        events = (
            self.session.query(LearnerEvent)
            .filter(
                LearnerEvent.user_id == user_id,
                LearnerEvent.org_id == org_id,
                LearnerEvent.course_id == course_id,
                LearnerEvent.event_type == "COURSE_UNLOCKED",
            )
            .all()
        )
        return any((event.payload_json or {}).get("path_id") == path_id for event in events)

    def evaluate_completion(self, user_id: str, path_id: int, org_id: int) -> tuple[LearningPathProgress | None, bool]:
        """Transition assigned path progress to completed once all path courses are completed."""
        progress = self.path_progress_repo.get_progress(user_id, path_id, org_id)
        if not progress:
            return None, False

        path_courses = self._path_courses(path_id, org_id)
        if not path_courses:
            return progress, False

        completed = 0
        for path_course in path_courses:
            completion = self.completion_policy.is_course_completed(
                user_id=user_id,
                course_id=path_course.course_id,
                org_id=org_id,
            )
            if completion.completed:
                completed += 1

        progress.completion_percentage = completed / len(path_courses) * 100.0
        if completed == len(path_courses):
            completed_now = self.path_progress_repo.mark_completed(progress)
            if completed_now:
                from app.services.notification_service import NotificationService
                NotificationService(self.session).emit_event(
                    "learning_path.completed",
                    org_id,
                    {"path_id": path_id},
                    user_id
                )
            return progress, completed_now

        if completed > 0:
            self.path_progress_repo.mark_in_progress(progress)
        self.session.flush()
        return progress, False

    def evaluate_unlocks(self, user_id: str, path_id: int, org_id: int):
        """Evaluate the next course unlocked by an assigned learner's path sequence."""
        path = self.session.query(LearningPath).filter_by(id=path_id, org_id=org_id).first()
        progress = self.path_progress_repo.get_progress(user_id, path_id, org_id)
        if not path or path.deleted_at or not progress:
            return None

        courses = self._path_courses(path_id, org_id)
        if not courses:
            return None
        
        # We find the first course that is not completed and emit UNLOCK if it wasn't already unlocked
        for i, course_item in enumerate(courses):
            c_id = course_item.course_id
            completion = self.completion_policy.is_course_completed(
                user_id=user_id,
                course_id=c_id,
                org_id=org_id,
            )
            
            # If the course is completed, we check the next one.
            if completion.completed:
                continue
                
            # This is the first incomplete course in the ordered path sequence.
            self.path_progress_repo.mark_in_progress(progress)

            if self._has_unlock_event(user_id, path_id, c_id, org_id):
                self.evaluate_completion(user_id, path_id, org_id)
                return None

            event = LearnerEvent(
                user_id=user_id,
                course_id=c_id,
                event_type="COURSE_UNLOCKED",
                schema_version="1.0",
                payload_json={"path_id": path_id, "course_id": c_id, "step": i + 1},
                created_at=datetime.now(timezone.utc),
                org_id=org_id
            )
            self.session.add(event)
            from app.services.notification_service import NotificationService
            NotificationService(self.session).emit_event(
                "learning_path.course_unlocked",
                org_id,
                {"path_id": path_id, "course_id": c_id},
                user_id
            )
            self.evaluate_completion(user_id, path_id, org_id)
            self.session.flush()
            return event

        self.evaluate_completion(user_id, path_id, org_id)
        self.session.flush()
        return None
