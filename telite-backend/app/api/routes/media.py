import json
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import TokenData, get_current_user, require_admin
from app.core.permissions import require_capability
from app.core.storage_paths import media_upload_root
from app.db.engine import db_session
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.course_section import CourseSection
from app.models.lesson_block import LessonBlock
from app.models.media_asset import MediaAsset
from app.repositories.media_repo import MediaRepository
from app.services.audit_service import AuditService
from app.services.h5p_service import (
    MAX_H5P_PACKAGE_BYTES,
    assert_h5p_asset,
    install_h5p_package,
    is_h5p_asset,
    resolve_h5p_extract_dir,
    safe_h5p_file_path,
    update_h5p_version_manifest,
)
from app.services.r2_client import generate_presigned_download_url, generate_presigned_upload_url

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
    return media_upload_root()

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

def _metadata_dict(asset: MediaAsset) -> dict:
    if not asset.metadata_json:
        return {}
    try:
        parsed = json.loads(asset.metadata_json)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}

def _merge_tags(existing: list[str], extra: list[str]) -> list[str]:
    merged = list(existing)
    for tag in extra:
        value = str(tag).strip().lower()
        if value and value not in merged:
            merged.append(value[:40])
    return merged[:20]

def _require_h5p_permission(current_user: TokenData, permission: str) -> None:
    if current_user.role == "super_admin" or current_user.is_platform_admin:
        return
    if not current_user.has_permission(permission):
        raise HTTPException(status_code=403, detail=f"You do not have the required capability: {permission}")

def _download_url_for(asset: MediaAsset) -> str:
    if asset.object_key.startswith("/uploads/"):
        return asset.object_key
    return generate_presigned_download_url(asset.object_key)

def _usage_count(db: Session, asset_id: int, org_id: int) -> int:
    from app.models.media_asset_usage import MediaAssetUsage
    return db.query(MediaAssetUsage).filter(
        MediaAssetUsage.media_asset_id == asset_id,
        MediaAssetUsage.org_id == org_id
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
        "metadata": _metadata_dict(asset),
        "download_url": _download_url_for(asset),
        "used_by_blocks": used_by_blocks,
        "can_delete": used_by_blocks == 0,
    }

def _h5p_metadata_payload(metadata, asset_version: int) -> dict:
    return {
        "title": metadata.title,
        "mainLibrary": metadata.main_library,
        "language": metadata.language,
        "embedTypes": ["div"],
        "asset_version": asset_version,
        "file_count": metadata.file_count,
        "extracted_bytes": metadata.extracted_bytes,
    }

