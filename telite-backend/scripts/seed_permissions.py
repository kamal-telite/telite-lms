import os
import sys

# Add the project root to sys.path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.engine import get_platform_session
from app.models.role_permission import RolePermission
from app.models.organization import Organization

def seed_permissions():
    with get_platform_session() as db:
        # Define role capabilities based on the matrix
        ROLE_CAPABILITIES = {
            "author": [
                "block.create", "block.edit", "block.delete",
                "module.create", "module.edit", "module.delete",
                "section.create", "section.edit", "section.delete",
                "media.upload", "media.replace", "media.delete",
                "course.submit", "version.view", "version.create"
            ],
            "reviewer": [
                "course.approve", "course.reject", "audit.view", "version.view"
            ],
            "category_admin": [
                "block.create", "block.edit", "block.delete",
                "module.create", "module.edit", "module.delete",
                "section.create", "section.edit", "section.delete",
                "media.upload", "media.replace", "media.delete",
                "course.submit", "course.approve", "course.reject",
                "course.publish", "course.archive",
                "version.view", "version.create", "version.rollback",
                "audit.view", "audit.export"
            ],
            "org_admin": [
                "block.create", "block.edit", "block.delete",
                "module.create", "module.edit", "module.delete",
                "section.create", "section.edit", "section.delete",
                "media.upload", "media.replace", "media.delete",
                "course.submit", "course.approve", "course.reject",
                "course.publish", "course.archive",
                "version.view", "version.create", "version.rollback",
                "audit.view", "audit.export", "permission.manage"
            ]
        }

        try:
            orgs = db.query(Organization).all()
            for org in orgs:
                for role, caps in ROLE_CAPABILITIES.items():
                    for cap in caps:
                        # Check if exists
                        existing = db.query(RolePermission).filter(
                            RolePermission.org_id == org.id,
                            RolePermission.role == role,
                            RolePermission.permission_key == cap
                        ).first()
                        
                        if not existing:
                            rp = RolePermission(
                                org_id=org.id,
                                role=role,
                                permission_key=cap,
                                enabled=True
                            )
                            db.add(rp)
            
            db.commit()
            print("Permissions seeded successfully.")
        except Exception as e:
            print(f"Error seeding permissions: {e}")
            db.rollback()

if __name__ == "__main__":
    seed_permissions()
