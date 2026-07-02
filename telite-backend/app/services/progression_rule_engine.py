"""Progression Rule Engine for module/section access control.

This service provides an extensible architecture for evaluating learner progression rules.
New rule types can be added by implementing the RuleEvaluator interface.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.models.progression_rule import ProgressionRule
from app.models.module_progress import ModuleProgress
from app.models.course_module import CourseModule
from app.models.course_section import CourseSection

logger = logging.getLogger("telite.rule_engine")


@dataclass(frozen=True)
class RuleEvaluationContext:
    """Context provided to rule evaluators."""
    user_id: str
    target_type: str
    target_id: int
    org_id: int
    session: Session


@dataclass(frozen=True)
class RuleEvaluationResult:
    """Result of a single rule evaluation."""
    rule_type: str
    passed: bool
    reason: str | None = None


@dataclass(frozen=True)
class AccessValidationResult:
    """Result of access validation for a learning item."""
    allowed: bool
    reason: str | None = None
    failed_rules: list[RuleEvaluationResult] | None = None


class RuleEvaluator(ABC):
    """Abstract base class for rule evaluators.

    Each rule type implements this interface to provide custom evaluation logic.
    """

    @abstractmethod
    def get_rule_type(self) -> str:
        """Return the rule type identifier (e.g., 'previous_module_completed')."""
        pass

    @abstractmethod
    def evaluate(
        self, rule: ProgressionRule, context: RuleEvaluationContext
    ) -> RuleEvaluationResult:
        """Evaluate whether the rule is satisfied.

        Args:
            rule: The progression rule to evaluate
            context: Evaluation context with user and target information

        Returns:
            RuleEvaluationResult indicating if the rule passed and why
        """
        pass


class PreviousModuleCompletedEvaluator(RuleEvaluator):
    """Evaluates whether the previous module in sort order is completed."""

    def get_rule_type(self) -> str:
        return "previous_module_completed"

    def evaluate(
        self, rule: ProgressionRule, context: RuleEvaluationContext
    ) -> RuleEvaluationResult:
        logger.info(
            f"Evaluating previous_module_completed rule {rule.id} for user {context.user_id}, target {context.target_type}:{context.target_id}"
        )
        try:
            # Get the current module
            current_module = context.session.query(CourseModule).filter(
                CourseModule.id == context.target_id,
                CourseModule.org_id == context.org_id,
                CourseModule.deleted_at.is_(None),
            ).first()

            if not current_module:
                logger.warning(f"Module {context.target_id} not found for rule evaluation")
                return RuleEvaluationResult(
                    rule_type=self.get_rule_type(),
                    passed=False,
                    reason="Module not found",
                )

            # Find the previous module by sort order
            previous_module = (
                context.session.query(CourseModule)
                .filter(
                    CourseModule.course_id == current_module.course_id,
                    CourseModule.org_id == context.org_id,
                    CourseModule.deleted_at.is_(None),
                    CourseModule.sort_order < current_module.sort_order,
                )
                .order_by(CourseModule.sort_order.desc())
                .first()
            )

            if not previous_module:
                # No previous module exists - allow access (first module)
                logger.info(f"No previous module found for {current_module.id}, allowing access")
                return RuleEvaluationResult(
                    rule_type=self.get_rule_type(),
                    passed=True,
                    reason=None,
                )

            # Check if previous module is completed
            previous_progress = context.session.query(ModuleProgress).filter(
                ModuleProgress.user_id == context.user_id,
                ModuleProgress.module_id == previous_module.id,
                ModuleProgress.org_id == context.org_id,
            ).first()

            if not previous_progress or previous_progress.status != "completed":
                logger.info(
                    f"Previous module {previous_module.id} not completed by user {context.user_id}"
                )
                return RuleEvaluationResult(
                    rule_type=self.get_rule_type(),
                    passed=False,
                    reason=f"Complete '{previous_module.title}' first",
                )

            logger.info(f"Previous module {previous_module.id} completed, allowing access")
            return RuleEvaluationResult(
                rule_type=self.get_rule_type(),
                passed=True,
                reason=None,
            )
        except Exception as e:
            logger.error(f"Error evaluating previous_module_completed rule {rule.id}: {e}", exc_info=True)
            return RuleEvaluationResult(
                rule_type=self.get_rule_type(),
                passed=False,
                reason="Error evaluating rule",
            )


class PreviousSectionCompletedEvaluator(RuleEvaluator):
    """Evaluates whether the previous section in sort order is completed.

    A section is considered completed when all its required modules are completed.
    """

    def get_rule_type(self) -> str:
        return "previous_section_completed"

    def evaluate(
        self, rule: ProgressionRule, context: RuleEvaluationContext
    ) -> RuleEvaluationResult:
        logger.info(
            f"Evaluating previous_section_completed rule {rule.id} for user {context.user_id}, target {context.target_type}:{context.target_id}"
        )
        try:
            # Get the current section
            current_section = context.session.query(CourseSection).filter(
                CourseSection.id == context.target_id,
                CourseSection.org_id == context.org_id,
                CourseSection.deleted_at.is_(None),
            ).first()

            if not current_section:
                logger.warning(f"Section {context.target_id} not found for rule evaluation")
                return RuleEvaluationResult(
                    rule_type=self.get_rule_type(),
                    passed=False,
                    reason="Section not found",
                )

            # Find the previous section by sort order
            previous_section = (
                context.session.query(CourseSection)
                .filter(
                    CourseSection.course_id == current_section.course_id,
                    CourseSection.org_id == context.org_id,
                    CourseSection.deleted_at.is_(None),
                    CourseSection.sort_order < current_section.sort_order,
                )
                .order_by(CourseSection.sort_order.desc())
                .first()
            )

            if not previous_section:
                # No previous section exists - allow access (first section)
                logger.info(f"No previous section found for {current_section.id}, allowing access")
                return RuleEvaluationResult(
                    rule_type=self.get_rule_type(),
                    passed=True,
                    reason=None,
                )

            # Get all modules in the previous section
            previous_modules = (
                context.session.query(CourseModule)
                .filter(
                    CourseModule.section_id == previous_section.id,
                    CourseModule.org_id == context.org_id,
                    CourseModule.deleted_at.is_(None),
                )
                .all()
            )

            if not previous_modules:
                # Previous section has no modules - consider it complete
                logger.info(f"Previous section {previous_section.id} has no modules, allowing access")
                return RuleEvaluationResult(
                    rule_type=self.get_rule_type(),
                    passed=True,
                    reason=None,
                )

            # Check if all modules in previous section are completed
            for module in previous_modules:
                module_progress = context.session.query(ModuleProgress).filter(
                    ModuleProgress.user_id == context.user_id,
                    ModuleProgress.module_id == module.id,
                    ModuleProgress.org_id == context.org_id,
                ).first()

                if not module_progress or module_progress.status != "completed":
                    logger.info(
                        f"Module {module.id} in previous section not completed by user {context.user_id}"
                    )
                    return RuleEvaluationResult(
                        rule_type=self.get_rule_type(),
                        passed=False,
                        reason=f"Complete all modules in '{previous_section.title}' first",
                    )

            logger.info(f"All modules in previous section {previous_section.id} completed, allowing access")
            return RuleEvaluationResult(
                rule_type=self.get_rule_type(),
                passed=True,
                reason=None,
            )
        except Exception as e:
            logger.error(f"Error evaluating previous_section_completed rule {rule.id}: {e}", exc_info=True)
            return RuleEvaluationResult(
                rule_type=self.get_rule_type(),
                passed=False,
                reason="Error evaluating rule",
            )


class ProgressionRuleEngine:
    """Main engine for evaluating progression rules.

    This engine loads all active rules for a target and evaluates them using
    registered rule evaluators.
    """

    def __init__(self, session: Session):
        self.session = session
        self._evaluators: dict[str, RuleEvaluator] = {}
        self._register_default_evaluators()

    def _register_default_evaluators(self) -> None:
        """Register the default rule evaluators."""
        self.register_evaluator(PreviousModuleCompletedEvaluator())
        self.register_evaluator(PreviousSectionCompletedEvaluator())

    def register_evaluator(self, evaluator: RuleEvaluator) -> None:
        """Register a rule evaluator for a specific rule type.

        Args:
            evaluator: The rule evaluator instance to register
        """
        self._evaluators[evaluator.get_rule_type()] = evaluator

    def get_evaluator(self, rule_type: str) -> RuleEvaluator | None:
        """Get the evaluator for a specific rule type.

        Args:
            rule_type: The rule type identifier

        Returns:
            The rule evaluator or None if not found
        """
        return self._evaluators.get(rule_type)

    def _load_rules(self, target_type: str, target_id: int, org_id: int) -> list[ProgressionRule]:
        """Load active rules for a target.

        Args:
            target_type: The target type (module or section)
            target_id: The target ID
            org_id: The organization ID

        Returns:
            List of active progression rules
        """
        return (
            self.session.query(ProgressionRule)
            .filter(
                ProgressionRule.target_type == target_type,
                ProgressionRule.target_id == target_id,
                ProgressionRule.org_id == org_id,
                ProgressionRule.is_active == True,
                ProgressionRule.deleted_at.is_(None),
            )
            .all()
        )

    def validate_access(
        self, user_id: str, target_type: str, target_id: int, org_id: int
    ) -> AccessValidationResult:
        """Validate whether a user can access a learning item.

        Args:
            user_id: The user ID
            target_type: The target type (module or section)
            target_id: The target ID
            org_id: The organization ID

        Returns:
            AccessValidationResult indicating if access is allowed and why
        """
        logger.info(
            f"Validating access for user {user_id} to {target_type}:{target_id} in org {org_id}"
        )
        context = RuleEvaluationContext(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            org_id=org_id,
            session=self.session,
        )

        rules = self._load_rules(target_type, target_id, org_id)
        logger.info(f"Found {len(rules)} active rules for {target_type}:{target_id}")

        if not rules:
            # No rules configured - allow access
            logger.info("No rules configured, allowing access")
            return AccessValidationResult(allowed=True)

        failed_results = []
        for rule in rules:
            evaluator = self.get_evaluator(rule.rule_type)
            if not evaluator:
                # Unknown rule type - skip it (don't block access)
                logger.warning(f"Unknown rule type: {rule.rule_type}, skipping")
                continue

            result = evaluator.evaluate(rule, context)
            if not result.passed:
                failed_results.append(result)

        if failed_results:
            # Return the first failure reason
            logger.info(
                f"Access denied for user {user_id} to {target_type}:{target_id}. Reason: {failed_results[0].reason}"
            )
            return AccessValidationResult(
                allowed=False,
                reason=failed_results[0].reason,
                failed_rules=failed_results,
            )

        logger.info(f"Access allowed for user {user_id} to {target_type}:{target_id}")
        return AccessValidationResult(allowed=True)
