from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.engine import platform_db_session
from app.repositories.org_repo import OrgRepository

logger = logging.getLogger("telite.signup")

signup_router = APIRouter(tags=["Signup & Verification"])

@signup_router.get("/signup/organizations")
def get_organizations(type: str | None = Query(default=None), db: Session = Depends(platform_db_session)):
    org_repo = OrgRepository(db)
    orgs = org_repo.list_all(org_type=type)
    return [
        {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "type": org.type,
            "logo_url": org.logo_url if hasattr(org, 'logo_url') else None,
        }
        for org in orgs
    ]
