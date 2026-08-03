"""Tests for Progression Rule Engine functionality."""

import pytest
import uuid
from sqlalchemy.orm import Session

from app.models.progression_rule import ProgressionRule
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.course_section import CourseSection
from app.models.module_progress import ModuleProgress
from app.models.section_progress import SectionProgress
from app.models.organization import Organization
from app.repositories.progression_rule_repo import ProgressionRuleRepository
from app.services.progression_rule_engine import ProgressionRuleEngine


def _setup_env(db_session: Session) -> int:
    from app.models.user import User
    org = Organization(name=f"Test Org {uuid.uuid4()}", type="company", domain=f"test.org-{uuid.uuid4()}", slug=f"test-org-{uuid.uuid4()}")
    db_session.add(org)
    db_session.flush()
    
    user = User(
        id="test_user", 
        org_id=org.id, 
        email=f"test{uuid.uuid4()}@example.com", 
        username=f"testuser{uuid.uuid4().hex[:8]}",
        full_name="Test User",
        role="learner",
        password_hash="dummy_hash",
        avatar_initials="TU",
        gradient_start="#000000",
        gradient_end="#ffffff"
    )
    db_session.add(user)
    db_session.flush()
    
    course = Course(id="test_course", name="Test Course", category_slug="test", slug="test-course", org_id=org.id)
    db_session.add(course)
    db_session.flush()
    
    section = CourseSection(id=1, course_id="test_course", title="Default Section", sort_order=0, org_id=org.id)
    db_session.add(section)
    db_session.flush()
    
    return org.id


def test_create_rule(db_session: Session):
    """Test creating a progression rule."""
    org_id = _setup_env(db_session)
    repo = ProgressionRuleRepository(db_session)
    
    rule = repo.create_rule(
        target_type="module",
        target_id=1,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=org_id,
        created_by="test_user",
    )
    
    assert rule.id is not None
    assert rule.target_type == "module"
    assert rule.target_id == 1
    assert rule.rule_type == "previous_module_completed"
    assert rule.is_active is True
    assert rule.org_id == 1
    
    db_session.rollback()


def test_get_rules_for_target(db_session: Session):
    """Test retrieving rules for a specific target."""
    org_id = _setup_env(db_session)
    repo = ProgressionRuleRepository(db_session)
    
    # Create a rule
    repo.create_rule(
        target_type="module",
        target_id=1,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=org_id,
    )
    
    # Retrieve rules
    rules = repo.get_rules_for_target("module", 1, org_id)
    
    assert len(rules) == 1
    assert rules[0].target_type == "module"
    assert rules[0].target_id == 1
    
    db_session.rollback()


def test_update_rule(db_session: Session):
    """Test updating a progression rule."""
    org_id = _setup_env(db_session)
    repo = ProgressionRuleRepository(db_session)
    
    # Create a rule
    rule = repo.create_rule(
        target_type="module",
        target_id=1,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=org_id,
    )
    
    # Update the rule
    updated_rule = repo.update_rule(
        rule,
        is_active=False,
        updated_by="test_user",
    )
    
    assert updated_rule.is_active is False
    
    db_session.rollback()


def test_delete_rule(db_session: Session):
    """Test soft deleting a progression rule."""
    org_id = _setup_env(db_session)
    repo = ProgressionRuleRepository(db_session)
    
    # Create a rule
    rule = repo.create_rule(
        target_type="module",
        target_id=1,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=org_id,
    )
    
    # Delete the rule
    repo.delete_rule(rule)
    
    # Verify it's soft deleted
    assert rule.deleted_at is not None
    
    # Verify it's not returned in active queries
    rules = repo.get_rules_for_target("module", 1, org_id)
    assert len(rules) == 0
    
    db_session.rollback()


def test_rule_engine_no_rules(db_session: Session):
    """Test rule engine when no rules are configured."""
    org_id = _setup_env(db_session)
    engine = ProgressionRuleEngine(db_session)
    
    result = engine.validate_access(
        user_id="test_user",
        target_type="module",
        target_id=1,
        org_id=org_id,
    )
    
    assert result.allowed is True
    assert result.reason is None