@media_router.post("/upload-url", dependencies=[Depends(require_admin), Depends(require_capability("media.upload"))])
def create_upload_url(
    request: GenerateUploadUrlRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    if is_h5p_asset(request.filename, request.mime_type):
        _require_h5p_permission(current_user, "h5p.upload")
        raise HTTPException(
            status_code=400,
            detail="H5P packages must be uploaded through the validated media upload endpoint.",
        )

    media_repo = MediaRepository(db)
    
    # Generate unique object key
    unique_id = uuid4().hex
    object_key = f"{current_user.org_id}/{unique_id}_{request.filename}"
    
    # Register the asset
    asset = MediaAsset(
        org_id=current_user.org_id,
        file_name=request.filename,
        storage_key=object_key,
        file_size=request.size_bytes,
        file_type=request.mime_type,
        storage_provider="r2",
        url=object_key,
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
    h5p_upload = is_h5p_asset(file.filename, file.content_type)
    if h5p_upload:
        _require_h5p_permission(current_user, "h5p.upload")
    if h5p_upload and size_bytes > MAX_H5P_PACKAGE_BYTES:
        raise HTTPException(status_code=400, detail="H5P package is too large")
    if size_bytes > 500 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    mime_type = file.content_type or "application/octet-stream"
    filename = _safe_filename(file.filename or "asset")
    org_dir = _uploads_root() / str(current_user.org_id)
    org_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid4().hex}_{filename}"
    target = org_dir / stored_name
    h5p_metadata = None
    if h5p_upload:
        mime_type = "application/x-h5p"
        h5p_metadata = install_h5p_package(
            target,
            contents=contents,
            filename=filename,
            mime_type=mime_type,
            extract_root=org_dir / "h5p_extracted" / stored_name,
        )
    else:
        target.write_bytes(contents)

    object_key = f"/uploads/media/{current_user.org_id}/{stored_name}"
    asset = MediaAsset(
        org_id=current_user.org_id,
        file_name=file.filename or filename,
        storage_key=object_key,
        file_size=size_bytes,
        file_type=mime_type,
        storage_provider="local",
        url=object_key,
        folder=_clean_folder(folder),
        tags_json=json.dumps(_merge_tags(_clean_tags(tags), ["h5p"] if h5p_upload else [])),
        metadata_json=json.dumps(_h5p_metadata_payload(h5p_metadata, 1)) if h5p_metadata else None,
        uploaded_by=current_user.id
    )
    media_repo.save_asset(asset)
    if h5p_upload:
        update_h5p_version_manifest(
            org_dir,
            asset_id=asset.id,
            asset_version=asset.asset_version or 1,
            stored_name=stored_name,
            metadata=h5p_metadata,
        )
    media_repo.log_activity(
        current_user.id,
        current_user.org_id,
        "MEDIA_UPLOADED",
        json.dumps({"asset_id": asset.id, "filename": asset.filename})
    )
    AuditService.log(db, current_user.org_id, current_user.id, "media", asset.id, "media.uploaded")
    if h5p_upload:
        AuditService.log(db, current_user.org_id, current_user.id, "h5p", asset.id, "h5p.uploaded")
    response = _asset_response(db, asset)
    db.commit()

    return {
        "asset": response
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
            MediaAsset.file_name.ilike(f"%{term}%") |
            MediaAsset.tags_json.ilike(f"%{term}%") |
            MediaAsset.folder.ilike(f"%{term}%")
        )
    if folder:
        query = query.filter(MediaAsset.folder == _clean_folder(folder))
    if tag:
        query = query.filter(MediaAsset.tags_json.ilike(f'%"{tag.strip().lower()}"%'))
    if type and type != "all":
        if type == "pdf":
            query = query.filter(MediaAsset.file_type == "application/pdf")
        elif type == "other":
            query = query.filter(
                ~MediaAsset.file_type.startswith("image/"),
                ~MediaAsset.file_type.startswith("video/"),
                ~MediaAsset.file_type.startswith("audio/"),
                MediaAsset.file_type != "application/pdf",
            )
        elif type.endswith("/"):
            query = query.filter(MediaAsset.file_type.startswith(type))
        elif type == "scorm":
            query = query.filter(
                MediaAsset.file_type.in_(
                    (
                        "application/zip",
                        "application/x-zip-compressed",
                        "application/octet-stream",
                    )
                )
            )
        elif type == "h5p":
            query = query.filter(
                MediaAsset.file_type.in_(
                    (
                        "application/zip",
                        "application/x-h5p",
                        "application/zip-compressed",
                        "application/octet-stream",
                    )
                ),
                MediaAsset.file_name.ilike("%.h5p")
            )
        elif "/" in type:
            query = query.filter(MediaAsset.file_type == type)
        else:
            query = query.filter(MediaAsset.file_type.startswith(f"{type}/"))

    assets = query.order_by(MediaAsset.created_at.desc(), MediaAsset.id.desc()).limit(limit).all()
    
    usage_counts = {}
    if assets:
        from sqlalchemy import func

        from app.models.media_asset_usage import MediaAssetUsage
        counts_query = db.query(
            MediaAssetUsage.media_asset_id,
            func.count(MediaAssetUsage.id)
        ).filter(
            MediaAssetUsage.media_asset_id.in_([a.id for a in assets]),
            MediaAssetUsage.org_id == current_user.org_id
        ).group_by(MediaAssetUsage.media_asset_id).all()
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
    response = _asset_response(db, asset)
    media_repo.log_activity(
        current_user.id,
        current_user.org_id,
        "MEDIA_METADATA_UPDATED",
        json.dumps({"asset_id": asset.id, "folder": asset.folder, "tags": _tag_list(asset)})
    )
    AuditService.log(db, current_user.org_id, current_user.id, "media", asset.id, "media.updated")
    db.commit()
    return {"asset": response}

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
    replacing_h5p = is_h5p_asset(asset.filename, asset.mime_type)
    replacement_is_h5p = is_h5p_asset(file.filename, file.content_type)
    if replacing_h5p or replacement_is_h5p:
        _require_h5p_permission(current_user, "h5p.edit")
    if replacing_h5p:
        assert_h5p_asset(file.filename or asset.filename, file.content_type or "application/octet-stream")
    if replacement_is_h5p and size_bytes > MAX_H5P_PACKAGE_BYTES:
        raise HTTPException(status_code=400, detail="H5P package is too large")
    if size_bytes > 500 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    mime_type = file.content_type or "application/octet-stream"
    filename = _safe_filename(file.filename or asset.filename)
    org_dir = _uploads_root() / str(current_user.org_id)
    org_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid4().hex}_{filename}"
    target = org_dir / stored_name
    h5p_metadata = None
    if replacing_h5p or replacement_is_h5p:
        mime_type = "application/x-h5p"
        h5p_metadata = install_h5p_package(
            target,
            contents=contents,
            filename=filename,
            mime_type=mime_type,
            extract_root=org_dir / "h5p_extracted" / stored_name,
        )
    else:
        target.write_bytes(contents)

    asset.file_name = file.filename or filename
    asset.storage_key = f"/uploads/media/{current_user.org_id}/{stored_name}"
    asset.file_size = size_bytes
    asset.file_type = mime_type
    if replacing_h5p or replacement_is_h5p:
        asset.tags_json = json.dumps(_merge_tags(_tag_list(asset), ["h5p"]))
        asset.metadata_json = json.dumps(_h5p_metadata_payload(h5p_metadata, asset.asset_version))
        update_h5p_version_manifest(
            org_dir,
            asset_id=asset.id,
            asset_version=asset.asset_version,
            stored_name=stored_name,
            metadata=h5p_metadata,
        )
    media_repo.log_activity(
        current_user.id,
        current_user.org_id,
        "MEDIA_REPLACED",
        json.dumps({"asset_id": asset.id, "filename": asset.filename, "asset_version": asset.asset_version})
    )
    AuditService.log(db, current_user.org_id, current_user.id, "media", asset.id, "media.replaced")
    if replacing_h5p or replacement_is_h5p:
        AuditService.log(db, current_user.org_id, current_user.id, "h5p", asset.id, "h5p.replaced")
    response = _asset_response(db, asset)
    db.commit()
    return {"asset": response}

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
    if is_h5p_asset(asset.filename, asset.mime_type):
        _require_h5p_permission(current_user, "h5p.delete")
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

    from app.models.media_asset_usage import MediaAssetUsage
    
    usages = db.query(MediaAssetUsage).filter(
        MediaAssetUsage.media_asset_id == asset_id,
        MediaAssetUsage.org_id == current_user.org_id
    ).all()
    
    results = []
    
    # Pre-fetch LessonBlocks for batch resolving
    lesson_block_ids = [int(u.entity_id) for u in usages if u.entity_type == "lesson_block" and str(u.entity_id).isdigit()]
    if lesson_block_ids:
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
            .filter(LessonBlock.id.in_(lesson_block_ids))
        )
        
        block_map = {row.block_id: row for row in query.all()}
        
        for u in usages:
            if u.entity_type == "lesson_block" and str(u.entity_id).isdigit():
                b_id = int(u.entity_id)
                if b_id in block_map:
                    row = block_map[b_id]
                    results.append({
                        "usage_context": u.usage_context,
                        "entity_type": "lesson_block",
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

@media_router.get("/h5p/{asset_id}/{file_path:path}")
def get_h5p_file(
    asset_id: int,
    file_path: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    media_repo = MediaRepository(db)
    asset = media_repo.get_asset_by_id(asset_id, current_user.org_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    assert_h5p_asset(asset.filename, asset.mime_type)
        
    # object_key looks like "/uploads/media/{org_id}/{stored_name}"
    parts = asset.object_key.split("/")
    stored_name = parts[-1]
    org_dir = _uploads_root() / str(current_user.org_id)
    extract_dir = resolve_h5p_extract_dir(
        org_dir,
        asset_id=asset.id,
        asset_version=asset.asset_version,
        current_stored_name=stored_name,
        current_asset_version=asset.asset_version or 1,
    )
    target_file = safe_h5p_file_path(extract_dir, file_path)
        
    return FileResponse(target_file)
