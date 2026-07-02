"""Repository for progression rule data access."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.progression_rule import ProgressionRule
from app.repositories.base_repo import BaseRepository


class ProgressionRuleRepository(BaseRepository[ProgressionRule]):
    """Repository for managing progression rules."""

    model = ProgressionRule

    def get_rules_for_target(
        self, target_type: str, target_id: int, org_id: int
    ) -> Sequence[ProgressionRule]:
        """Get all active rules for a specific target.

        Args:
            target_type: The target type (module or section)
            target_id: The target ID
            org_id: The organization ID

        Returns:
            List of active progression rules
        """
        stmt = select(ProgressionRule).where(
            ProgressionRule.target_type == target_type,
            ProgressionRule.target_id == target_id,
            ProgressionRule.org_id == org_id,
            ProgressionRule.is_active == True,
            ProgressionRule.deleted_at.is_(None),
        )
        return self.session.execute(stmt).scalars().all()

    def get_all_rules_for_course(
        self, course_id: str, org_id: int
    ) -> Sequence[ProgressionRule]:
        """Get all active rules for a course (both modules and sections).

        Args:
            course_id: The course ID
            org_id: The organization ID

        Returns:
            List of active progression rules for the course
        """
        from app.models.course_module import CourseModule
        from app.models.course_section import CourseSection

        # Get all module IDs for the course
        module_ids = (
            self.session.execute(
                select(CourseModule.id)
                .where(
                    CourseModule.course_id == course_id,
                    CourseModule.org_id == org_id,
                    CourseModule.deleted_at.is_(None),
                )
            )
            .scalars()
            .all()
        )

        # Get all section IDs for the course
        section_ids = (
            self.session.execute(
                select(CourseSection.id)
                .where(
                    CourseSection.course_id == course_id,
                    CourseSection.org_id == org_id,
                    CourseSection.deleted_at.is_(None),
                )
            )
            .scalars()
            .all()
        )

        # Get rules for all modules and sections
        all_rules = []
        if module_ids:
            module_rules = (
                self.session.execute(
                    select(ProgressionRule)
                    .where(
                        ProgressionRule.target_type == "module",
                        ProgressionRule.target_id.in_(module_ids),
                        ProgressionRule.org_id == org_id,
                        ProgressionRule.is_active == True,
                        ProgressionRule.deleted_at.is_(None),
                    )
                )
                .scalars()
                .all()
            )
            all_rules.extend(module_rules)

        if section_ids:
            section_rules = (
                self.session.execute(
                    select(ProgressionRule)
                    .where(
                        ProgressionRule.target_type == "section",
                        ProgressionRule.target_id.in_(section_ids),
                        ProgressionRule.org_id == org_id,
                        ProgressionRule.is_active == True,
                        ProgressionRule.deleted_at.is_(None),
                    )
                )
                .scalars()
                .all()
            )
            all_rules.extend(section_rules)

        return all_rules

    def create_rule(
        self,
        *,
        target_type: str,
        target_id: int,
        rule_type: str,
        rule_value: dict,
        org_id: int,
        created_by: str | None = None,
    ) -> ProgressionRule:
        """Create a new progression rule.

        Args:
            target_type: The target type (module or section)
            target_id: The target ID
            rule_type: The rule type
            rule_value: Rule-specific configuration
            org_id: The organization ID
            created_by: User ID who created the rule

        Returns:
            The created progression rule
        """
        rule = ProgressionRule(
            target_type=target_type,
            target_id=target_id,
            rule_type=rule_type,
            rule_value=rule_value,
            org_id=org_id,
            created_by=created_by,
            is_active=True,
        )
        self.session.add(rule)
        self.session.flush()
        return rule

    def update_rule(
        self,
        rule: ProgressionRule,
        *,
        rule_type: str | None = None,
        rule_value: dict | None = None,
        is_active: bool | None = None,
        updated_by: str | None = None,
    ) -> ProgressionRule:
        """Update an existing progression rule.

        Args:
            rule: The rule to update
            rule_type: New rule type (optional)
            rule_value: New rule value (optional)
            is_active: New active status (optional)
            updated_by: User ID who updated the rule

        Returns:
            The updated progression rule
        """
        if rule_type is not None:
            rule.rule_type = rule_type
        if rule_value is not None:
            rule.rule_value = rule_value
        if is_active is not None:
            rule.is_active = is_active
        if updated_by is not None:
            rule.updated_by = updated_by
        self.session.flush()
        return rule

    def delete_rule(self, rule: ProgressionRule) -> None:
        """Soft delete a progression rule.

        Args:
            rule: The rule to delete
        """
        from datetime import datetime, timezone

        rule.deleted_at = datetime.now(timezone.utc)
        self.session.flush()
