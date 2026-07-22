import os
import sys

# Add the project root to sys.path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.rbac import ROLE_PERMISSIONS
from app.db.engine import get_platform_session
from app.models.organization import Organization
from app.models.role_permission import RolePermission

AUTHOR_WORKFLOW_CAPABILITIES = {
    "course.submit",
    "version.view",
    "version.create",
}

REVIEW_WORKFLOW_CAPABILITIES = {
    "course.approve",
    "course.reject",
    "version.view",
}

ADMIN_WORKFLOW_CAPABILITIES = AUTHOR_WORKFLOW_CAPABILITIES | REVIEW_WORKFLOW_CAPABILITIES | {
    "audit.view",
    "audit.export",
    "course.publish",
    "course.archive",
    "version.rollback",
}


def _role_capabilities(role: str, *extras: set[str]) -> list[str]:
    capabilities = set(ROLE_PERMISSIONS[role])
    for extra in extras:
        capabilities.update(extra)
    return sorted(capabilities)


def seed_permissions():
    with get_platform_session() as db:
        # Keep seeded permissions based on the application RBAC matrix. The
        # workflow capabilities below are still enforced by publishing routes
        # through check_capability() until that legacy path is migrated.
        ROLE_CAPABILITIES = {
            "author": _role_capabilities("author", AUTHOR_WORKFLOW_CAPABILITIES),
            "reviewer": _role_capabilities("reviewer", REVIEW_WORKFLOW_CAPABILITIES),
            "category_admin": _role_capabilities("category_admin", ADMIN_WORKFLOW_CAPABILITIES),
            "super_admin": _role_capabilities("super_admin", ADMIN_WORKFLOW_CAPABILITIES),
            # Legacy org_admin rows are treated as the organization super-admin role.
            "org_admin": _role_capabilities("super_admin", ADMIN_WORKFLOW_CAPABILITIES),
        }

        try:
            orgs = db.query(Organization).all()
            for org in orgs:
                for role, caps in ROLE_CAPABILITIES.items():
                    for cap in caps:
                        from sqlalchemy.dialects.postgresql import insert
                        stmt = insert(RolePermission).values(
                            org_id=org.id,
                            role=role,
                            permission_key=cap,
                            enabled=True
                        ).on_conflict_do_nothing(
                            index_elements=['org_id', 'role', 'permission_key']
                        )
                        db.execute(stmt)
            
            db.commit()
            print("Permissions seeded successfully.")
        except Exception as e:
            print(f"Error seeding permissions: {e}")
            db.rollback()

if __name__ == "__main__":
    seed_permissions()
