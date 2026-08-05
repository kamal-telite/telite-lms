from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification_preference import (
    NotificationCategory,
    NotificationPreference,
    OrganizationNotificationDefault,
)
from app.models.user import User

logger = logging.getLogger("telite.preferences")

class PreferenceResolver:
    """
    Resolves notification preferences for users, combining system defaults,
    organization defaults, and user-specific overrides.
    """
    def __init__(self, session: Session):
        self.session = session

    def resolve_for_user(self, user_id: str, org_id: int, category_str: str) -> dict[str, bool]:
        """
        Resolves preferences for a single user and category.
        
        Returns:
            dict with boolean keys: 'in_app', 'email'
        """
        if category_str == "security":
            # Security notifications are strictly mandatory
            return {"in_app": True, "email": True}
            
        try:
            category = NotificationCategory(category_str)
        except ValueError:
            # If the category doesn't strictly match our enum, default to True
            logger.warning("Unrecognized notification category '%s', defaulting to True", category_str)
            return {"in_app": True, "email": True}
            
        # 1. Start with system defaults (True for everything except marketing maybe, but default True for all is fine)
        resolved = {"in_app": True, "email": True}
        
        # 2. Check Org defaults
        org_def = self.session.execute(
            select(OrganizationNotificationDefault)
            .where(
                OrganizationNotificationDefault.org_id == org_id,
                OrganizationNotificationDefault.category == category.value
            )
        ).scalar_one_or_none()
        
        if org_def:
            resolved["in_app"] = org_def.channel_in_app
            resolved["email"] = org_def.channel_email
            
        # 3. Check User overrides
        user_pref = self.session.execute(
            select(NotificationPreference)
            .where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.org_id == org_id,
                NotificationPreference.category == category.value
            )
        ).scalar_one_or_none()
        
        if user_pref:
            resolved["in_app"] = user_pref.channel_in_app
            resolved["email"] = user_pref.channel_email
            
        return resolved

    def resolve_for_users_batch(self, user_ids: list[str], org_id: int, category_str: str) -> dict[str, dict[str, bool]]:
        """
        Resolves preferences for a batch of users using a single prefetch query.
        
        Args:
            user_ids: List of user IDs to resolve preferences for.
            org_id: Organization ID.
            category_str: The notification category.
            
        Returns:
            A dictionary mapping user_id to their resolved preferences dict (in_app, email).
        """
        if not user_ids:
            return {}
            
        if category_str == "security":
            return {uid: {"in_app": True, "email": True} for uid in user_ids}
            
        try:
            category = NotificationCategory(category_str)
        except ValueError:
            return {uid: {"in_app": True, "email": True} for uid in user_ids}

        resolved_batch = {}
        
        # 1 & 2. Get base defaults (System + Org)
        base_prefs = {"in_app": True, "email": True}
        org_def = self.session.execute(
            select(OrganizationNotificationDefault)
            .where(
                OrganizationNotificationDefault.org_id == org_id,
                OrganizationNotificationDefault.category == category.value
            )
        ).scalar_one_or_none()
        
        if org_def:
            base_prefs["in_app"] = org_def.channel_in_app
            base_prefs["email"] = org_def.channel_email
            
        # Initialize all users with the base preferences
        for uid in user_ids:
            resolved_batch[uid] = dict(base_prefs)
            
        # 3. Fetch all user overrides in a single query
        user_prefs = self.session.execute(
            select(NotificationPreference)
            .where(
                NotificationPreference.org_id == org_id,
                NotificationPreference.category == category.value,
                NotificationPreference.user_id.in_(user_ids)
            )
        ).scalars().all()
        
        for pref in user_prefs:
            resolved_batch[pref.user_id]["in_app"] = pref.channel_in_app
            resolved_batch[pref.user_id]["email"] = pref.channel_email
            
        return resolved_batch
