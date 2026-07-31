"""Notification Preferences Repository."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification_preference import (
    NotificationCategory,
    NotificationPreference,
    OrganizationNotificationDefault,
)
from app.schemas.notification_preferences import NotificationCategoryConfig


class NotificationPreferenceRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_user_preferences(self, user_id: str, org_id: int) -> dict[str, NotificationPreference]:
        """Fetch all explicit overrides for a given user."""
        stmt = (
            select(NotificationPreference)
            .where(NotificationPreference.user_id == user_id)
            .where(NotificationPreference.org_id == org_id)
        )
        return {p.category: p for p in self.session.execute(stmt).scalars()}

    def get_org_defaults(self, org_id: int) -> dict[str, OrganizationNotificationDefault]:
        """Fetch all tenant-level defaults for an organization."""
        stmt = select(OrganizationNotificationDefault).where(OrganizationNotificationDefault.org_id == org_id)
        return {d.category: d for d in self.session.execute(stmt).scalars()}

    def evaluate_preferences(self, user_id: str, org_id: int) -> list[NotificationCategoryConfig]:
        """
        Merge preferences based on priority: User -> Org -> System.
        System default is always opt-in (True).
        Critical categories are forced to True.
        """
        user_prefs = self.get_user_preferences(user_id, org_id)
        org_defaults = self.get_org_defaults(org_id)
        
        results = []
        for cat in NotificationCategory:
            is_critical = cat == NotificationCategory.SECURITY
            
            if is_critical:
                results.append(
                    NotificationCategoryConfig(
                        category=cat.value,
                        channel_email=True,
                        channel_in_app=True,
                        is_critical=True,
                        source="critical"
                    )
                )
                continue
            
            # 1. User Preference
            if cat.value in user_prefs:
                upref = user_prefs[cat.value]
                results.append(
                    NotificationCategoryConfig(
                        category=cat.value,
                        channel_email=upref.channel_email,
                        channel_in_app=upref.channel_in_app,
                        is_critical=False,
                        source="user"
                    )
                )
                continue
                
            # 2. Org Default
            if cat.value in org_defaults:
                odef = org_defaults[cat.value]
                results.append(
                    NotificationCategoryConfig(
                        category=cat.value,
                        channel_email=odef.channel_email,
                        channel_in_app=odef.channel_in_app,
                        is_critical=False,
                        source="org"
                    )
                )
                continue
                
            # 3. System Default (Opt-in)
            results.append(
                NotificationCategoryConfig(
                    category=cat.value,
                    channel_email=True,
                    channel_in_app=True,
                    is_critical=False,
                    source="system"
                )
            )
            
        return results

    def update_user_preference(
        self, user_id: str, org_id: int, category: str, channel_email: bool | None, channel_in_app: bool | None
    ) -> NotificationPreference:
        """Update or create a user preference for a given category."""
        if category == NotificationCategory.SECURITY.value:
            raise ValueError("Cannot override critical security notification preferences")
            
        stmt = (
            select(NotificationPreference)
            .where(NotificationPreference.user_id == user_id)
            .where(NotificationPreference.category == category)
        )
        pref = self.session.execute(stmt).scalar_one_or_none()
        
        if not pref:
            # Need to get current evaluated value to fill missing fields if only updating one
            evaluated = next(c for c in self.evaluate_preferences(user_id, org_id) if c.category == category)
            email_val = channel_email if channel_email is not None else evaluated.channel_email
            in_app_val = channel_in_app if channel_in_app is not None else evaluated.channel_in_app
            
            pref = NotificationPreference(
                user_id=user_id,
                org_id=org_id,
                category=category,
                channel_email=email_val,
                channel_in_app=in_app_val
            )
            self.session.add(pref)
        else:
            if channel_email is not None:
                pref.channel_email = channel_email
            if channel_in_app is not None:
                pref.channel_in_app = channel_in_app
                
        self.session.flush()
        return pref
