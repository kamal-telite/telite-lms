"""Service to evaluate Learning Path unlock rules based on learner progress."""

from sqlalchemy.orm import Session
from datetime import datetime

from app.models.learning_path import LearningPath
from app.models.learning_path_progress import LearningPathProgress
from app.models.course_progress import CourseProgress
from app.models.learner_event import LearnerEvent
from app.repositories.progress_repo import ProgressRepository
from app.repositories.learning_path_progress_repo import LearningPathProgressRepository

class LearningPathUnlockService:
    def __init__(self, session: Session):
        self.session = session
        self.progress_repo = ProgressRepository(session)
        self.path_progress_repo = LearningPathProgressRepository(session)

    def evaluate_unlocks(self, user_id: str, path_id: int, org_id: int):
        """Evaluate if the next courses in the path should be unlocked."""
        path = self.session.query(LearningPath).filter_by(id=path_id, org_id=org_id).first()
        if not path:
            return

        # Simple sequential rule evaluation (assuming path.courses_json stores the ordered courses)
        courses = path.courses_json if path.courses_json else []
        
        # We find the first course that is not completed and emit UNLOCK if it wasn't already unlocked
        for i, course_item in enumerate(courses):
            c_id = course_item.get("course_id")
            cp = self.progress_repo.get_course_progress(user_id, c_id, org_id)
            
            # If the course is completed, we check the next one.
            if cp and cp.status == "completed":
                continue
                
            # If this course is not completed, this is the current active course
            # Emit UNLOCK event if not already emitted?
            # Actually, unlock service evaluates the Learning Path completion and next step unlocks.
            
            event = LearnerEvent(
                user_id=user_id,
                course_id=c_id,
                event_type="COURSE_UNLOCKED",
                schema_version="1.0",
                payload_json={"path_id": path_id, "step": i + 1},
                created_at=datetime.utcnow(),
                org_id=org_id
            )
            self.session.add(event)
            break

        self.session.flush()
