"""
Admin branding endpoint — /api/admin/organizations/{org_id}/branding

Allows tenant admins to update their organisation's branding configuration
and upload branding assets (logos, favicons, banners).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
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
        
    if role == "category_admin" and user_org_id == org_id:
        return
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to manage this organization's branding."
    )


@admin_branding_router.patch("/{org_id}/branding")
def update_branding(
    org_id: int,
    request: BrandingUpdateRequest,
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Update branding colors, fonts, and theme for an organization."""
    verify_org_admin(current_user, org_id)

    with get_platform_session() as session:
        repo = OrgRepository(session)
        org = repo.get_by_id(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        updated_org = repo.update_branding(
            org_id=org_id,
            primary_color=request.primary_color,
            secondary_color=request.secondary_color,
            font_family=request.font_family,
            theme_mode=request.theme_mode,
            custom_domain=request.custom_domain,
        )

        return {
            "status": "success",
            "message": "Branding updated successfully",
            "branding": {
                "primary_color": updated_org.branding.primary_color if updated_org.branding else None,
                "secondary_color": updated_org.branding.secondary_color if updated_org.branding else None,
                "font_family": updated_org.branding.font_family if updated_org.branding else None,
                "theme_mode": updated_org.branding.theme_mode if updated_org.branding else None,
                "custom_domain": updated_org.branding.custom_domain if updated_org.branding else None,
            }
        }


@admin_branding_router.post("/{org_id}/branding/upload/{asset_type}")
async def upload_branding_asset(
    org_id: int,
    asset_type: str,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Upload a branding asset (logo, favicon, or login_banner).
    Saves the file to local storage and updates the organization's database record.
    """
    verify_org_admin(current_user, org_id)

    valid_types = {"logo", "favicon", "login_banner"}
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

        # Save file to disk securely
        try:
            file_url = await save_branding_asset(file, org.slug, asset_type)
        except Exception as e:
            logger.exception("Failed to save uploaded branding asset")
            raise HTTPException(status_code=500, detail=str(e))

        # Update DB with new URL
        update_kwargs = {}
        if asset_type == "logo":
            update_kwargs["logo_url"] = file_url
        elif asset_type == "favicon":
            update_kwargs["favicon_url"] = file_url
        elif asset_type == "login_banner":
            update_kwargs["login_banner_url"] = file_url

        repo.update_branding(org_id=org_id, **update_kwargs)

        return {
            "status": "success",
            "message": f"{asset_type} uploaded successfully",
            "url": file_url,
        }
