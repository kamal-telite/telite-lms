from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api.auth import TokenData
from app.api.routes import platform as platform_routes
from app.db.engine import platform_db_session
from app.main import create_app
from app.models.invitation import OrgInvitation
from app.models.organization import Organization


def _platform_admin() -> TokenData:
    return TokenData(
        id="platform-admin",
        username="platform-admin",
        email="platform@example.com",
        full_name="Platform Admin",
        role="platform_admin",
        org_id=1,
        is_platform_admin=True,
        permissions=["platform.manage_admins", "platform.manage_orgs"],
    )


def _client(db_session, monkeypatch) -> TestClient:
    app = create_app()

    def override_platform_admin():
        return _platform_admin()

    def override_db_session():
        yield db_session
        db_session.commit()

    app.dependency_overrides[platform_routes.require_platform_admin] = override_platform_admin
    app.dependency_overrides[platform_db_session] = override_db_session
    monkeypatch.setattr(platform_routes, "send_invitation_email", lambda **_: True)
    return TestClient(app)


def _seed_invitation(db_session) -> OrgInvitation:
    org = Organization(
        id=11,
        name="THDC-IHET",
        type="college",
        domain="thdcihet.ac.in",
        slug="thdc-ihet",
        status="pending_activation",
        plan="free",
    )
    invitation = OrgInvitation(
        org_id=11,
        email="kp22ec06@thdcihet.ac.in",
        role="super_admin",
        token="invite-token",
        invited_by="platform-admin",
        expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
        delivery_status="failed",
    )
    db_session.add_all([org, invitation])
    db_session.commit()
    return invitation


def test_platform_admin_invitations_lists_pending_invites(db_session, monkeypatch):
    invitation = _seed_invitation(db_session)
    client = _client(db_session, monkeypatch)

    response = client.get("/api/platform/admins/invitations")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["pending_invitations"][0]["id"] == invitation.id
    assert payload["pending_invitations"][0]["email"] == "kp22ec06@thdcihet.ac.in"
    assert payload["pending_invitations"][0]["org_name"] == "THDC-IHET"
    assert payload["pending_invitations"][0]["delivery_status"] == "failed"


def test_platform_admin_invitation_resend_records_attempt(db_session, monkeypatch):
    invitation = _seed_invitation(db_session)
    client = _client(db_session, monkeypatch)

    response = client.post(f"/api/platform/admins/invitations/{invitation.id}/resend")

    assert response.status_code == 200
    payload = response.json()["invitation"]
    assert payload["delivery_status"] == "delivered"
    assert payload["resend_count"] == 1
    assert payload["last_resent_at"] is not None


def test_platform_admin_invitation_revoke_removes_from_pending(db_session, monkeypatch):
    invitation = _seed_invitation(db_session)
    client = _client(db_session, monkeypatch)

    response = client.delete(f"/api/platform/admins/invitations/{invitation.id}")

    assert response.status_code == 200
    assert response.json()["invitation"]["revoked_at"] is not None
    db_session.refresh(invitation)
    assert invitation.revoked_at is not None

    pending_response = client.get("/api/platform/admins/invitations")
    assert pending_response.status_code == 200
    assert pending_response.json()["pending_invitations"] == []
