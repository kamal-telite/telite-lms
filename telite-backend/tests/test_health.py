"""Smoke tests for API health and permission resolution."""

from __future__ import annotations

from app.core.permissions import resolve_permissions


def test_liveness(client):
    response = client.get("/health/liveness")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["api"] == "running"


def test_readiness(client):
    response = client.get("/health/readiness")
    assert response.status_code == 200
    payload = response.json()
    assert payload["checks"]["database"] == "ok"
    assert payload["checks"]["redis"] in ("ok", "skipped")


def test_metrics(client):
    client.get("/health/liveness")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "telite_http_requests_total" in response.text


def test_resolve_permissions_learner_defaults():
    permissions = resolve_permissions("learner", False, None, None, None)
    assert "learner.view_courses" in permissions
    assert "authoring.publish" not in permissions


def test_resolve_permissions_platform_admin():
    permissions = resolve_permissions("learner", True, None, None, None)
    assert "platform.manage_orgs" in permissions
