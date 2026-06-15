"""
TaskRepository — task data access.

Replaces: list_tasks, fetch_task_by_id, create_or_update_task,
delete_task, submit_task.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.task_workflow import TaskAssignment, TaskReview, TaskSubmission
from app.repositories.base_repo import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task

    @staticmethod
    def assignment_status(task_status: str | None) -> str:
        if task_status in (None, "", "pending", "overdue"):
            return "assigned"
        if task_status == "completed":
            return "approved"
        return task_status

    @staticmethod
    def task_status(assignment_status: str | None) -> str:
        if assignment_status == "assigned":
            return "pending"
        if assignment_status == "approved":
            return "completed"
        return assignment_status or "pending"

    def _latest_submission(self, assignment_id: int) -> TaskSubmission | None:
        stmt = (
            select(TaskSubmission)
            .where(TaskSubmission.assignment_id == assignment_id)
            .order_by(desc(TaskSubmission.submitted_at), desc(TaskSubmission.created_at))
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def _latest_review(self, submission_id: int | None) -> TaskReview | None:
        if not submission_id:
            return None
        stmt = (
            select(TaskReview)
            .where(TaskReview.submission_id == submission_id)
            .order_by(desc(TaskReview.reviewed_at), desc(TaskReview.created_at))
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def task_payload(self, task: Task, assignment: TaskAssignment | None = None) -> dict[str, Any]:
        payload = task.to_dict()
        if assignment:
            submission = self._latest_submission(assignment.id)
            review = self._latest_review(submission.id if submission else None)
            payload.update(
                {
                    "assignment_id": assignment.id,
                    "learner_id": assignment.learner_id,
                    "status": assignment.status,
                    "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
                    "started_at": assignment.started_at.isoformat() if assignment.started_at else None,
                    "submitted_at": assignment.submitted_at.isoformat() if assignment.submitted_at else None,
                    "completed_at": assignment.completed_at.isoformat() if assignment.completed_at else None,
                    "submission": submission.to_dict() if hasattr(submission, "to_dict") else self.submission_payload(submission),
                    "review": self.review_payload(review),
                }
            )
        return payload

    def submission_payload(self, submission: TaskSubmission | None) -> dict[str, Any] | None:
        if not submission:
            return None
        return {
            "id": submission.id,
            "assignment_id": submission.assignment_id,
            "submission_notes": submission.submission_notes,
            "attachment_url": submission.attachment_url,
            "github_url": submission.github_url,
            "external_url": submission.external_url,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        }

    def review_payload(self, review: TaskReview | None) -> dict[str, Any] | None:
        if not review:
            return None
        return {
            "id": review.id,
            "submission_id": review.submission_id,
            "review_status": review.review_status,
            "review_notes": review.review_notes,
            "reviewed_by": review.reviewed_by,
            "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
        }

    def list_by_org(
        self,
        org_id: int,
        *,
        category_slug: str | None = None,
        assigned_to: str | None = None,
        status: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[Task]:
        stmt = select(Task).where(Task.org_id == org_id)
        if category_slug:
            stmt = stmt.where(
                or_(Task.category_slug == category_slug, Task.is_cross_category.is_(True))
            )
        if assigned_to:
            stmt = stmt.where(
                or_(
                    Task.assigned_to_user_id == assigned_to,
                    Task.assignment_scope == "all",
                )
            )
        if status:
            stmt = stmt.where(Task.status == status)
        stmt = stmt.order_by(Task.created_at.desc()).limit(limit).offset(offset)
        return self.session.execute(stmt).scalars().all()

    def list_assignment_payloads_by_org(
        self,
        org_id: int,
        *,
        category_slug: str | None = None,
        assigned_to: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        stmt = select(Task, TaskAssignment).join(TaskAssignment, TaskAssignment.task_id == Task.id).where(Task.org_id == org_id)
        if category_slug:
            stmt = stmt.where(or_(Task.category_slug == category_slug, Task.is_cross_category.is_(True)))
        if assigned_to:
            stmt = stmt.where(TaskAssignment.learner_id == assigned_to)
        if status:
            stmt = stmt.where(TaskAssignment.status == status)
        stmt = stmt.order_by(desc(Task.created_at))
        return [self.task_payload(task, assignment) for task, assignment in self.session.execute(stmt).all()]

    def create_task(
        self,
        *,
        title: str,
        category_slug: str,
        org_id: int,
        assigned_label: str,
        assigned_by: str | None = None,
        **extra: Any,
    ) -> Task:
        from datetime import datetime
        extra_status = extra.pop("status", "pending")
        task = Task(
            id=f"task-{uuid.uuid4().hex[:10]}",
            title=title.strip(),
            category_slug=category_slug,
            org_id=org_id,
            assigned_label=assigned_label,
            assigned_by=assigned_by,
            status=extra_status,
            **extra,
        )
        self.session.add(task)
        self.session.flush()
        return task

    def create_assignment(self, *, task: Task, learner_id: str, status: str | None = None) -> TaskAssignment:
        assignment = TaskAssignment(
            task_id=task.id,
            learner_id=learner_id,
            status=status or self.assignment_status(task.status),
            assigned_at=datetime.now(timezone.utc),
            org_id=task.org_id,
        )
        self.session.add(assignment)
        self.session.flush()
        return assignment

    def get_assignment(self, task_id: str, learner_id: str | None = None) -> TaskAssignment | None:
        stmt = select(TaskAssignment).where(TaskAssignment.task_id == task_id)
        if learner_id:
            stmt = stmt.where(TaskAssignment.learner_id == learner_id)
        return self.session.execute(stmt.order_by(TaskAssignment.id).limit(1)).scalar_one_or_none()

    def start_assignment(self, assignment: TaskAssignment) -> TaskAssignment:
        now = datetime.now(timezone.utc)
        if assignment.status in ("assigned", "revision_requested"):
            assignment.status = "in_progress"
        if not assignment.started_at:
            assignment.started_at = now
        self.session.flush()
        return assignment

    def submit_assignment(
        self,
        assignment: TaskAssignment,
        *,
        submission_notes: str | None = None,
        attachment_url: str | None = None,
        github_url: str | None = None,
        external_url: str | None = None,
    ) -> TaskSubmission:
        now = datetime.now(timezone.utc)
        assignment.status = "submitted"
        assignment.submitted_at = now
        submission = TaskSubmission(
            assignment_id=assignment.id,
            submission_notes=submission_notes,
            attachment_url=attachment_url,
            github_url=github_url,
            external_url=external_url,
            submitted_at=now,
            org_id=assignment.org_id,
        )
        self.session.add(submission)
        self.session.flush()
        return submission

    def review_assignment(
        self,
        assignment: TaskAssignment,
        *,
        review_status: str,
        review_notes: str | None,
        reviewed_by: str | None,
    ) -> TaskReview:
        submission = self._latest_submission(assignment.id)
        if not submission:
            raise ValueError("Task has no submission to review")
        now = datetime.now(timezone.utc)
        assignment.status = review_status
        if review_status == "approved":
            assignment.completed_at = now
        review = TaskReview(
            submission_id=submission.id,
            review_status=review_status,
            review_notes=review_notes,
            reviewed_by=reviewed_by,
            reviewed_at=now,
            org_id=assignment.org_id,
        )
        self.session.add(review)
        self.session.flush()
        return review

    def update_task(self, task: Task, **fields: Any) -> Task:
        for key, value in fields.items():
            if hasattr(task, key):
                setattr(task, key, value)
        self.session.flush()
        return task

    def submit_task(self, task: Task) -> Task:
        task.status = "submitted"
        self.session.flush()
        return task

    def delete_task(self, task: Task) -> None:
        self.session.delete(task)
        self.session.flush()
