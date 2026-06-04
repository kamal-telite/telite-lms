"""
Public branding endpoint — /api/public/branding/{tenant}

Returns organisation-specific branding data for the frontend theme engine.
This endpoint is intentionally PUBLIC (no auth required) so the login page
can load the correct branding before the user authenticates.

PHASE 3: Foundation endpoint using the new OrgRepository.
PHASE 7: Will be expanded with full white-label engine.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.db.engine import get_platform_session
from app.repositories.org_repo import OrgRepository

logger = logging.getLogger("telite.branding")

branding_router = APIRouter(prefix="/api/public", tags=["Branding"])


@branding_router.get("/branding/{tenant_slug}")
def get_tenant_branding(tenant_slug: str) -> dict[str, Any]:
    """
    Return public branding configuration for a tenant slug.

    Used by the React frontend to:
    - Set CSS variables (primary_color, secondary_color, font_family)
    - Display the correct logo and favicon
    - Apply the correct theme mode (light/dark)
    - Show the organisation name on the login page

    This endpoint bypasses RLS because it is public — it only returns
    non-sensitive branding data, never user or course data.
    """
    with get_platform_session() as session:
        repo = OrgRepository(session)
        branding = repo.get_branding(tenant_slug.lower().strip())

    if branding is None:
        # Return safe defaults so the frontend never breaks
        logger.warning("Branding requested for unknown tenant: %s", tenant_slug)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{tenant_slug}' not found.",
        )

    return branding


@branding_router.get("/branding/{tenant_slug}/health")
def branding_health(tenant_slug: str) -> dict[str, Any]:
    """Lightweight check — confirms the tenant exists without full branding."""
    with get_platform_session() as session:
        repo = OrgRepository(session)
        org = repo.get_by_slug(tenant_slug.lower().strip())

    if org is None:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    return {
        "slug": org.slug,
        "name": org.name,
        "status": org.status,
        "has_branding": bool(org.primary_color or org.logo_url),
    }
