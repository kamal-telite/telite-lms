import json
from uuid import uuid4
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.api.auth import get_current_user, require_admin, TokenData
from app.db.engine import db_session
from app.repositories.media_repo import MediaRepository
from app.models.media_asset import MediaAsset
from app.models.lesson_block import LessonBlock
from app.models.course_module import CourseModule
from app.models.course_section import CourseSection
from app.models.course import Course
from app.services.r2_client import generate_presigned_upload_url, generate_presigned_download_url
from app.services.audit_service import AuditService
from app.core.permissions import require_capability

media_router = APIRouter(prefix="/authoring/media", tags=["Media Library"])

class GenerateUploadUrlRequest(BaseModel):
    filename: str
    mime_type: str
    size_bytes: int

class AssetResponse(BaseModel):
    id: int
    filename: str
    object_key: str
    asset_version: int
    size_bytes: int
    mime_type: str
    download_url: str

class UpdateAssetMetadataRequest(BaseModel):
    folder: str | None = None
    tags: List[str] = []

def _uploads_root() -> Path:
    return Path(__file__).resolve().parents[3] / "uploads" / "media"

def _safe_filename(filename: str) -> str:
    safe = "".join(ch for ch in filename if ch.isalnum() or ch in ".-_ ")
    return safe.strip().replace(" ", "_") or "asset"

def _clean_folder(folder: str | None) -> str | None:
    if not folder:
        return None
    cleaned = folder.strip().strip("/\\")
    return cleaned[:120] or None

def _clean_tags(tags: List[str] | str | None) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        tags = tags.split(",")
    cleaned = []
    for tag in tags:
        value = str(tag).strip().lower()
        if value and value not in cleaned:
            cleaned.append(value[:40])
    return cleaned[:20]

def _tag_list(asset: MediaAsset) -> list[str]:
    if not asset.tags_json:
        return []
    try:
        parsed = json.loads(asset.tags_json)
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []

def _download_url_for(asset: MediaAsset) -> str:
    if asset.object_key.startswith("/uploads/"):
        return asset.object_key
    return generate_presigned_download_url(asset.object_key)

def _usage_count(db: Session, asset_id: int, org_id: int) -> int:
    return db.query(LessonBlock).filter(
        LessonBlock.media_asset_id == asset_id,
        LessonBlock.org_id == org_id,
        LessonBlock.deleted_at.is_(None),
    ).count()

def _asset_response(db: Session, asset: MediaAsset, usage_count: int | None = None) -> dict:
    used_by_blocks = usage_count if usage_count is not None else _usage_count(db, asset.id, asset.org_id)
    return {
        "id": asset.id,
        "filename": asset.filename,
        "object_key": asset.object_key,
        "asset_version": asset.asset_version,
        "size_bytes": asset.size_bytes,
        "mime_type": asset.mime_type,
        "folder": asset.folder or "",
        "tags": _tag_list(asset),
        "download_url": _download_url_for(asset),
        "used_by_blocks": used_by_blocks,
        "can_delete": used_by_blocks == 0,
    }

