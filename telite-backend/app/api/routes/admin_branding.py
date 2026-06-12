"""
Admin branding endpoint — /api/admin/organizations/{org_id}/branding

Allows tenant admins to update their organisation's branding configuration
and upload branding assets (logos, favicons, banners).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.db.engine import get_platform_session
from app.repositories.org_repo import OrgRepository
from app.services.upload_service import save_branding_asset

logger = logging.getLogger("telite.admin_branding")

admin_branding_router = APIRouter(prefix="/api/admin/organizations", tags=["Admin Branding"])


class BrandingUpdateRequest(BaseModel):
    primary_color: str | None = None
    secondary_color: str | None = None
    font_family: str | None = None
    theme_mode: str | None = None
    custom_domain: str | None = None


from app.api.auth import TokenData

def verify_org_admin(user: TokenData, org_id: int) -> None:
    """Ensure the user is a super_admin or an admin of this specific org."""
    role = user.role
    user_org_id = user.org_id
    
    if role == "super_admin":
        return
        
    if role in ["category_admin", "company_super_admin", "college_super_admin"] and user_org_id == org_id:
        return
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to manage this organization's branding."
    )


@admin_branding_router.get("/{org_id}/branding/draft")
def get_draft_branding(
    org_id: int,
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Get current draft branding config."""
    verify_org_admin(current_user, org_id)
    with get_platform_session() as session:
        repo = OrgRepository(session)
        draft = repo.get_draft_branding(org_id)
        return {"status": "success", "branding": draft or {}}

@admin_branding_router.post("/{org_id}/branding/draft")
def save_draft_branding(
    org_id: int,
    request: dict[str, Any],
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Save config as draft."""
    verify_org_admin(current_user, org_id)
    with get_platform_session() as session:
        repo = OrgRepository(session)
        draft = repo.save_draft_branding(org_id, request, user_id=current_user.id)
        return {"status": "success", "message": "Draft saved successfully", "branding": draft}

@admin_branding_router.post("/{org_id}/branding/publish")
def publish_branding(
    org_id: int,
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Publish current draft to live."""
    verify_org_admin(current_user, org_id)
    with get_platform_session() as session:
        repo = OrgRepository(session)
        try:
            published = repo.publish_branding(org_id, user_id=current_user.id)
            return {"status": "success", "message": "Branding published successfully", "branding": published}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

@admin_branding_router.get("/{org_id}/branding/history")
def get_branding_history(
    org_id: int,
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Get published branding history."""
    verify_org_admin(current_user, org_id)
    with get_platform_session() as session:
        repo = OrgRepository(session)
        history = repo.get_branding_history(org_id)
        return {"status": "success", "history": history}

@admin_branding_router.post("/{org_id}/branding/rollback/{version_id}")
def rollback_branding(
    org_id: int,
    version_id: int,
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Rollback to a specific version."""
    verify_org_admin(current_user, org_id)
    with get_platform_session() as session:
        repo = OrgRepository(session)
        try:
            rolled_back = repo.rollback_branding(org_id, version_id, user_id=current_user.id)
            return {"status": "success", "message": "Rolled back successfully", "branding": rolled_back}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

@admin_branding_router.post("/{org_id}/branding/upload/{asset_type}")
async def upload_branding_asset(
    org_id: int,
    asset_type: str,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Upload a branding asset (logo, favicon, or login_banner) directly to the draft."""
    verify_org_admin(current_user, org_id)

    valid_types = {"logo", "favicon", "login_banner", "certificate"}
    if asset_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid asset type. Must be one of: {', '.join(valid_types)}"
        )

    with get_platform_session() as session:
        repo = OrgRepository(session)
        org = repo.get_by_id(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        try:
            file_url = await save_branding_asset(file, org.slug, asset_type)
        except Exception as e:
            logger.exception("Failed to save uploaded branding asset")
            raise HTTPException(status_code=500, detail=str(e))

        # We keep the legacy update here to ensure the file URL persists independently
        # But we also want the frontend to include it in the draft save.
        update_kwargs = {}
        if asset_type == "logo":
            update_kwargs["logo_url"] = file_url
        elif asset_type == "favicon":
            update_kwargs["favicon_url"] = file_url
        elif asset_type == "login_banner":
            update_kwargs["login_banner_url"] = file_url
        elif asset_type == "certificate":
            update_kwargs["certificate_template_url"] = file_url

        repo.update_branding(org_id=org_id, **update_kwargs)

        return {
            "status": "success",
            "message": f"{asset_type} uploaded successfully",
            "url": file_url,
        }
