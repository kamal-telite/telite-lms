"""Tests for Progression Rule Engine functionality."""

import pytest
from sqlalchemy.orm import Session

from app.models.progression_rule import ProgressionRule
from app.models.course_module import CourseModule
from app.models.course_section import CourseSection
from app.models.module_progress import ModuleProgress
from app.repositories.progression_rule_repo import ProgressionRuleRepository
from app.services.progression_rule_engine import ProgressionRuleEngine


def test_create_rule(db_session: Session):
    """Test creating a progression rule."""
    repo = ProgressionRuleRepository(db_session)
    
    rule = repo.create_rule(
        target_type="module",
        target_id=1,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=1,
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
    repo = ProgressionRuleRepository(db_session)
    
    # Create a rule
    repo.create_rule(
        target_type="module",
        target_id=1,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=1,
    )
    
    # Retrieve rules
    rules = repo.get_rules_for_target("module", 1, 1)
    
    assert len(rules) == 1
    assert rules[0].target_type == "module"
    assert rules[0].target_id == 1
    
    db_session.rollback()


def test_update_rule(db_session: Session):
    """Test updating a progression rule."""
    repo = ProgressionRuleRepository(db_session)
    
    # Create a rule
    rule = repo.create_rule(
        target_type="module",
        target_id=1,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=1,
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
    repo = ProgressionRuleRepository(db_session)
    
    # Create a rule
    rule = repo.create_rule(
        target_type="module",
        target_id=1,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=1,
    )
    
    # Delete the rule
    repo.delete_rule(rule)
    
    # Verify it's soft deleted
    assert rule.deleted_at is not None
    
    # Verify it's not returned in active queries
    rules = repo.get_rules_for_target("module", 1, 1)
    assert len(rules) == 0
    
    db_session.rollback()


def test_rule_engine_no_rules(db_session: Session):
    """Test rule engine when no rules are configured."""
    engine = ProgressionRuleEngine(db_session)
    
    result = engine.validate_access(
        user_id="test_user",
        target_type="module",
        target_id=1,
        org_id=1,
    )
    
    assert result.allowed is True
    assert result.reason is None


def test_rule_engine_unknown_rule_type(db_session: Session):
    """Test rule engine with unknown rule type (should not block)."""
    # Create a rule with unknown type
    rule = ProgressionRule(
        target_type="module",
        target_id=1,
        rule_type="unknown_rule_type",
        rule_value={},
        org_id=1,
        is_active=True,
    )
    db_session.add(rule)
    db_session.flush()
    
    engine = ProgressionRuleEngine(db_session)
    
    result = engine.validate_access(
        user_id="test_user",
        target_type="module",
        target_id=1,
        org_id=1,
    )
    
    # Unknown rule types should not block access
    assert result.allowed is True
    
    db_session.rollback()


def test_previous_module_completed_evaluator_first_module(db_session: Session):
    """Test previous_module_completed evaluator when there's no previous module."""
    # Create a module with sort_order 0 (first module)
    module = CourseModule(
        id=1,
        course_id="test_course",
        section_id=1,
        title="First Module",
        module_type="lesson",
        sort_order=0,
        org_id=1,
    )
    db_session.add(module)
    db_session.flush()
    
    # Create a rule
    rule = ProgressionRule(
        target_type="module",
        target_id=1,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=1,
        is_active=True,
    )
    db_session.add(rule)
    db_session.flush()
    
    engine = ProgressionRuleEngine(db_session)
    
    result = engine.validate_access(
        user_id="test_user",
        target_type="module",
        target_id=1,
        org_id=1,
    )
    
    # First module should be accessible
    assert result.allowed is True
    
    db_session.rollback()


def test_previous_module_completed_evaluator_not_completed(db_session: Session):
    """Test previous_module_completed evaluator when previous module is not completed."""
    # Create two modules
    module1 = CourseModule(
        id=1,
        course_id="test_course",
        section_id=1,
        title="First Module",
        module_type="lesson",
        sort_order=0,
        org_id=1,
    )
    module2 = CourseModule(
        id=2,
        course_id="test_course",
        section_id=1,
        title="Second Module",
        module_type="lesson",
        sort_order=1,
        org_id=1,
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
        org_id=1,
        is_active=True,
    )
    db_session.add(rule)
    db_session.flush()
    
    engine = ProgressionRuleEngine(db_session)
    
    result = engine.validate_access(
        user_id="test_user",
        target_type="module",
        target_id=2,
        org_id=1,
    )
    
    # Should be denied because first module is not completed
    assert result.allowed is False
    assert "Complete" in result.reason
    
    db_session.rollback()


def test_previous_module_completed_evaluator_completed(db_session: Session):
    """Test previous_module_completed evaluator when previous module is completed."""
    # Create two modules
    module1 = CourseModule(
        id=1,
        course_id="test_course",
        section_id=1,
        title="First Module",
        module_type="lesson",
        sort_order=0,
        org_id=1,
    )
    module2 = CourseModule(
        id=2,
        course_id="test_course",
        section_id=1,
        title="Second Module",
        module_type="lesson",
        sort_order=1,
        org_id=1,
    )
    db_session.add(module1)
    db_session.add(module2)
    db_session.flush()
    
    # Mark first module as completed
    progress = ModuleProgress(
        user_id="test_user",
        module_id=1,
        org_id=1,
        status="completed",
        completion_pct=100,
    )
    db_session.add(progress)
    db_session.flush()
    
    # Create a rule for the second module
    rule = ProgressionRule(
        target_type="module",
        target_id=2,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=1,
        is_active=True,
    )
    db_session.add(rule)
    db_session.flush()
    
    engine = ProgressionRuleEngine(db_session)
    
    result = engine.validate_access(
        user_id="test_user",
        target_type="module",
        target_id=2,
        org_id=1,
    )
    
    # Should be allowed because first module is completed
    assert result.allowed is True
    
    db_session.rollback()


def test_get_all_rules_for_course(db_session: Session):
    """Test getting all rules for a course."""
    repo = ProgressionRuleRepository(db_session)
    
    # Create modules and sections for a course
    module1 = CourseModule(
        id=1,
        course_id="test_course",
        section_id=1,
        title="Module 1",
        module_type="lesson",
        sort_order=0,
        org_id=1,
    )
    section1 = CourseSection(
        id=1,
        course_id="test_course",
        title="Section 1",
        sort_order=0,
        org_id=1,
    )
    db_session.add(module1)
    db_session.add(section1)
    db_session.flush()
    
    # Create rules for both
    repo.create_rule(
        target_type="module",
        target_id=1,
        rule_type="previous_module_completed",
        rule_value={},
        org_id=1,
    )
    repo.create_rule(
        target_type="section",
        target_id=1,
        rule_type="previous_section_completed",
        rule_value={},
        org_id=1,
    )
    
    # Get all rules for course
    rules = repo.get_all_rules_for_course("test_course", 1)
    
    assert len(rules) == 2
    
    db_session.rollback()
