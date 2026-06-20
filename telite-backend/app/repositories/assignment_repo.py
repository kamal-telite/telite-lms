from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.lesson_block import LessonBlock
from app.models.user import User


class AssignmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_block_context(self, block_id: int, org_id: int | None) -> tuple[LessonBlock, CourseModule, Course] | None:
        stmt = (
            select(LessonBlock, CourseModule, Course)
            .join(CourseModule, LessonBlock.module_id == CourseModule.id)
            .join(Course, CourseModule.course_id == Course.id)
            .where(
                LessonBlock.id == block_id,
                LessonBlock.deleted_at.is_(None),
                CourseModule.deleted_at.is_(None),
            )
        )
        if org_id is not None:
            stmt = stmt.where(
                LessonBlock.org_id == org_id,
                CourseModule.org_id == org_id,
                Course.org_id == org_id,
            )
        row = self.session.execute(stmt).first()
        if not row:
            return None
        return row[0], row[1], row[2]

    def get_submission_for_learner(self, block_id: int, learner_id: str, org_id: int) -> AssignmentSubmission | None:
        stmt = select(AssignmentSubmission).where(
            AssignmentSubmission.block_id == block_id,
            AssignmentSubmission.user_id == learner_id,
            AssignmentSubmission.org_id == org_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_submission(self, submission_id: int, org_id: int | None = None) -> AssignmentSubmission | None:
        stmt = select(AssignmentSubmission).where(AssignmentSubmission.id == submission_id)
        if org_id is not None:
            stmt = stmt.where(AssignmentSubmission.org_id == org_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_submissions_for_block(self, block_id: int, org_id: int) -> Sequence[tuple[AssignmentSubmission, User]]:
        stmt = (
            select(AssignmentSubmission, User)
            .join(User, AssignmentSubmission.user_id == User.id)
            .where(AssignmentSubmission.block_id == block_id, AssignmentSubmission.org_id == org_id)
            .order_by(AssignmentSubmission.updated_at.desc().nullslast(), AssignmentSubmission.created_at.desc())
        )
        return self.session.execute(stmt).all()

    def save_submission(
        self,
        *,
        block_id: int,
        learner_id: str,
        org_id: int,
        submission_text: str | None,
        files: list[dict],
        status: str,
    ) -> AssignmentSubmission:
        now = datetime.now(timezone.utc)
        submission = self.get_submission_for_learner(block_id, learner_id, org_id)
        if submission is None:
            submission = AssignmentSubmission(
                block_id=block_id,
                user_id=learner_id,
                org_id=org_id,
                attempt_number=1,
                created_at=now,
            )
            self.session.add(submission)
        elif status in ("submitted", "resubmitted") and submission.status in ("submitted", "graded", "returned"):
            submission.attempt_number = (submission.attempt_number or 1) + 1

        submission.submission_text = submission_text
        submission.submission_files_json = files
        submission.status = status
        submission.updated_at = now
        if files:
            first = files[0]
            submission.file_path = first.get("file_path")
            submission.original_filename = first.get("original_filename") or first.get("filename")
            submission.mime_type = first.get("mime_type")
            submission.file_size = first.get("file_size") or first.get("size_bytes")
        if status in ("submitted", "resubmitted"):
            submission.submitted_at = now
        self.session.flush()
        return submission

    def grade_submission(
        self,
        submission: AssignmentSubmission,
        *,
        grade: float | None,
        feedback: str | None,
        graded_by: str,
        returned: bool = False,
    ) -> AssignmentSubmission:
        now = datetime.now(timezone.utc)
        submission.grade = grade
        submission.feedback = feedback
        submission.graded_by = graded_by
        submission.graded_at = now
        submission.status = "returned" if returned else "graded"
        submission.updated_at = now
        self.session.flush()
        return submission
