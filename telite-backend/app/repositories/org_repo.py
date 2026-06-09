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
from app.core.utils import slugify


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

    # ── Phase 7 Branding (Draft/Publish) ──────────────────────────────────────

    def get_branding(self, slug: str) -> dict[str, Any] | None:
        """
        Return the public (published) branding payload for a tenant slug.
        Reads from the organization_branding table via the relationship.
        """
        org = self.get_by_slug(slug)
        if org is None:
            return None
        b = org.branding  # OrganizationBranding or None
        
        # Parse terminology JSON if exists
        import json
        terminology = {}
        if b and b.terminology_json:
            try:
                terminology = json.loads(b.terminology_json)
            except:
                pass

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
            "terminology": terminology,
        }

    def get_draft_branding(self, org_id: int) -> dict[str, Any] | None:
        """Fetch the current 'draft' version from branding_versions, or fallback to published."""
        from app.models.branding import BrandingVersion
        
        org = self.get_by_id(org_id)
        if not org:
            return None

        stmt = select(BrandingVersion).where(
            BrandingVersion.org_id == org_id,
            BrandingVersion.status == "draft"
        ).order_by(BrandingVersion.version_number.desc()).limit(1)
        
        draft = self.session.execute(stmt).scalar_one_or_none()
        
        if draft:
            import json
            try:
                config = json.loads(draft.configuration_json)
                return config
            except:
                pass
                
        # Fallback to published if no draft
        return self.get_branding(org.slug) if org.slug else None

    def save_draft_branding(self, org_id: int, config: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
        """Save a new draft version."""
        from app.models.branding import BrandingVersion
        import json
        
        # Get latest version number
        stmt = select(BrandingVersion.version_number).where(
            BrandingVersion.org_id == org_id
        ).order_by(BrandingVersion.version_number.desc()).limit(1)
        latest_version = self.session.execute(stmt).scalar_one_or_none() or 0
        
        # Check if there is an existing draft, update it, or create a new one
        stmt = select(BrandingVersion).where(
            BrandingVersion.org_id == org_id,
            BrandingVersion.status == "draft"
        ).limit(1)
        draft = self.session.execute(stmt).scalar_one_or_none()
        
        config_json = json.dumps(config)
        
        if draft:
            draft.configuration_json = config_json
            draft.created_by = user_id
        else:
            draft = BrandingVersion(
                org_id=org_id,
                version_number=latest_version + 1,
                status="draft",
                configuration_json=config_json,
                created_by=user_id
            )
            self.session.add(draft)
            
        self.session.flush()
        return config

    def publish_branding(self, org_id: int, user_id: str | None = None) -> dict[str, Any]:
        """Publish the current draft."""
        from app.models.branding import BrandingVersion, BrandingAuditLog
        from app.models.organization_branding import OrganizationBranding
        import json
        
        # Find draft
        stmt = select(BrandingVersion).where(
            BrandingVersion.org_id == org_id,
            BrandingVersion.status == "draft"
        ).limit(1)
        draft = self.session.execute(stmt).scalar_one_or_none()
        
        if not draft:
            raise ValueError("No draft found to publish")
            
        config = json.loads(draft.configuration_json)
        
        # Update organization_branding (published cache)
        org = self.get_by_id(org_id)
        if org.branding is None:
            org.branding = OrganizationBranding(organization_id=org_id)
            self.session.add(org.branding)
            
        org.branding.primary_color = config.get("primary_color")
        org.branding.secondary_color = config.get("secondary_color")
        org.branding.font_family = config.get("font") or config.get("font_family")
        org.branding.theme_mode = config.get("theme") or config.get("theme_mode", "light")
        org.branding.logo_url = config.get("logo")
        org.branding.favicon_url = config.get("favicon")
        org.branding.login_banner_url = config.get("banner")
        org.branding.custom_domain = config.get("custom_domain")
        
        if "terminology" in config:
            org.branding.terminology_json = json.dumps(config["terminology"])
            
        # Promote draft to published
        draft.status = "published"
        
        # Log audit
        audit = BrandingAuditLog(
            org_id=org_id,
            action="published",
            user_id=user_id,
            changes_json=draft.configuration_json
        )
        self.session.add(audit)
        
        self.session.flush()
        return config

    def rollback_branding(self, org_id: int, version_id: int, user_id: str | None = None) -> dict[str, Any]:
        """Rollback to a previous published version."""
        from app.models.branding import BrandingVersion, BrandingAuditLog
        from app.models.organization_branding import OrganizationBranding
        import json
        
        # Get target version
        stmt = select(BrandingVersion).where(
            BrandingVersion.id == version_id,
            BrandingVersion.org_id == org_id,
            BrandingVersion.status == "published"
        )
        target = self.session.execute(stmt).scalar_one_or_none()
        
        if not target:
            raise ValueError("Version not found or not published")
            
        config = json.loads(target.configuration_json)
        
        # Update published cache
        org = self.get_by_id(org_id)
        if org.branding is None:
            org.branding = OrganizationBranding(organization_id=org_id)
            self.session.add(org.branding)
            
        org.branding.primary_color = config.get("primary_color")
        org.branding.secondary_color = config.get("secondary_color")
        org.branding.font_family = config.get("font") or config.get("font_family")
        org.branding.theme_mode = config.get("theme") or config.get("theme_mode", "light")
        org.branding.logo_url = config.get("logo")
        org.branding.favicon_url = config.get("favicon")
        org.branding.login_banner_url = config.get("banner")
        org.branding.custom_domain = config.get("custom_domain")
        
        if "terminology" in config:
            org.branding.terminology_json = json.dumps(config["terminology"])
            
        # Log audit
        audit = BrandingAuditLog(
            org_id=org_id,
            action="rollback",
            user_id=user_id,
            changes_json=target.configuration_json
        )
        self.session.add(audit)
        
        self.session.flush()
        return config

    def get_branding_history(self, org_id: int) -> list[dict[str, Any]]:
        """List all published versions."""
        from app.models.branding import BrandingVersion
        stmt = select(BrandingVersion).where(
            BrandingVersion.org_id == org_id,
            BrandingVersion.status == "published"
        ).order_by(BrandingVersion.version_number.desc())
        
        versions = self.session.execute(stmt).scalars().all()
        return [v.to_dict() for v in versions]

    # ── Legacy update_branding method (kept for asset uploads temporarily) ──
    def update_branding(
        self,
        org_id: int,
        **kwargs: Any
    ) -> Organization | None:
        """Legacy asset update method."""
        from app.models.organization_branding import OrganizationBranding
        org = self.get_by_id(org_id)
        if org is None:
            return None

        if org.branding is None:
            org.branding = OrganizationBranding(organization_id=org.id)
            self.session.add(org.branding)

        for key, value in kwargs.items():
            if hasattr(org.branding, key):
                setattr(org.branding, key, value)
        self.session.flush()
        return org

    def suspend_org(self, org_id: int) -> None:
        self.session.execute(
            update(Organization).where(Organization.id == org_id).values(status="suspended")
        )

    def activate_org(self, org_id: int) -> None:
        self.session.execute(
            update(Organization).where(Organization.id == org_id).values(status="active")
        )
