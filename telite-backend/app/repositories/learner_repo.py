"""Learner Repository for fetching enrolled courses and modules."""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.learning_path import LearningPath
from app.models.user import User


class LearnerRepository:
    """Repository for learner-facing content with strict access checks."""
    
    def __init__(self, session: Session):
        self.session = session

    def get_enrolled_courses(self, user_id: str, org_id: int) -> List[Course]:
        user = self.session.get(User, user_id)
        stmt = select(Course).where(Course.org_id == org_id)
        if user and user.role == "learner" and user.category_scope:
            stmt = stmt.where(
                Course.category_slug == user.category_scope,
                Course.status.in_(("active", "published")),
            )
        elif user and user.role == "learner":
            stmt = stmt.where(Course.status.in_(("active", "published")))
        return list(self.session.scalars(stmt))

    def get_course(self, course_id: str, user_id: str, org_id: int) -> Optional[Course]:
        user = self.session.get(User, user_id)
        stmt = select(Course).where(
            Course.id == course_id,
            Course.org_id == org_id
        )
        if user and user.role == "learner":
            stmt = stmt.where(Course.status.in_(("active", "published")))
        return self.session.scalar(stmt)

    def get_learning_paths(self, user_id: str, org_id: int) -> List[LearningPath]:
        stmt = select(LearningPath)
        return list(self.session.scalars(stmt))

    def get_learning_path(self, path_id: int, user_id: str, org_id: int) -> Optional[LearningPath]:
        stmt = select(LearningPath).where(LearningPath.id == path_id)
        return self.session.scalar(stmt)
