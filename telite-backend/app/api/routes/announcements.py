"""Announcement runtime APIs."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.auth import TokenData, get_current_user, require_admin
from app.db.engine import db_session
from app.repositories.announcement_repo import AnnouncementRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.user_repo import UserRepository
from app.core.notification_payloads import announcement_notification_metadata
from app.models.notification import NotificationType


announcements_router = APIRouter(prefix="/announcements", tags=["Announcements"])


class AnnouncementPayload(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    audience_type: Literal["all", "role", "category", "user"] = "all"
    audience_value: str | None = None
    status: Literal["draft", "published", "archived"] = "published"


class AnnouncementUpdatePayload(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1)
    audience_type: Literal["all", "role", "category", "user"] | None = None
    audience_value: str | None = None
    status: Literal["draft", "published", "archived"] | None = None


def _require_org(current_user: TokenData) -> int:
    if current_user.org_id is None:
        raise HTTPException(status_code=403, detail="Organization context is required")
    return current_user.org_id


def _create_announcement_notifications(db: Session, announcement, org_id: int) -> None:
    """Create notifications for all users targeted by the announcement."""
    from app.models.announcement import AnnouncementAudience
    from app.services.notification_service import NotificationService
    
    # Get the audience for this announcement
    audience_stmt = select(AnnouncementAudience).where(
        AnnouncementAudience.announcement_id == announcement.id
    )
    audience_rows = db.execute(audience_stmt).scalars().all()
    
    service = NotificationService(db)
    
    context = {
        "announcement_id": announcement.id,
        "title": announcement.title,
        "body": announcement.body
    }
    
    for audience in audience_rows:
        audience_dict = {
            "type": audience.audience_type,
            "value": audience.audience_value
        }
        service.fanout_event("announcement.published", org_id, context, audience_dict)


@announcements_router.get("/my")
def list_my_announcements(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    org_id = _require_org(current_user)
    items = AnnouncementRepository(db).list_for_user(
        user_id=current_user.id,
        org_id=org_id,
        role=current_user.role,
        category_scope=current_user.category_scope,
    )
    return {"items": items, "total": len(items)}


@announcements_router.patch("/{announcement_id}/read")
def mark_announcement_read(
    announcement_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    org_id = _require_org(current_user)
    repo = AnnouncementRepository(db)
    visible = {
        item["id"]
        for item in repo.list_for_user(
            user_id=current_user.id,
            org_id=org_id,
            role=current_user.role,
            category_scope=current_user.category_scope,
        )
    }
    if announcement_id not in visible:
        raise HTTPException(status_code=404, detail="Announcement not found")
    read_state = repo.mark_read(announcement_id=announcement_id, user_id=current_user.id, org_id=org_id)
    db.commit()
    return {
        "announcement_id": announcement_id,
        "is_read": True,
        "read_at": read_state.read_at.isoformat(),
    }


@announcements_router.get("", dependencies=[Depends(require_admin)])
def list_announcements(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    org_id = _require_org(current_user)
    items = [item.to_dict() for item in AnnouncementRepository(db).list_for_admin(org_id)]
    return {"items": items, "total": len(items)}


@announcements_router.post("", dependencies=[Depends(require_admin)])
def create_announcement(
    payload: AnnouncementPayload,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    org_id = _require_org(current_user)
    try:
        announcement = AnnouncementRepository(db).create(
            org_id=org_id,
            title=payload.title,
            body=payload.body,
            created_by=current_user.id,
            audience_type=payload.audience_type,
            audience_value=payload.audience_value,
            status=payload.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    
    # Create notifications if announcement is published
    if announcement.status == "published":
        try:
            _create_announcement_notifications(db, announcement, org_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                f"Failed to create notifications for announcement {announcement.id}: {e}",
                exc_info=True
            )
    
    db.commit()
    return announcement.to_dict()


@announcements_router.get("/{announcement_id}", dependencies=[Depends(require_admin)])
def get_announcement(
    announcement_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    announcement = AnnouncementRepository(db).get_for_admin(announcement_id, _require_org(current_user))
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return announcement.to_dict()


@announcements_router.patch("/{announcement_id}", dependencies=[Depends(require_admin)])
def update_announcement(
    announcement_id: int,
    payload: AnnouncementUpdatePayload,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    org_id = _require_org(current_user)
    
    # Get current announcement to check if status is changing to published
    repo = AnnouncementRepository(db)
    current_announcement = repo.get_for_admin(announcement_id, org_id)
    was_published = current_announcement and current_announcement.status == "published"
    
    try:
        announcement = repo.update(
            announcement_id=announcement_id,
            org_id=org_id,
            title=payload.title,
            body=payload.body,
            audience_type=payload.audience_type,
            audience_value=payload.audience_value,
            status=payload.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Create notifications if announcement is being published now (wasn't published before)
    if announcement.status == "published" and not was_published:
        _create_announcement_notifications(db, announcement, org_id)
    
    db.commit()
    return announcement.to_dict()


@announcements_router.delete("/{announcement_id}", dependencies=[Depends(require_admin)])
def delete_announcement(
    announcement_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    deleted = AnnouncementRepository(db).delete(announcement_id, _require_org(current_user))
    if not deleted:
        raise HTTPException(status_code=404, detail="Announcement not found")
    db.commit()
    return {"status": "deleted", "id": announcement_id}
