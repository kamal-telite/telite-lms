"""Learning session pipeline verification.

Covers runtime API sequencing, database persistence, dashboard analytics,
and regression cases for module switching and duplicate session termination.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.auth import TokenData, get_current_user
from app.db.engine import db_session
from app.main import create_app
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.course_progress import CourseProgress
from app.models.enrollment import EnrollmentRequest
from app.models.learning_session import LearningSession
from app.models.organization import Organization
from app.models.user import User
from app.repositories.analytics_repo import AnalyticsRepository


def _learner(org_id: int = 77) -> TokenData:
    return TokenData(
        id="learner-ls-1",
        username="learner-ls",
        email="learner-ls@example.com",
        full_name="Learning Session Learner",
        role="learner",
        org_id=org_id,
        category_scope="learning-time",
    )


def _client(db_session) -> TestClient:
    app = create_app()

    def override_user():
        return _learner()

    def override_db_session():
        yield db_session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[db_session] = override_db_session
    return TestClient(app)


def _seed(db_session):
    org = Organization(
        id=77,
        name="Learning Time Org",
        type="company",
        domain="learning-time.test",
        slug="learning-time-org",
        status="active",
    )
    learner = User(
        id="learner-ls-1",
        username="learner-ls",
        email="learner-ls@example.com",
        full_name="Learning Session Learner",
        role="learner",
        org_id=77,
        password_hash="hash",
        avatar_initials="LL",
        gradient_start="#111111",
        gradient_end="#222222",
        category_scope="learning-time",
    )
    course = Course(
        id="course-ls-1",
        name="Learning Time Course",
        slug="learning-time-course",
        description="Verification course",
        category_slug="learning-time",
        status="published",
        org_id=77,
        tier="free",
    )
    module_a = CourseModule(
        id=701,
        course_id=course.id,
        title="Module A",
        module_type="lesson",
        status="published",
        org_id=77,
    )
    module_b = CourseModule(
        id=702,
        course_id=course.id,
        title="Module B",
        module_type="lesson",
        status="published",
        org_id=77,
    )
    enrollment = EnrollmentRequest(
        id="enrollment-ls-1",
        full_name=learner.full_name,
        email=learner.email,
        category_slug="learning-time",
        request_type="course",
        org_id=77,
        status="approved",
        requested_at="2026-07-26T00:00:00",
    )
    db_session.add(org)
    db_session.flush()
    db_session.add_all([learner, course, module_a, module_b, enrollment])
    db_session.commit()
    return {"course": course, "module_a": module_a, "module_b": module_b}


def _start(client: TestClient, course_id: str, module_id: int | None):
    return client.post(
        "/api/v1/learner/learning-sessions/start",
        json={"course_id": course_id, "module_id": module_id},
    )


def _heartbeat(client: TestClient, session_id: int, course_id: str, module_id: int | None, active_seconds: int):
    return client.post(
        "/api/v1/learner/learning-sessions/heartbeat",
        json={
            "session_id": session_id,
            "course_id": course_id,
            "module_id": module_id,
            "active_seconds": active_seconds,
        },
    )


def _end(client: TestClient, session_id: int, reason: str = "ended"):
    return client.post(
        "/api/v1/learner/learning-sessions/end",
        json={"session_id": session_id, "reason": reason},
    )


def test_learning_session_runtime_and_database_verification(db_session):
    """Simulates ~1 minute of active learning with heartbeats and exit."""
    ctx = _seed(db_session)
    client = _client(db_session)
    course_id = ctx["course"].id
    module_id = ctx["module_a"].id
    trace: list[dict] = []

    start_resp = _start(client, course_id, module_id)
    trace.append({"step": "POST /learning-sessions/start", "status": start_resp.status_code, "body": start_resp.json()})
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session"]["id"]
    assert start_resp.json()["session"]["active_seconds"] == 0

    for seconds in (30, 25):
        hb = _heartbeat(client, session_id, course_id, module_id, seconds)
        trace.append(
            {
                "step": "POST /learning-sessions/heartbeat",
                "status": hb.status_code,
                "request_active_seconds": seconds,
                "body": hb.json(),
            }
        )
        assert hb.status_code == 200
        assert hb.json()["session"]["active_seconds"] == sum(x["request_active_seconds"] for x in trace if "request_active_seconds" in x)

    session_row = db_session.execute(
        select(LearningSession).where(LearningSession.id == session_id)
    ).scalar_one()
    progress_row = db_session.execute(
        select(CourseProgress).where(
            CourseProgress.user_id == "learner-ls-1",
            CourseProgress.course_id == course_id,
        )
    ).scalar_one()

    assert session_row.active_seconds == 55
    assert progress_row.time_spent_seconds == 55

    final_hb = _heartbeat(client, session_id, course_id, module_id, 15)
    trace.append(
        {
            "step": "POST /learning-sessions/heartbeat (final before exit)",
            "status": final_hb.status_code,
            "request_active_seconds": 15,
            "body": final_hb.json(),
        }
    )
    assert final_hb.status_code == 200
    assert final_hb.json()["session"]["active_seconds"] == 70

    end_started = time.perf_counter()
    end_resp = _end(client, session_id, "ended")
    end_elapsed_ms = round((time.perf_counter() - end_started) * 1000)
    trace.append({"step": "POST /learning-sessions/end", "status": end_resp.status_code, "elapsed_ms": end_elapsed_ms, "body": end_resp.json()})
    assert end_resp.status_code == 200
    assert end_resp.json()["session"]["status"] == "ended"

    dash_started = time.perf_counter()
    dash_resp = client.get("/dashboard/learner")
    dash_elapsed_ms = round((time.perf_counter() - dash_started) * 1000)
    dashboard = dash_resp.json()
    trace.append(
        {
            "step": "GET /dashboard/learner",
            "status": dash_resp.status_code,
            "elapsed_ms": dash_elapsed_ms,
            "today_time_seconds": dashboard["hero"]["today_time_seconds"],
            "time_spent_hours": dashboard["hero"]["time_spent_hours"],
        }
    )
    assert dash_resp.status_code == 200
    assert dashboard["hero"]["today_time_seconds"] == 70

    total_session_seconds = db_session.execute(
        select(LearningSession.active_seconds).where(LearningSession.user_id == "learner-ls-1")
    ).scalars().all()
    assert sum(total_session_seconds) == 70

    repo_summary = AnalyticsRepository(db_session).get_learner_summary("learner-ls-1")
    assert repo_summary["hero"]["today_time_seconds"] == dashboard["hero"]["today_time_seconds"] == 70

    # Evidence artifact for manual review in CI logs.
    for entry in trace:
        print(f"TRACE {entry}")


def test_exit_sequence_final_heartbeat_commits_before_dashboard(db_session):
    """Ensures dashboard reads time only after the final heartbeat has committed."""
    ctx = _seed(db_session)
    client = _client(db_session)
    course_id = ctx["course"].id
    module_id = ctx["module_a"].id

    session_id = _start(client, course_id, module_id).json()["session"]["id"]
    _heartbeat(client, session_id, course_id, module_id, 40)

    final_started = time.perf_counter()
    final_hb = _heartbeat(client, session_id, course_id, module_id, 20)
    final_elapsed_ms = round((time.perf_counter() - final_started) * 1000)
    assert final_hb.status_code == 200

    _end(client, session_id, "ended")

    dash_started = time.perf_counter()
    dashboard = client.get("/dashboard/learner").json()
    dash_elapsed_ms = round((time.perf_counter() - dash_started) * 1000)

    assert dashboard["hero"]["today_time_seconds"] == 60
    print(
        "ORDERING final_heartbeat_ms=%s dashboard_fetch_ms=%s today_time_seconds=%s"
        % (final_elapsed_ms, dash_elapsed_ms, dashboard["hero"]["today_time_seconds"])
    )


def test_module_switch_records_previous_session(db_session):
    ctx = _seed(db_session)
    client = _client(db_session)
    course_id = ctx["course"].id

    session_one = _start(client, course_id, ctx["module_a"].id).json()["session"]["id"]
    hb_one = _heartbeat(client, session_one, course_id, ctx["module_a"].id, 30)
    assert hb_one.status_code == 200
    end_one = _end(client, session_one, "module_changed")
    assert end_one.status_code == 200
    assert end_one.json()["session"]["end_reason"] == "module_changed"

    session_two = _start(client, course_id, ctx["module_b"].id).json()["session"]["id"]
    hb_two = _heartbeat(client, session_two, course_id, ctx["module_b"].id, 20)
    assert hb_two.status_code == 200

    sessions = db_session.execute(
        select(LearningSession).where(LearningSession.user_id == "learner-ls-1").order_by(LearningSession.id)
    ).scalars().all()
    assert len(sessions) == 2
    assert sessions[0].active_seconds == 30
    assert sessions[0].status == "ended"
    assert sessions[1].active_seconds == 20
    assert sessions[1].status == "active"


def test_duplicate_session_termination_is_idempotent(db_session):
    ctx = _seed(db_session)
    client = _client(db_session)
    course_id = ctx["course"].id
    module_id = ctx["module_a"].id

    session_id = _start(client, course_id, module_id).json()["session"]["id"]
    _heartbeat(client, session_id, course_id, module_id, 10)

    first_end = _end(client, session_id, "ended")
    second_end = _end(client, session_id, "ended")
    assert first_end.status_code == 200
    assert second_end.status_code == 200
    assert first_end.json()["session"]["status"] == "ended"
    assert second_end.json()["session"]["status"] == "ended"

    closed_hb = _heartbeat(client, session_id, course_id, module_id, 5)
    assert closed_hb.status_code == 409


def test_beacon_compatible_heartbeat_payload_is_accepted(db_session):
    """sendBeacon uses the same JSON body as the normal heartbeat POST."""
    ctx = _seed(db_session)
    client = _client(db_session)
    course_id = ctx["course"].id
    module_id = ctx["module_a"].id

    session_id = _start(client, course_id, module_id).json()["session"]["id"]
    beacon_payload = {
        "session_id": session_id,
        "course_id": course_id,
        "module_id": module_id,
        "active_seconds": 18,
    }
    resp = client.post("/api/v1/learner/learning-sessions/heartbeat", json=beacon_payload)
    assert resp.status_code == 200
    assert resp.json()["session"]["active_seconds"] == 18