def test_rule_engine_unknown_rule_type(db_session: Session):
    """Test rule engine with unknown rule type (should not block)."""
    org_id = _setup_env(db_session)
    # Create a rule with unknown type
    rule = ProgressionRule(
        target_type="module",
        target_id=1,
        rule_type="unknown_rule_type",
        rule_value={},
        org_id=org_id,
        is_active=True,
    )
    db_session.add(rule)
    db_session.flush()
    
    engine = ProgressionRuleEngine(db_session)
    
    result = engine.validate_access(
        user_id="test_user",
        target_type="module",
        target_id=1,
        org_id=org_id,
    )
    
    # Unknown rule types should not block access
    assert result.allowed is True
    
    db_session.rollback()


def test_previous_module_completed_evaluator_first_module(db_session: Session):
    """Test previous_module_completed evaluator when there's no previous module."""
    org_id = _setup_env(db_session)
    
    # Create a module with sort_order 0 (first module)
    module = CourseModule(
        id=1,
        course_id="test_course",
        section_id=1,
        title="First Module",
        module_type="lesson",
        sort_order=0,
        org_id=org_id,
    )
    db_session.add(module)
    db_session.flush()
    
    # Create a rule
    rule = ProgressionRule(
        target_type="module",
        target_id=1,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=org_id,
        is_active=True,
    )
    db_session.add(rule)
    db_session.flush()
    
    engine = ProgressionRuleEngine(db_session)
    
    result = engine.validate_access(
        user_id="test_user",
        target_type="module",
        target_id=1,
        org_id=org_id,
    )
    
    # First module should be accessible
    assert result.allowed is True
    
    db_session.rollback()


def test_previous_module_completed_evaluator_not_completed(db_session: Session):
    """Test previous_module_completed evaluator when previous module is not completed."""
    org_id = _setup_env(db_session)
    
    # Create two modules
    module1 = CourseModule(
        id=1,
        course_id="test_course",
        section_id=1,
        title="First Module",
        module_type="lesson",
        sort_order=0,
        org_id=org_id,
    )
    module2 = CourseModule(
        id=2,
        course_id="test_course",
        section_id=1,
        title="Second Module",
        module_type="lesson",
        sort_order=1,
        org_id=org_id,
    )
    db_session.add(module1)
    db_session.add(module2)
    db_session.flush()
    
    # Create a rule for the second module
    rule = ProgressionRule(
        target_type="module",
        target_id=2,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=org_id,
        is_active=True,
    )
    db_session.add(rule)
    db_session.flush()
    
    engine = ProgressionRuleEngine(db_session)
    
    result = engine.validate_access(
        user_id="test_user",
        target_type="module",
        target_id=2,
        org_id=org_id,
    )
    
    # Should be denied because first module is not completed
    assert result.allowed is False
    assert "Complete" in result.reason
    
    db_session.rollback()


def test_previous_module_completed_evaluator_completed(db_session: Session):
    """Test previous_module_completed evaluator when previous module is completed."""
    org_id = _setup_env(db_session)
    
    # Create two modules
    module1 = CourseModule(
        id=1,
        course_id="test_course",
        section_id=1,
        title="First Module",
        module_type="lesson",
        sort_order=0,
        org_id=org_id,
    )
    module2 = CourseModule(
        id=2,
        course_id="test_course",
        section_id=1,
        title="Second Module",
        module_type="lesson",
        sort_order=1,
        org_id=org_id,
    )
    db_session.add(module1)
    db_session.add(module2)
    db_session.flush()
    
    # Mark first module as completed
    progress = ModuleProgress(
        user_id="test_user",
        module_id=1,
        org_id=org_id,
        status="completed",
    )
    db_session.add(progress)
    db_session.flush()
    
    # Create a rule for the second module
    rule = ProgressionRule(
        target_type="module",
        target_id=2,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=org_id,
        is_active=True,
    )
    db_session.add(rule)
    db_session.flush()
    
    engine = ProgressionRuleEngine(db_session)
    
    result = engine.validate_access(
        user_id="test_user",
        target_type="module",
        target_id=2,
        org_id=org_id,
    )
    
    # Should be allowed because first module is completed
    assert result.allowed is True
    
    db_session.rollback()


