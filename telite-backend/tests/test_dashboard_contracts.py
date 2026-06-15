"""Phase A.5 dashboard API contract verification.

These tests run against a live backend URL and validate minimal response
contracts for role dashboards. They are opt-in so routine unit tests do not
depend on Docker.

Run with:
    $env:TELITE_RUN_LIVE_CONTRACT_TESTS="1"
    pytest tests/test_dashboard_contracts.py
"""

from __future__ import annotations

import os
from typing import Any

import pytest
import requests
from pydantic import BaseModel, Field


pytestmark = pytest.mark.skipif(
    os.getenv("TELITE_RUN_LIVE_CONTRACT_TESTS") != "1",
    reason="Set TELITE_RUN_LIVE_CONTRACT_TESTS=1 to run live dashboard contract tests.",
)


BASE_URL = os.getenv("TELITE_CONTRACT_BASE_URL") or f"http://localhost:{os.getenv('BACKEND_PORT', '8001')}"


class PlatformOverviewResponse(BaseModel):
    total_orgs: int = Field(ge=0)
    total_users: int = Field(ge=0)
    active_sessions: int = Field(ge=0)
    recent_activity: list[dict[str, Any]]


class SuperAdminDashboardResponse(BaseModel):
    kpis: dict[str, Any]
    categories: list[dict[str, Any]] = []
    courses: list[dict[str, Any]] = []
    learners: dict[str, Any]


class CategoryDashboardResponse(BaseModel):
    category: dict[str, Any]
    kpis: dict[str, Any]
    courses: list[dict[str, Any]]
    learners: dict[str, Any]


class LearnerDashboardResponse(BaseModel):
    profile: dict[str, Any]
    hero: dict[str, Any]
    stats: dict[str, Any]
    courses: list[dict[str, Any]] = []


def _login(username: str, password: str) -> str:
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": username, "password": password},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _get(path: str, token: str) -> dict[str, Any]:
    response = requests.get(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def test_platform_overview_contract():
    token = _login(
        os.getenv("TELITE_PLATFORM_TEST_USER", "globaladmin"),
        os.getenv("TELITE_PLATFORM_TEST_PASSWORD", "GlobalAdmin@1234"),
    )
    payload = _get("/api/platform/analytics/overview", token)
    PlatformOverviewResponse.model_validate(payload)


def test_super_admin_dashboard_contract():
    token = _login(
        os.getenv("TELITE_SUPER_ADMIN_TEST_USER", "kt_superadmin"),
        os.getenv("TELITE_SUPER_ADMIN_TEST_PASSWORD", "KTSuper@1234"),
    )
    payload = _get("/dashboard/super-admin", token)
    SuperAdminDashboardResponse.model_validate(payload)


def test_category_admin_dashboard_contract():
    token = _login(
        os.getenv("TELITE_CATEGORY_ADMIN_TEST_USER", "kt_category_admin"),
        os.getenv("TELITE_CATEGORY_ADMIN_TEST_PASSWORD", "KTCategory@1234"),
    )
    payload = _get("/dashboard/categories/kt-foundations/admin", token)
    CategoryDashboardResponse.model_validate(payload)


def test_learner_dashboard_contract():
    token = _login(
        os.getenv("TELITE_LEARNER_TEST_USER", "kt_learner_1"),
        os.getenv("TELITE_LEARNER_TEST_PASSWORD", "KTLearner@1234"),
    )
    payload = _get("/dashboard/learner", token)
    LearnerDashboardResponse.model_validate(payload)
    assert payload["hero"]["current_course"]["id"]
    assert payload["hero"]["current_course"]["name"]
    assert payload["courses"]
    assert all(course.get("id") for course in payload["courses"])
    assert all(course.get("name") for course in payload["courses"])
    assert all("completion_pct" in course for course in payload["courses"])
