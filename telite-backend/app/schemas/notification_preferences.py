"""Pydantic schemas for notification preferences."""

from pydantic import BaseModel, ConfigDict


class NotificationPreferenceBase(BaseModel):
    category: str
    channel_email: bool
    channel_in_app: bool


class NotificationPreferenceRead(NotificationPreferenceBase):
    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    channel_email: bool | None = None
    channel_in_app: bool | None = None


class OrganizationNotificationDefaultRead(NotificationPreferenceBase):
    model_config = ConfigDict(from_attributes=True)


class OrganizationNotificationDefaultUpdate(BaseModel):
    channel_email: bool | None = None
    channel_in_app: bool | None = None


class NotificationCategoryConfig(BaseModel):
    """Merged configuration representing the final evaluated preference."""
    category: str
    channel_email: bool
    channel_in_app: bool
    is_critical: bool
    source: str  # "user", "org", "system", "critical"

