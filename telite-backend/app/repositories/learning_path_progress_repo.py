"""Learning Path Progress Repository."""

from datetime import datetime, timezone
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.learning_path_progress import LearningPathProgress
from app.models.notification import NotificationType
from app.repositories.notification_repo import NotificationRepository
from app.core.notification_payloads import (
    learning_path_assigned_idempotency_key,
    learning_path_assigned_metadata,
)


class LearningPathProgressRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_progress(self, user_id: str, path_id: str, org_id: int) -> Optional[LearningPathProgress]:
        stmt = select(LearningPathProgress).where(
            LearningPathProgress.user_id == user_id,
            LearningPathProgress.path_id == path_id,
            LearningPathProgress.org_id == org_id
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def assign_path(self, user_id: str, path_id: int, org_id: int) -> tuple[LearningPathProgress, bool]:
        """Create the canonical learner/path assignment row if it does not exist."""
        existing = self.get_progress(user_id, path_id, org_id)
        if existing:
            return existing, False

        progress = LearningPathProgress(
            user_id=user_id,
            path_id=path_id,
            org_id=org_id,
            status="not_started",
            completion_percentage=0.0,
        )
        self.session.add(progress)
        self.session.flush()
        NotificationRepository(self.session).create_once(
            user_id=user_id,
            org_id=org_id,
            title="Learning Path Assigned",
            body="A new learning path has been assigned to you.",
            notif_type=NotificationType.LEARNING_PATH_ASSIGNED,
            source_type="learning_path",
            source_id=path_id,
            metadata=learning_path_assigned_metadata(path_id=path_id),
            idempotency_key=learning_path_assigned_idempotency_key(
                user_id=user_id,
                path_id=path_id,
            ),
        )
        return progress, True

    def mark_in_progress(self, progress: LearningPathProgress) -> bool:
        if progress.status != "not_started":
            return False
        progress.status = "in_progress"
        progress.started_at = progress.started_at or datetime.now(timezone.utc)
        self.session.flush()
        return True

    def mark_completed(self, progress: LearningPathProgress) -> bool:
        if progress.status == "completed":
            return False
        progress.status = "completed"
        progress.completion_percentage = 100.0
        progress.started_at = progress.started_at or datetime.now(timezone.utc)
        progress.completed_at = progress.completed_at or datetime.now(timezone.utc)
        self.session.flush()
        return True

    def upsert_progress(self, progress: LearningPathProgress) -> LearningPathProgress:
        self.session.add(progress)
        self.session.flush()
        return progress
