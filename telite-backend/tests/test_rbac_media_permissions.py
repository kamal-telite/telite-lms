import pytest
from fastapi import HTTPException

from app.api.auth import TokenData
from app.core.permissions import require_capability, resolve_permissions
from app.core.rbac import ROLE_PERMISSIONS, Permission, has_permission

MEDIA_PERMISSIONS = {
    Permission.MEDIA_UPLOAD,
    Permission.MEDIA_REPLACE,
    Permission.MEDIA_DELETE,
}


def _category_admin(permissions: list[str] | None = None) -> TokenData:
    return TokenData(
        id="category-admin-1",
        username="category-admin",
        email="category-admin@example.com",
        role="category_admin",
        full_name="Category Admin",
        category_scope="backend-development",
        org_id=1,
        permissions=permissions or [],
    )


class _EmptyQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None


class _AuditDb:
    def query(self, *args, **kwargs):
        return _EmptyQuery()

    def add(self, *args, **kwargs):
        return None

    def flush(self):
        return None

    def commit(self):
        return None


def test_media_permissions_are_authoritative_role_defaults():
    for role in ("author", "category_admin", "super_admin"):
        assert MEDIA_PERMISSIONS.issubset(ROLE_PERMISSIONS[role])


def test_category_admin_resolves_media_permissions_without_seeded_overrides():
    resolved = set(resolve_permissions("category_admin", org_id=1, db=None))

    assert MEDIA_PERMISSIONS.issubset(resolved)


def test_category_admin_upload_guard_passes_from_static_defaults():
    user = _category_admin()
    dependency = require_capability(Permission.MEDIA_UPLOAD)

    assert has_permission(user, Permission.MEDIA_UPLOAD)
    assert dependency(db=None, current_user=user) == user


def test_media_upload_guard_still_rejects_missing_capability_claim_and_role():
    learner = TokenData(
        id="learner-1",
        username="learner",
        email="learner@example.com",
        role="learner",
        full_name="Learner",
        org_id=1,
        permissions=[],
    )
    dependency = require_capability(Permission.MEDIA_UPLOAD)

    with pytest.raises(HTTPException) as exc:
        dependency(db=_AuditDb(), current_user=learner)

    assert exc.value.status_code == 403
    assert Permission.MEDIA_UPLOAD in exc.value.detail
