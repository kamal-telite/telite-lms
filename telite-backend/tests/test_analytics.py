import pytest
from app.repositories.analytics_repo import AnalyticsRepository
from app.models.organization import Organization
from app.models.user import User
from app.models.course import Course
from app.models.category import Category
from app.models.learner_event import LearnerEvent

@pytest.fixture
def repo(db_session):
    return AnalyticsRepository(db_session)

@pytest.fixture
def seed_data(db_session):
    org = Organization(name="Test Org", domain="test.telite.local", type="company", slug="test-org")
    db_session.add(org)
    db_session.flush()
    
    category = Category(id="test-cat", name="Test Category", slug="test-category", description="", org_id=org.id)
    db_session.add(category)
    db_session.flush()

    course = Course(id="test-course", name="Test Course", slug="test-course", category_slug=category.slug, org_id=org.id)
    db_session.add(course)
    db_session.flush()

    user = User(
        id="test-user", 
        username="testuser", 
        email="test@telite.local", 
        full_name="Test User", 
        role="learner", 
        org_id=org.id,
        avatar_initials="TU",
        gradient_start="blue",
        gradient_end="red",
        password_hash="test"
    )
    db_session.add(user)
    db_session.flush()
    
    return {"org": org, "category": category, "course": course, "user": user}

def test_get_global_kpis(db_session, repo, seed_data):
    org = seed_data["org"]
    course = seed_data["course"]
    user = seed_data["user"]

    event1 = LearnerEvent(user_id=str(user.id), course_id=str(course.id), event_type="COURSE_COMPLETED", payload_json={}, org_id=org.id)
    db_session.add(event1)
    db_session.flush()

    kpis = repo.get_global_kpis(org.id)
    assert "total_learners" in kpis["kpis"]
    assert "total_completions" in kpis["kpis"]
    assert kpis["kpis"]["total_completions"] == 1

def test_get_category_metrics(repo, seed_data):
    metrics = repo.get_category_metrics(seed_data["category"].slug, org_id=seed_data["org"].id)
    assert "courses" in metrics
    assert len(metrics["courses"]) == 1
    assert metrics["courses"][0]["name"] == "Test Course"

def test_get_learner_summary(db_session, repo, seed_data):
    org = seed_data["org"]
    course = seed_data["course"]
    user = seed_data["user"]

    event = LearnerEvent(user_id=str(user.id), course_id=str(course.id), event_type="QUIZ_SUBMITTED", payload_json={}, org_id=org.id)
    db_session.add(event)
    db_session.flush()

    summary = repo.get_learner_summary(str(user.id))
    assert "quizzes_submitted" in summary["stats"]
    assert summary["stats"]["quizzes_submitted"] == 1
