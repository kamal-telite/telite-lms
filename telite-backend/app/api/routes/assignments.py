from __future__ import annotations

import json
import logging
from inspect import isawaitable
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.api.auth import TokenData, get_current_user, require_admin
from app.db.engine import db_session
from app.services.assignment_service import AssignmentService, set_assignment_actor_context
from app.services.assignment_storage import get_storage_provider


assignment_router = APIRouter(tags=["Native Assignments"])
logger = logging.getLogger(__name__)


class DraftRequest(BaseModel):
    submission_text: str | None = None
    existing_file_paths: list[str] | None = None


class GradeRequest(BaseModel):
    grade: float | None = Field(default=None, ge=0)
    feedback: str | None = None
    returned: bool = False


class ReviewRequest(BaseModel):
    feedback: str | None = None


def _service(db: Session, current_user: TokenData) -> AssignmentService:
    set_assignment_actor_context(db, current_user)
    return AssignmentService(db)


async def _await_if_needed(result):
    if isawaitable(result):
        return await result
    return result


async def _parse_submission_request(request: Request) -> tuple[str | None, List[UploadFile], list[str] | None]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        files = [
            value
            for value in form.values()
            if isinstance(value, StarletteUploadFile) and value.filename
        ]
        submission_text = form.get("submission_text")
        existing_file_paths = []
        existing_json = form.get("existing_file_paths")
        if existing_json:
            try:
                existing_file_paths = json.loads(str(existing_json))
            except Exception:
                existing_file_paths = []
        return (
            str(submission_text) if submission_text is not None else None,
            files,
            existing_file_paths,
        )

    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            body = {}
        if isinstance(body, dict):
            submission_text = body.get("submission_text")
            existing_file_paths = body.get("existing_file_paths") or []
            return (
                str(submission_text) if submission_text is not None else None,
                [],
                existing_file_paths,
            )

    return None, [], []


@assignment_router.get("/learner/assignments/{block_id}/submission")
def get_assignment_submission(
    block_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    try:
        return _service(db, current_user).get_learner_submission(block_id, current_user)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Assignment submission lookup failed",
            extra={
                "assignment_id": block_id,
                "learner_id": getattr(current_user, "id", None),
                "endpoint": "/api/v1/learner/assignments/{block_id}/submission",
            },
        )
        raise HTTPException(status_code=500, detail="Unable to load your assignment submission.") from exc


@assignment_router.patch("/learner/assignments/{block_id}/draft")
async def save_assignment_draft(
    block_id: int,
    body: DraftRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    return await _await_if_needed(
        _service(db, current_user).save_draft(
            block_id,
            current_user,
            body.submission_text,
            [],
            existing_file_paths=body.existing_file_paths,
        )
    )


@assignment_router.post("/learner/assignments/{block_id}/submit")
async def submit_assignment(
    block_id: int,
    request: Request,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    submission_text, files, existing_file_paths = await _parse_submission_request(request)
    return await _await_if_needed(
        _service(db, current_user).submit(
            block_id,
            current_user,
            submission_text,
            files,
            resubmit=False,
            existing_file_paths=existing_file_paths,
        )
    )


@assignment_router.post("/learner/assignments/{block_id}/resubmit")
async def resubmit_assignment(
    block_id: int,
    request: Request,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    submission_text, files, existing_file_paths = await _parse_submission_request(request)
    return await _await_if_needed(
        _service(db, current_user).submit(
            block_id,
            current_user,
            submission_text,
            files,
            resubmit=True,
            existing_file_paths=existing_file_paths,
        )
    )


@assignment_router.get("/admin/assignments/{block_id}/submissions")
def list_assignment_submissions(
    block_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(require_admin),
):
    return _service(db, current_user).list_submissions(block_id, current_user)


@assignment_router.get("/admin/categories/{category_slug}/assignment-verifications")
def list_assignment_verifications(
    category_slug: str,
    status: str | None = Query(default=None),
    course_id: str | None = Query(default=None),
    learner_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(require_admin),
):
    return _service(db, current_user).list_verification_queue(
        category_slug,
        current_user,
        status_filter=status,
        course_id=course_id,
        learner_id=learner_id,
        search=search,
    )


@assignment_router.get("/admin/submissions/{submission_id}")
def get_admin_submission(
    submission_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(require_admin),
):
    return _service(db, current_user).get_admin_submission(submission_id, current_user)


@assignment_router.post("/admin/submissions/{submission_id}/grade")
def grade_submission(
    submission_id: int,
    body: GradeRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(require_admin),
):
    return _service(db, current_user).grade(
        submission_id,
        current_user,
        grade=body.grade,
        feedback=body.feedback,
        returned=body.returned,
    )


@assignment_router.post("/admin/submissions/{submission_id}/approve")
def approve_submission(
    submission_id: int,
    body: ReviewRequest | None = None,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(require_admin),
):
    return _service(db, current_user).review(
        submission_id,
        current_user,
        approved=True,
        feedback=body.feedback if body else None,
    )


@assignment_router.post("/admin/submissions/{submission_id}/reject")
def reject_submission(
    submission_id: int,
    body: ReviewRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(require_admin),
):
    return _service(db, current_user).review(
        submission_id,
        current_user,
        approved=False,
        feedback=body.feedback,
    )


@assignment_router.get("/submissions/{submission_id}/download")
def download_submission_attachment(
    submission_id: int,
    asset_id: str | None = Query(default=None),
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    service = _service(db, current_user)
    _, file_info = service.resolve_download(submission_id, current_user, asset_id=asset_id)
    path = get_storage_provider().resolve(file_info["file_path"])
    filename = file_info.get("original_filename") or file_info.get("filename") or path.name
    mime_type = file_info.get("mime_type") or "application/octet-stream"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type=mime_type, filename=filename)
