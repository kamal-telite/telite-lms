from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.engine import db_session
from app.api.auth import get_current_user, TokenData
from app.repositories.notification_repo import NotificationRepository

notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])

class NotificationResponse(BaseModel):
    id: int
    user_id: str
    title: str
    message: str
    type: str
    is_read: bool
    org_id: int
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    action_url: Optional[str] = None
    created_at: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

class PaginatedNotifications(BaseModel):
    items: List[NotificationResponse]

class UnreadCountResponse(BaseModel):
    count: int

@notifications_router.get("", response_model=PaginatedNotifications)
def get_notifications(
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Get notifications for the current user."""
    repo = NotificationRepository(db)
    notifications = repo.list_for_user(
        user_id=current_user.id,
        org_id=current_user.org_id,
        limit=limit,
        unread_only=unread_only
    )
    
    return {
        "items": [n.to_dict() for n in notifications]
    }

@notifications_router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Get the number of unread notifications."""
    repo = NotificationRepository(db)
    count = repo.count_unread(current_user.id, current_user.org_id)
    return {"count": count}

@notifications_router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Mark a specific notification as read."""
    repo = NotificationRepository(db)
    updated = repo.mark_read(current_user.id, current_user.org_id, [notification_id])
    db.commit()
    
    if not updated:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    return {"success": True}

@notifications_router.post("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Mark all unread notifications as read."""
    repo = NotificationRepository(db)
    count = repo.mark_read(current_user.id, current_user.org_id)
    db.commit()
    
    return {"success": True, "updated": count}
