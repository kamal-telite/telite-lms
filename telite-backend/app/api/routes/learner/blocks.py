"""Learner block-related endpoints (PDF, poll, resources)."""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, TokenData
from app.db.engine import db_session
from app.models.lesson_block import LessonBlock
from app.models.media_asset import MediaAsset
from app.models.lesson_block_progress import LessonBlockProgress
from app.repositories.progress_repo import ProgressRepository
from app.models.learner_event import LearnerEvent
from app.api.routes.learner.schemas import PollVoteRequest
from app.api.routes.learner.utils import (
    resolve_block_for_learner,
    resolve_local_media_path,
    inline_pdf_disposition,
)

logger = logging.getLogger(__name__)

learner_blocks_router = APIRouter(tags=["Learner Block APIs"])


@learner_blocks_router.get("/blocks/{block_id}/pdf")
def view_pdf_block(
    block_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    """View a PDF block."""
    block, _ = resolve_block_for_learner(block_id, db, current_user.id, current_user.org_id)
    if block.get("block_type") != "pdf":
        raise HTTPException(status_code=400, detail="Block is not a PDF")

    settings = block.get("metadata_json") or block.get("settings") or {}
    asset_id = block.get("media_asset_id") or settings.get("asset_id")
    if not asset_id:
        raise HTTPException(status_code=404, detail="PDF asset is not configured")
    try:
        asset_id = int(asset_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="PDF asset is not configured") from exc

    asset = db.query(MediaAsset).filter(
        MediaAsset.id == asset_id,
        MediaAsset.org_id == current_user.org_id,
        MediaAsset.deleted_at.is_(None),
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="PDF asset not found")
    if asset.mime_type != "application/pdf" and not asset.file_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Configured asset is not a PDF")

    if asset.storage_key.startswith("/uploads/") or asset.storage_key.startswith("org_"):
        path = resolve_local_media_path(asset.storage_key, current_user.org_id)
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=asset.file_name,
            headers={
                "Content-Disposition": inline_pdf_disposition(asset.file_name),
                "X-Content-Type-Options": "nosniff",
            },
        )

    from app.services.r2_client import generate_presigned_download_url
    return RedirectResponse(generate_presigned_download_url(asset.storage_key), status_code=302)


@learner_blocks_router.post("/blocks/{block_id}/poll/vote")
async def poll_vote(
    block_id: int,
    request: PollVoteRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Vote on a poll block."""
    block, course_id = resolve_block_for_learner(block_id, db, current_user.id, current_user.org_id)
    if block.get("block_type") != "poll":
        raise HTTPException(status_code=400, detail="Block is not a poll")
    
    settings = block.get("metadata_json", block.get("settings", {}))
    options = settings.get("options", [])
    if request.option_id < 0 or request.option_id >= len(options):
        raise HTTPException(status_code=400, detail="Invalid option")
    
    # Prevent duplicate voting: check if user already voted on this poll
    existing_vote = db.query(LearnerEvent).filter(
        LearnerEvent.user_id == current_user.id,
        LearnerEvent.block_id == block_id,
        LearnerEvent.event_type == "POLL_VOTED",
        LearnerEvent.org_id == current_user.org_id,
    ).first()
    
    allow_change = settings.get("allow_vote_change", False)
    if existing_vote and not allow_change:
        raise HTTPException(status_code=409, detail="You have already voted on this poll")
    
    if existing_vote and allow_change:
        # Update existing vote
        existing_vote.payload_json = {"option_id": request.option_id}
        existing_vote.created_at = datetime.utcnow()
    else:
        # New vote
        db.add(LearnerEvent(
            user_id=current_user.id,
            course_id=course_id,
            module_id=block.get("module_id"),
            block_id=block_id,
            event_type="POLL_VOTED",
            schema_version="1.0",
            payload_json={"option_id": request.option_id},
            created_at=datetime.utcnow(),
            org_id=current_user.org_id
        ))
    
    progress_repo = ProgressRepository(db)
    bp = progress_repo.get_block_progress(current_user.id, str(block_id), current_user.org_id)
    if not bp:
        bp = LessonBlockProgress(
            user_id=current_user.id,
            block_id=str(block_id),
            module_id=block.get("module_id"),
            org_id=current_user.org_id,
            status="completed",
            completed_at=datetime.utcnow()
        )
        db.add(bp)
    else:
        bp.status = "completed"
        bp.completed_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Vote recorded", "voted": True}


@learner_blocks_router.get("/blocks/{block_id}/poll-results")
async def poll_results(
    block_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Get poll results."""
    block, course_id = resolve_block_for_learner(block_id, db, current_user.id, current_user.org_id)
    if block.get("block_type") != "poll":
        raise HTTPException(status_code=400, detail="Block is not a poll")
    
    settings = block.get("metadata_json", block.get("settings", {}))
    options = settings.get("options", [])
    
    # Aggregate real votes from LearnerEvent table
    vote_events = db.query(LearnerEvent).filter(
        LearnerEvent.block_id == block_id,
        LearnerEvent.event_type == "POLL_VOTED",
        LearnerEvent.org_id == current_user.org_id,
    ).all()
    
    vote_counts = {}
    total_votes = 0
    my_vote = []
    for evt in vote_events:
        payload = evt.payload_json or {}
        option_id = payload.get("option_id")
        if option_id is not None:
            vote_counts[option_id] = vote_counts.get(option_id, 0) + 1
            total_votes += 1
            if evt.user_id == current_user.id:
                my_vote = [option_id]
    
    results = {}
    for i, o in enumerate(options):
        opt_id = o.get("id", i)
        results[opt_id] = vote_counts.get(opt_id, vote_counts.get(i, 0))
    
    return {"results": results, "total_votes": total_votes, "my_vote": my_vote}


@learner_blocks_router.get("/blocks/{block_id}/resources/{asset_id}/download")
def download_resource(
    block_id: int,
    asset_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Return a download URL for a resource collection asset."""
    block, course_id = resolve_block_for_learner(block_id, db, current_user.id, current_user.org_id)
    if block.get("block_type") != "resource_collection":
        raise HTTPException(status_code=400, detail="Block is not a resource collection")
    
    asset = db.query(MediaAsset).filter(
        MediaAsset.id == asset_id,
        MediaAsset.org_id == current_user.org_id,
        MediaAsset.deleted_at.is_(None),
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Generate download URL
    from app.services.r2_client import generate_presigned_download_url
    if asset.storage_key.startswith("/uploads/"):
        # Return absolute URL for local files to avoid React Router interception
        from app.core.runtime import get_api_base_url
        base_url = get_api_base_url()
        url = f"{base_url}{asset.storage_key}"
    else:
        url = generate_presigned_download_url(asset.storage_key)
    
    # Emit telemetry event
    db.add(LearnerEvent(
        user_id=current_user.id,
        course_id=course_id,
        module_id=block.get("module_id"),
        block_id=block_id,
        event_type="RESOURCE_DOWNLOADED",
        schema_version="1.0",
        payload_json={"asset_id": asset_id, "filename": asset.file_name},
        created_at=datetime.utcnow(),
        org_id=current_user.org_id
    ))
    db.commit()
    
    return {"url": url, "filename": asset.file_name}
