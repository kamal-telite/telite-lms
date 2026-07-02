import os

from app.services import email


def test_build_frontend_url_uses_app_url_and_encodes_params(monkeypatch):
    monkeypatch.setattr(email, "APP_URL", "http://localhost:3000")
    url = email._build_frontend_url("set-password", {"token": "abc 123"})

    assert url == "http://localhost:3000/set-password?token=abc+123"


def test_send_invitation_email_prints_frontend_link_when_smtp_unconfigured(monkeypatch, capsys):
    monkeypatch.setattr(email, "APP_URL", "http://localhost:3000")
    monkeypatch.setattr(email, "SMTP_USER", "")
    monkeypatch.setattr(email, "SMTP_PASSWORD", "")

    result = email.send_invitation_email(
        to_email="learner@example.com",
        org_name="Example Org",
        org_domain="example.org",
        role="learner",
        token="invite-token",
        expires_at="2026-12-31T23:59:59Z",
    )

    captured = capsys.readouterr()
    assert result is False
    assert "http://localhost:3000/set-password?token=invite-token" in captured.out


def test_send_password_reset_email_prints_frontend_link_when_smtp_unconfigured(monkeypatch, capsys):
    monkeypatch.setattr(email, "APP_URL", "http://localhost:3000")
    monkeypatch.setattr(email, "SMTP_USER", "")
    monkeypatch.setattr(email, "SMTP_PASSWORD", "")

    result = email.send_password_reset_email(
        to_email="user@example.com",
        name="Test User",
        token="reset-token",
        expires_at="2026-12-31T23:59:59Z",
    )

    captured = capsys.readouterr()
    assert result is False
    assert "http://localhost:3000/reset-password?token=reset-token" in captured.out
