from __future__ import annotations

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import TokenData
from app.db.rls import set_platform_context, set_rls_context
from app.models.assignment_submission import AssignmentSubmission
from app.models.learner_event import LearnerEvent
from app.models.lesson_block_progress import LessonBlockProgress
from app.models.notification import NotificationType
from app.core.notification_payloads import assignment_graded_metadata
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.enrollment_repo import EnrollmentRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.progress_repo import ProgressRepository
from app.services.assignment_storage import StorageProvider, get_storage_provider
from app.services.gradebook_service import GradebookService
from datetime import datetime, timezone


ADMIN_ROLES = {"platform_admin", "super_admin", "category_admin", "instructor", "author", "reviewer"}
MUTABLE_STATUSES = {"draft", "returned"}


def set_assignment_actor_context(db: Session, user: TokenData) -> None:
    if user.is_platform_admin:
        set_platform_context(db)
    elif user.org_id is not None:
        set_rls_context(db, user.org_id)
    db.execute(text("SELECT set_config('app.current_user_id', :user_id, true)"), {"user_id": user.id})
    db.execute(text("SELECT set_config('app.current_user_role', :role, true)"), {"role": "platform_admin" if user.is_platform_admin else user.role})


class AssignmentService:
    def __init__(self, db: Session, storage: StorageProvider | None = None):
        self.db = db
        self.repo = AssignmentRepository(db)
        self.storage = storage or get_storage_provider()

    def _require_assignment_block(self, block_id: int, user: TokenData):
        context = self.repo.get_block_context(block_id, None if user.is_platform_admin else user.org_id)
        if not context:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment block not found")
        block, module, course = context
        if block.block_type != "assignment":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Block is not an assignment")
        return block, module, course

    def _require_learner_access(self, block_id: int, user: TokenData):
        block, module, course = self._require_assignment_block(block_id, user)
        if not EnrollmentRepository(self.db).has_access(user.id, course.id, user.org_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enrolled or access denied")
        return block, module, course

    def _require_admin_access(self, block_id: int, user: TokenData):
        block, module, course = self._require_assignment_block(block_id, user)
        if user.is_platform_admin:
            return block, module, course
        if user.role not in ADMIN_ROLES:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        if user.role == "category_admin" and user.category_scope and user.category_scope != course.category_slug:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Category access denied")
        return block, module, course

    async def _store_files(self, *, block_id: int, user: TokenData, files: list[UploadFile] | None) -> list[dict]:
        stored = []
        for upload in files or []:
            if not upload or not upload.filename:
                continue
            item = await self.storage.upload(
                org_id=user.org_id,
                block_id=block_id,
                learner_id=user.id,
                file=upload,
            )
            stored.append(item.to_public_dict(asset_id=item.file_path))
        return stored

    def get_learner_submission(self, block_id: int, user: TokenData) -> dict:
        self._require_learner_access(block_id, user)
        submission = self.repo.get_submission_for_learner(block_id, user.id, user.org_id)
        return {"submission": submission.to_dict() if submission else None}

    async def save_draft(self, block_id: int, user: TokenData, submission_text: str | None, files: list[UploadFile] | None = None) -> dict:
        self._require_learner_access(block_id, user)
        existing = self.repo.get_submission_for_learner(block_id, user.id, user.org_id)
        if existing and existing.status in {"submitted", "graded"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submitted assignments cannot be edited as drafts")
        uploaded = await self._store_files(block_id=block_id, user=user, files=files)
        existing_files = existing.submission_files_json if existing else []
        submission = self.repo.save_submission(
            block_id=block_id,
            learner_id=user.id,
            org_id=user.org_id,
            submission_text=submission_text,
            files=[*(existing_files or []), *uploaded],
            status="draft",
        )
        self.db.commit()
        return {"message": "Assignment draft saved", "submission": submission.to_dict()}

    async def submit(self, block_id: int, user: TokenData, submission_text: str | None, files: list[UploadFile] | None, *, resubmit: bool = False) -> dict:
        block, module, course = self._require_learner_access(block_id, user)
        existing = self.repo.get_submission_for_learner(block_id, user.id, user.org_id)
        if existing and existing.status == "graded" and not resubmit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update a graded assignment without resubmitting")
        if existing and existing.status == "submitted" and resubmit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submission is already awaiting review")

        uploaded = await self._store_files(block_id=block_id, user=user, files=files)
        existing_files = existing.submission_files_json if existing else []
        all_files = [*(existing_files or []), *uploaded]
        if not (submission_text or "").strip() and not all_files:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submission text or file is required")

        submission = self.repo.save_submission(
            block_id=block_id,
            learner_id=user.id,
            org_id=user.org_id,
            submission_text=submission_text,
            files=all_files,
            status="resubmitted" if resubmit else "submitted",
        )
        self._mark_assignment_complete(user=user, block_id=block_id, module_id=module.id, course_id=course.id, files_count=len(all_files))
        self.db.commit()
        return {"message": "Assignment submitted successfully", "submission": submission.to_dict()}

    def _mark_assignment_complete(self, *, user: TokenData, block_id: int, module_id: int, course_id: str, files_count: int) -> None:
        now = datetime.now(timezone.utc)
        progress_repo = ProgressRepository(self.db)
        progress = progress_repo.get_block_progress(user.id, block_id, user.org_id)
        if progress is None:
            self.db.add(LessonBlockProgress(
                user_id=user.id,
                block_id=str(block_id),
                module_id=module_id,
                org_id=user.org_id,
                status="completed",
                completed_at=now,
            ))
        else:
            progress.status = "completed"
            progress.completed_at = now
        self.db.add(LearnerEvent(
            user_id=user.id,
            course_id=course_id,
            module_id=module_id,
            block_id=block_id,
            event_type="ASSIGNMENT_SUBMITTED",
            schema_version="1.0",
            payload_json={"files_count": files_count},
            created_at=now,
            org_id=user.org_id,
        ))

    def list_submissions(self, block_id: int, user: TokenData) -> dict:
        block, module, course = self._require_admin_access(block_id, user)
        rows = self.repo.list_submissions_for_block(block_id, block.org_id)
        return {
            "assignment": {
                "block_id": block.id,
                "module_id": module.id,
                "course_id": course.id,
                "course_name": course.name,
                "title": block.content or (block.metadata_json or {}).get("title") or "Assignment",
            },
            "submissions": [
                {
                    **submission.to_dict(),
                    "learner": {
                        "id": learner.id,
                        "name": learner.full_name,
                        "email": learner.email,
                    },
                }
                for submission, learner in rows
            ],
        }

    def get_admin_submission(self, submission_id: int, user: TokenData) -> dict:
        submission = self._require_submission_access(submission_id, user, admin=True)
        return {"submission": submission.to_dict()}

    def grade(self, submission_id: int, user: TokenData, *, grade: float | None, feedback: str | None, returned: bool = False) -> dict:
        submission = self._require_submission_access(submission_id, user, admin=True)
        block, module, course = self._require_admin_access(submission.block_id, user)
        updated = self.repo.grade_submission(
            submission,
            grade=grade,
            feedback=feedback,
            graded_by=user.id,
            returned=returned,
        )
        if not returned and updated.grade is not None:
            gradebook = GradebookService(self.db)
            grade_item = gradebook.ensure_assignment_grade_item(
                org_id=updated.org_id,
                course=course,
                block=block,
                actor_user_id=user.id,
            )
            points_possible = float(grade_item.points_possible or 100)
            points_awarded = float(updated.grade)
            percentage = (points_awarded / points_possible * 100.0) if points_possible > 0 else None
            gradebook.upsert_current_result(
                org_id=updated.org_id,
                course_id=course.id,
                course_version_id=gradebook.course_version_token(
                    user_id=updated.user_id,
                    course_id=course.id,
                    org_id=updated.org_id,
                ),
                grade_item=grade_item,
                user_id=updated.user_id,
                source_type="assignment_submission",
                source_id=str(updated.id),
                attempt_number=updated.attempt_number,
                points_awarded=points_awarded,
                points_possible=points_possible,
                percentage=percentage,
                status="graded",
                graded_by=user.id,
                graded_at=updated.graded_at,
                feedback=updated.feedback,
                metadata={
                    "source_submission_id": updated.id,
                    "attempt_number": updated.attempt_number,
                    "attempt_strategy": (grade_item.grading_policy_json or {}).get("attempt_strategy", "latest"),
                    "returned": returned,
                },
            )
        NotificationRepository(self.db).create(
            user_id=updated.user_id,
            org_id=updated.org_id,
            title="Assignment Graded",
            body="Your assignment has been graded.",
            notif_type=NotificationType.ASSIGNMENT_GRADED,
            source_type="assignment",
            source_id=str(updated.id),
            metadata=assignment_graded_metadata(
                course_id=course.id,
                block_id=block.id,
                submission_id=updated.id,
            ),
        )
        self.db.commit()
        return {"message": "Submission graded", "submission": updated.to_dict()}

    def _require_submission_access(self, submission_id: int, user: TokenData, *, admin: bool = False) -> AssignmentSubmission:
        submission = self.repo.get_submission(submission_id, None if user.is_platform_admin else user.org_id)
        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
        if not admin and not user.is_platform_admin and submission.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Submission access denied")
        if admin and not user.is_platform_admin:
            self._require_admin_access(submission.block_id, user)
        return submission

    def resolve_download(self, submission_id: int, user: TokenData, *, asset_id: str | None = None) -> tuple[AssignmentSubmission, dict]:
        submission = self._require_submission_access(submission_id, user, admin=user.role in ADMIN_ROLES or user.is_platform_admin)
        files = submission.submission_files_json or []
        if not files:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No attachment found")
        selected = None
        if asset_id:
            selected = next((item for item in files if str(item.get("asset_id") or item.get("file_path")) == str(asset_id)), None)
        else:
            selected = files[0]
        if not selected or not selected.get("file_path"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
        return submission, selected
