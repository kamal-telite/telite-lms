import json
from uuid import uuid4
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.api.auth import get_current_user, require_admin, TokenData
from app.db.engine import db_session
from app.repositories.media_repo import MediaRepository
from app.models.media_asset import MediaAsset
from app.services.r2_client import generate_presigned_upload_url, generate_presigned_download_url

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

def _uploads_root() -> Path:
    return Path(__file__).resolve().parents[3] / "uploads" / "media"

def _safe_filename(filename: str) -> str:
    safe = "".join(ch for ch in filename if ch.isalnum() or ch in ".-_ ")
    return safe.strip().replace(" ", "_") or "asset"

def _download_url_for(asset: MediaAsset) -> str:
    if asset.object_key.startswith("/uploads/"):
        return asset.object_key
    return generate_presigned_download_url(asset.object_key)

@media_router.post("/upload-url", dependencies=[Depends(require_admin)])
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
    db.commit()
    
    # Generate Presigned URL
    upload_url = generate_presigned_upload_url(object_key, request.mime_type)
    
    return {
        "upload_url": upload_url,
        "asset_id": asset.id,
        "object_key": object_key
    }

@media_router.post("/upload", dependencies=[Depends(require_admin)])
async def upload_asset(
    file: UploadFile = File(...),
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
        uploaded_by=current_user.id
    )
    media_repo.save_asset(asset)
    media_repo.log_activity(
        current_user.id,
        current_user.org_id,
        "MEDIA_UPLOADED",
        json.dumps({"asset_id": asset.id, "filename": asset.filename})
    )
    db.commit()
    db.refresh(asset)

    return {
        "asset": {
            "id": asset.id,
            "filename": asset.filename,
            "object_key": asset.object_key,
            "asset_version": asset.asset_version,
            "size_bytes": asset.size_bytes,
            "mime_type": asset.mime_type,
            "download_url": _download_url_for(asset),
        }
    }

@media_router.get("", dependencies=[Depends(require_admin)])
def list_assets(
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    media_repo = MediaRepository(db)
    assets = media_repo.get_assets(current_user.org_id)
    
    response = []
    for a in assets:
        response.append({
            "id": a.id,
            "filename": a.filename,
            "object_key": a.object_key,
            "asset_version": a.asset_version,
            "size_bytes": a.size_bytes,
            "mime_type": a.mime_type,
            "download_url": _download_url_for(a)
        })
        
    return {"assets": response}

@media_router.delete("/{asset_id}", dependencies=[Depends(require_admin)])
def delete_asset(
    asset_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    media_repo = MediaRepository(db)
    asset = media_repo.get_asset_by_id(asset_id, current_user.org_id)
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    media_repo.delete_asset(asset, current_user.id)
    
    media_repo.log_activity(
        current_user.id, 
        current_user.org_id, 
        "MEDIA_DELETED", 
        json.dumps({"asset_id": asset.id, "filename": asset.filename})
    )
    db.commit()
    return {"success": True}
