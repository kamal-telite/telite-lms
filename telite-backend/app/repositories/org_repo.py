"""
OrgRepository — organisation (tenant) data access.

Replaces: list_organizations, get_organization, create_organization,
update_organization, create_platform_organization, toggle_feature_flag, etc.
"""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.repositories.base_repo import BaseRepository
from app.services.store import slugify


class OrgRepository(BaseRepository[Organization]):
    model = Organization

    # ── Lookups ───────────────────────────────────────────────────────────────

    def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(Organization.slug == slug.lower().strip())
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_domain(self, domain: str) -> Organization | None:
        stmt = select(Organization).where(Organization.domain == domain.lower().strip())
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_name(self, name: str) -> Organization | None:
        stmt = select(Organization).where(Organization.name == name.strip())
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(
        self,
        *,
        status: str | None = None,
        org_type: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Organization]:
        stmt = select(Organization)
        if status:
            stmt = stmt.where(Organization.status == status)
        if org_type:
            stmt = stmt.where(Organization.type == org_type)
        if search:
            term = f"%{search}%"
            stmt = stmt.where(Organization.name.ilike(term))
        stmt = stmt.order_by(Organization.name).limit(limit).offset(offset)
        return self.session.execute(stmt).scalars().all()

    # ── Mutations ─────────────────────────────────────────────────────────────

    def create_org(
        self,
        *,
        name: str,
        org_type: str,
        domain: str,
        created_by: str | None = None,
        **extra: Any,
    ) -> Organization:
        slug = extra.pop("slug", None) or slugify(name)
        # Ensure slug uniqueness
        base_slug = slug
        counter = 1
        while self.get_by_slug(slug) is not None:
            slug = f"{base_slug}-{counter}"
            counter += 1

        org = Organization(
            name=name.strip(),
            type=org_type,
            domain=domain.lower().strip(),
            slug=slug,
            status="active",
            plan="free",
            created_by=created_by,
            **extra,
        )
        self.session.add(org)
        self.session.flush()
        return org

    def update_org(self, org: Organization, **fields: Any) -> Organization:
        for key, value in fields.items():
            if hasattr(org, key):
                setattr(org, key, value)
        self.session.flush()
        return org

    def update_branding(
        self,
        org_id: int,
        *,
        logo_url: str | None = None,
        favicon_url: str | None = None,
        primary_color: str | None = None,
        secondary_color: str | None = None,
        font_family: str | None = None,
        theme_mode: str | None = None,
        custom_domain: str | None = None,
        login_banner_url: str | None = None,
    ) -> Organization | None:
        """Update branding fields on the organisation_branding row."""
        from app.models.organization_branding import OrganizationBranding

        org = self.get_by_id(org_id)
        if org is None:
            return None

        # Auto-create branding row if it doesn't exist yet
        if org.branding is None:
            org.branding = OrganizationBranding(organization_id=org.id)
            self.session.add(org.branding)
            self.session.flush()

        updates = {
            k: v for k, v in {
                "logo_url": logo_url,
                "favicon_url": favicon_url,
                "primary_color": primary_color,
                "secondary_color": secondary_color,
                "font_family": font_family,
                "theme_mode": theme_mode,
                "custom_domain": custom_domain,
                "login_banner_url": login_banner_url,
            }.items() if v is not None
        }
        for key, value in updates.items():
            if hasattr(org.branding, key):
                setattr(org.branding, key, value)
        self.session.flush()
        return org

    def get_branding(self, slug: str) -> dict[str, Any] | None:
        """
        Return the public branding payload for a tenant slug.
        Reads from the organization_branding table via the relationship.
        """
        org = self.get_by_slug(slug)
        if org is None:
            return None
        b = org.branding  # OrganizationBranding or None
        return {
            "organization": org.name,
            "slug": org.slug,
            "logo": b.logo_url if b else None,
            "favicon": b.favicon_url if b else None,
            "primary_color": (b.primary_color if b else None) or "#2563EB",
            "secondary_color": (b.secondary_color if b else None) or "#111827",
            "font": (b.font_family if b else None) or "Inter",
            "theme": (b.theme_mode if b else None) or "light",
            "banner": b.login_banner_url if b else None,
            "custom_domain": b.custom_domain if b else None,
        }

    def suspend_org(self, org_id: int) -> None:
        self.session.execute(
            update(Organization).where(Organization.id == org_id).values(status="suspended")
        )

    def activate_org(self, org_id: int) -> None:
        self.session.execute(
            update(Organization).where(Organization.id == org_id).values(status="active")
        )
