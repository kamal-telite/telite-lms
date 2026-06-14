from pathlib import Path

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.auth import TokenData, get_current_user
from app.main import create_app


def _client_as(user: TokenData | None) -> TestClient:
    app = create_app()

    def override_current_user():
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return user

    app.dependency_overrides[get_current_user] = override_current_user
    return TestClient(app)


def test_local_media_requires_same_tenant_or_platform_admin():
    uploads_root = Path(__file__).resolve().parents[1] / "uploads" / "media"
    asset_dir = uploads_root / "9001"
    asset_dir.mkdir(parents=True, exist_ok=True)
    asset_path = asset_dir / "phase-a5-media.txt"
    asset_path.write_text("tenant media", encoding="utf-8")

    tenant_user = TokenData(
        id="user-a",
        email="a@example.test",
        role="superadmin",
        full_name="Tenant A",
        org_id=9001,
    )
    other_tenant_user = tenant_user.model_copy(update={"org_id": 9002})
    platform_user = tenant_user.model_copy(update={"org_id": None, "is_platform_admin": True})

    try:
        assert _client_as(None).get("/uploads/media/9001/phase-a5-media.txt").status_code == 401

        same_tenant_response = _client_as(tenant_user).get("/uploads/media/9001/phase-a5-media.txt")
        assert same_tenant_response.status_code == 200
        assert same_tenant_response.text == "tenant media"

        cross_tenant_response = _client_as(other_tenant_user).get("/uploads/media/9001/phase-a5-media.txt")
        assert cross_tenant_response.status_code == 404

        platform_response = _client_as(platform_user).get("/uploads/media/9001/phase-a5-media.txt")
        assert platform_response.status_code == 200
    finally:
        asset_path.unlink(missing_ok=True)