def test_get_all_rules_for_course(db_session: Session):
    """Test getting all rules for a course."""
    org_id = _setup_env(db_session)
    repo = ProgressionRuleRepository(db_session)

    # Create modules and sections for a course
    module1 = CourseModule(
        id=1,
        course_id="test_course",
        section_id=1,
        title="Module 1",
        module_type="lesson",
        sort_order=0,
        org_id=org_id,
    )
    db_session.add(module1)
    db_session.flush()
    
    # Create rules for both
    repo.create_rule(
        target_type="module",
        target_id=1,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=org_id,
    )
    repo.create_rule(
        target_type="section",
        target_id=1,
        rule_type="previous_section_completed",
        rule_value={},
        org_id=org_id,
    )
    
    # Get all rules for course
    rules = repo.get_all_rules_for_course("test_course", org_id)
    
    assert len(rules) == 2
    
    db_session.rollback()


def test_module_access_evaluates_parent_section_rules(db_session: Session):
    """A module inside a locked section must be denied by the section rule."""
    org_id = _setup_env(db_session)

    section2 = CourseSection(
        id=2,
        course_id="test_course",
        title="Locked Section",
        sort_order=1,
        org_id=org_id,
    )
    previous_module = CourseModule(
        id=1,
        course_id="test_course",
        section_id=1,
        title="Unfinished Previous Module",
        module_type="lesson",
        sort_order=0,
        org_id=org_id,
    )
    module = CourseModule(
        id=2,
        course_id="test_course",
        section_id=2,
        title="Locked Section Module",
        module_type="lesson",
        sort_order=0,
        org_id=org_id,
    )
    rule = ProgressionRule(
        target_type="section",
        target_id=2,
        rule_type="previous_section_completed",
        rule_value={},
        org_id=org_id,
        is_active=True,
    )
    db_session.add(section2)
    db_session.flush()
    db_session.add_all([previous_module, module, rule])
    db_session.flush()

    result = ProgressionRuleEngine(db_session).validate_access(
        user_id="test_user",
        target_type="module",
        target_id=2,
        org_id=org_id,
    )

    assert result.allowed is False
    assert "Complete" in result.reason

    db_session.rollback()


def test_minimum_section_time_rule_allows_child_module_after_previous_section_time_met(db_session: Session):
    """Section delay rules configured on a section must unlock its child module."""
    org_id = _setup_env(db_session)

    section1_module = CourseModule(
        id=1,
        course_id="test_course",
        section_id=1,
        title="First Section Module",
        module_type="lesson",
        sort_order=0,
        org_id=org_id,
    )
    section2 = CourseSection(
        id=2,
        course_id="test_course",
        title="Delayed Section",
        sort_order=1,
        org_id=org_id,
    )
    section2_module = CourseModule(
        id=2,
        course_id="test_course",
        section_id=2,
        title="Delayed Section Module",
        module_type="lesson",
        sort_order=0,
        org_id=org_id,
    )
    db_session.add(section2)
    db_session.flush()
    db_session.add_all([section1_module, section2_module])
    db_session.flush()

    previous_section = db_session.query(CourseSection).filter(CourseSection.id == 1).first()
    previous_section.minimum_time_seconds = 120
    db_session.add_all([
        ModuleProgress(user_id="test_user", module_id=1, org_id=org_id, status="completed"),
        SectionProgress(
            user_id="test_user",
            section_id=1,
            org_id=org_id,
            status="completed",
            completion_percentage=100.0,
            time_spent_seconds=120,
        ),
        ProgressionRule(
            target_type="section",
            target_id=2,
            rule_type="previous_section_completed",
            rule_value={},
            org_id=org_id,
            is_active=True,
        ),
        ProgressionRule(
            target_type="section",
            target_id=2,
            rule_type="minimum_section_time",
            rule_value={},
            org_id=org_id,
            is_active=True,
        ),
    ])
    db_session.flush()

    result = ProgressionRuleEngine(db_session).validate_access(
        user_id="test_user",
        target_type="module",
        target_id=2,
        org_id=org_id,
    )

    assert result.allowed is True

    db_session.rollback()
