"""API routes for managing notification preferences."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.engine import db_session
from app.api.auth import get_current_user
from app.api.auth import TokenData
from app.models.notification_preference import NotificationCategory
from app.models.user import User
from app.repositories.notification_preference_repo import NotificationPreferenceRepository
from app.schemas.notification_preferences import NotificationCategoryConfig, NotificationPreferenceUpdate

router = APIRouter(prefix="/notifications/preferences", tags=["Notifications"])


@router.get("", response_model=list[NotificationCategoryConfig])
def get_notification_preferences(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> Any:
    """
    Get the fully evaluated notification preferences for the current user.
    This merges explicit user overrides, organization defaults, and system defaults.
    """
    repo = NotificationPreferenceRepository(db)
    return repo.evaluate_preferences(current_user.id, current_user.org_id)


@router.patch("/{category}", response_model=NotificationCategoryConfig)
def update_notification_preference(
    category: str,
    update_data: NotificationPreferenceUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> Any:
    """
    Update the user's notification preferences for a specific category.
    """
    try:
        NotificationCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid notification category: {category}",
        )

    if category == NotificationCategory.SECURITY.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot override critical security notification preferences.",
        )

    repo = NotificationPreferenceRepository(db)
    
    # Update the explicit preference row
    repo.update_user_preference(
        user_id=current_user.id,
        org_id=current_user.org_id,
        category=category,
        channel_email=update_data.channel_email,
        channel_in_app=update_data.channel_in_app,
    )
    db.commit()

    # Re-evaluate and return the updated config
    evaluated = repo.evaluate_preferences(current_user.id, current_user.org_id)
    updated_config = next(c for c in evaluated if c.category == category)
    return updated_config