@media_router.post("/upload-url", dependencies=[Depends(require_admin), Depends(require_capability("media.upload"))])
def create_upload_url(
    request: GenerateUploadUrlRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    media_repo = MediaRepository(db)
    
    # Generate unique object key
    unique_id = uuid4().hex
    object_key = f"{current_user.org_id}/{unique_id}_{request.filename}"
    
    # Register the asset
    asset = MediaAsset(
        org_id=current_user.org_id,
        filename=request.filename,
        object_key=object_key,
        size_bytes=request.size_bytes,
        mime_type=request.mime_type,
        uploaded_by=current_user.id
    )
    media_repo.save_asset(asset)
    
    # Log Activity
    media_repo.log_activity(
        current_user.id, 
        current_user.org_id, 
        "MEDIA_UPLOADED", 
        json.dumps({"asset_id": asset.id, "filename": asset.filename})
    )
    AuditService.log(db, current_user.org_id, current_user.id, "media", asset.id, "media.uploaded")
    db.commit()
    
    # Generate Presigned URL
    upload_url = generate_presigned_upload_url(object_key, request.mime_type)
    
    return {
        "upload_url": upload_url,
        "asset_id": asset.id,
        "object_key": object_key
    }

@media_router.post("/upload", dependencies=[Depends(require_admin), Depends(require_capability("media.upload"))])
async def upload_asset(
    file: UploadFile = File(...),
    folder: str | None = Form(default=None),
    tags: str | None = Form(default=None),
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    media_repo = MediaRepository(db)

    contents = await file.read()
    size_bytes = len(contents)
    if size_bytes > 500 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    mime_type = file.content_type or "application/octet-stream"
    filename = _safe_filename(file.filename or "asset")
    org_dir = _uploads_root() / str(current_user.org_id)
    org_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid4().hex}_{filename}"
    target = org_dir / stored_name
    target.write_bytes(contents)

    object_key = f"/uploads/media/{current_user.org_id}/{stored_name}"
    asset = MediaAsset(
        org_id=current_user.org_id,
        filename=file.filename or filename,
        object_key=object_key,
        size_bytes=size_bytes,
        mime_type=mime_type,
        folder=_clean_folder(folder),
        tags_json=json.dumps(_clean_tags(tags)),
        uploaded_by=current_user.id
    )
    media_repo.save_asset(asset)
    media_repo.log_activity(
        current_user.id,
        current_user.org_id,
        "MEDIA_UPLOADED",
        json.dumps({"asset_id": asset.id, "filename": asset.filename})
    )
    AuditService.log(db, current_user.org_id, current_user.id, "media", asset.id, "media.uploaded")
    db.commit()
    db.refresh(asset)

    return {
        "asset": _asset_response(db, asset)
    }

@media_router.get("", dependencies=[Depends(require_admin)])
def list_assets(
    search: str | None = Query(default=None, max_length=120),
    type: str | None = Query(default=None, max_length=50),
    folder: str | None = Query(default=None, max_length=120),
    tag: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=100, ge=1, le=250),
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    query = db.query(MediaAsset).filter(
        MediaAsset.org_id == current_user.org_id,
        MediaAsset.deleted_at.is_(None),
    )
    if search:
        term = search.strip()
        query = query.filter(
            MediaAsset.filename.ilike(f"%{term}%") |
            MediaAsset.tags_json.ilike(f"%{term}%") |
            MediaAsset.folder.ilike(f"%{term}%")
        )
    if folder:
        query = query.filter(MediaAsset.folder == _clean_folder(folder))
    if tag:
        query = query.filter(MediaAsset.tags_json.ilike(f'%"{tag.strip().lower()}"%'))
    if type and type != "all":
        if type == "pdf":
            query = query.filter(MediaAsset.mime_type == "application/pdf")
        elif type == "other":
            query = query.filter(
                ~MediaAsset.mime_type.startswith("image/"),
                ~MediaAsset.mime_type.startswith("video/"),
                ~MediaAsset.mime_type.startswith("audio/"),
                MediaAsset.mime_type != "application/pdf",
            )
        elif type.endswith("/"):
            query = query.filter(MediaAsset.mime_type.startswith(type))
        elif type == "scorm":
            query = query.filter(
                MediaAsset.mime_type.in_(
                    (
                        "application/zip",
                        "application/x-zip-compressed",
                        "application/octet-stream",
                    )
                )
            )
        elif "/" in type:
            query = query.filter(MediaAsset.mime_type == type)
        else:
            query = query.filter(MediaAsset.mime_type.startswith(f"{type}/"))

    assets = query.order_by(MediaAsset.created_at.desc(), MediaAsset.id.desc()).limit(limit).all()
    
    usage_counts = {}
    if assets:
        from sqlalchemy import func
        counts_query = db.query(
            LessonBlock.media_asset_id,
            func.count(LessonBlock.id)
        ).filter(
            LessonBlock.media_asset_id.in_([a.id for a in assets]),
            LessonBlock.deleted_at.is_(None)
        ).group_by(LessonBlock.media_asset_id).all()
        for aid, count in counts_query:
            usage_counts[aid] = count
    
    response = [_asset_response(db, a, usage_counts.get(a.id, 0)) for a in assets]
    folders = sorted({asset.folder for asset in assets if asset.folder})
    tags = sorted({tag for asset in assets for tag in _tag_list(asset)})
        
    return {"assets": response, "count": len(response), "folders": folders, "tags": tags}

@media_router.patch("/{asset_id}", dependencies=[Depends(require_admin)])
def update_asset_metadata(
    asset_id: int,
    request: UpdateAssetMetadataRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    media_repo = MediaRepository(db)
    asset = media_repo.get_asset_by_id(asset_id, current_user.org_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.folder = _clean_folder(request.folder)
    asset.tags_json = json.dumps(_clean_tags(request.tags))
    media_repo.log_activity(
        current_user.id,
        current_user.org_id,
        "MEDIA_METADATA_UPDATED",
        json.dumps({"asset_id": asset.id, "folder": asset.folder, "tags": _tag_list(asset)})
    )
    db.commit()
    db.refresh(asset)
    return {"asset": _asset_response(db, asset)}

@media_router.post("/{asset_id}/replace", dependencies=[Depends(require_admin), Depends(require_capability("media.replace"))])
async def replace_asset_file(
    asset_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    media_repo = MediaRepository(db)
    asset = media_repo.get_asset_by_id(asset_id, current_user.org_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    contents = await file.read()
    size_bytes = len(contents)
    if size_bytes > 500 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    mime_type = file.content_type or "application/octet-stream"
    filename = _safe_filename(file.filename or asset.filename)
    org_dir = _uploads_root() / str(current_user.org_id)
    org_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid4().hex}_{filename}"
    target = org_dir / stored_name
    target.write_bytes(contents)

    asset.filename = file.filename or filename
    asset.object_key = f"/uploads/media/{current_user.org_id}/{stored_name}"
    asset.size_bytes = size_bytes
    asset.mime_type = mime_type
    asset.asset_version = (asset.asset_version or 1) + 1
    media_repo.log_activity(
        current_user.id,
        current_user.org_id,
        "MEDIA_REPLACED",
        json.dumps({"asset_id": asset.id, "filename": asset.filename, "asset_version": asset.asset_version})
    )
    AuditService.log(db, current_user.org_id, current_user.id, "media", asset.id, "media.replaced")
    db.commit()
    db.refresh(asset)
    return {"asset": _asset_response(db, asset)}

@media_router.delete("/{asset_id}", dependencies=[Depends(require_admin), Depends(require_capability("media.delete"))])
def delete_asset(
    asset_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    media_repo = MediaRepository(db)
    asset = media_repo.get_asset_by_id(asset_id, current_user.org_id)
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    used_by_blocks = _usage_count(db, asset.id, current_user.org_id)
    if used_by_blocks:
        raise HTTPException(
            status_code=409,
            detail=f"Asset is attached to {used_by_blocks} lesson block(s). Remove it from those blocks before deleting.",
        )
        
    media_repo.delete_asset(asset, current_user.id)
    
    media_repo.log_activity(
        current_user.id, 
        current_user.org_id, 
        "MEDIA_DELETED", 
        json.dumps({"asset_id": asset.id, "filename": asset.filename})
    )
    AuditService.log(db, current_user.org_id, current_user.id, "media", asset.id, "media.deleted")
    db.commit()
    return {"success": True}

@media_router.get("/{asset_id}/usage", dependencies=[Depends(require_admin)])
def get_asset_usage(
    asset_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    media_repo = MediaRepository(db)
    asset = media_repo.get_asset_by_id(asset_id, current_user.org_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    query = (
        db.query(
            LessonBlock.id.label("block_id"),
            LessonBlock.block_type.label("block_type"),
            CourseModule.id.label("module_id"),
            CourseModule.title.label("module_title"),
            CourseSection.id.label("section_id"),
            CourseSection.title.label("section_title"),
            Course.id.label("course_id"),
            Course.name.label("course_title")
        )
        .join(CourseModule, LessonBlock.module_id == CourseModule.id)
        .outerjoin(CourseSection, CourseModule.section_id == CourseSection.id)
        .join(Course, CourseModule.course_id == Course.id)
        .filter(
            LessonBlock.media_asset_id == asset_id,
            LessonBlock.org_id == current_user.org_id,
            LessonBlock.deleted_at.is_(None)
        )
    )
    
    results = []
    for row in query.all():
        results.append({
            "block_id": row.block_id,
            "block_type": row.block_type,
            "module_id": row.module_id,
            "module_title": row.module_title,
            "section_id": row.section_id,
            "section_title": row.section_title or (f"Section {row.section_id}" if row.section_id else "Unassigned Section"),
            "course_id": row.course_id,
            "course_title": row.course_title
        })
        
    return {"usage": results}
