"""Management API schemas and request/response models."""

from typing import Any
from pydantic import BaseModel, Field


class CategoryPayload(BaseModel):
    name: str
    slug: str
    description: str | None = ""
    admin_user_id: str | None = None
    planned_courses: int = Field(default=0, ge=0)
    status: str = "active"
    accent_color: str | None = None
    org_type: str = "college"
    organization_id: int | None = None


class AdminPayload(BaseModel):
    full_name: str
    email: str
    role: str
    password: str | None = None
    username: str | None = None
    category_scope: str | None = None


class InviteAdminPayload(BaseModel):
    username: str
    email: str
    role: str
    category_scope: str | None = None
    full_name: str | None = None


class InviteLearnerPayload(BaseModel):
    username: str
    email: str
    full_name: str
    category_scope: str | None = None
    course_ids: list[str] = Field(default_factory=list)


class CoursePayload(BaseModel):
    name: str
    slug: str | None = None
    description: str
    tier: str
    status: str = "draft"
    module_count: int = Field(default=0, ge=0)
    modules: list[str] = Field(default_factory=list)
    lessons_count: int = Field(default=0, ge=0)
    hours: float = Field(default=0, ge=0)
    prerequisite_course_id: str | None = None
    cover_image_url: str | None = None


class UserRolePayload(BaseModel):
    role: str
    category_scope: str | None = None


class UserActivePayload(BaseModel):
    is_active: bool


class AllowedDomainPayload(BaseModel):
    domain: str
    label: str
