"""Analytics utility functions."""

import json
from typing import Any


def round_value(value: float | int | None, digits: int = 1) -> float:
    """Round a numeric value to specified digits."""
    return round(float(value or 0), digits)


def safe_json_list(raw: str | None) -> list[dict[str, Any]]:
    """Safely parse a JSON string into a list of dictionaries."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def iso_format(value: Any) -> str | None:
    """Convert a value to ISO format string if possible."""
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def event_status(event_type: str) -> str:
    """Determine the status category for an event type."""
    if event_type in {"COURSE_COMPLETED", "MODULE_COMPLETED", "BLOCK_COMPLETED", "QUIZ_SUBMITTED"}:
        return "success"
    if event_type in {"PROGRESS_MUTATION", "HEARTBEAT", "BLOCK_VIEWED", "POLL_VOTED", "FLASHCARD_FLIPPED", "RESOURCE_DOWNLOADED"}:
        return "info"
    return "warning" if "FAILED" in event_type else "info"


def event_type(event_type: str) -> str:
    """Determine the category for an event type."""
    if "ENROLL" in event_type:
        return "enrollment"
    if "QUIZ" in event_type:
        return "pal"
    if "COURSE" in event_type or "MODULE" in event_type or "BLOCK" in event_type or event_type in ["POLL_VOTED", "FLASHCARD_FLIPPED", "RESOURCE_DOWNLOADED"]:
        return "course"
    return "system"


def event_title(event_type: str, learner_name: str, course_name: str | None, module_title: str | None) -> str:
    """Generate a human-readable title for an event."""
    course_label = course_name or "course"
    module_label = module_title or "module"
    labels = {
        "COURSE_STARTED": f"{learner_name} started {course_label}",
        "COURSE_COMPLETED": f"{learner_name} completed {course_label}",
        "MODULE_COMPLETED": f"{learner_name} completed {module_label}",
        "BLOCK_COMPLETED": f"{learner_name} completed an interactive block",
        "BLOCK_VIEWED": f"{learner_name} viewed content in {course_label}",
        "HEARTBEAT": f"{learner_name} continued learning in {course_label}",
        "PROGRESS_MUTATION": f"{learner_name} progress updated in {course_label}",
        "QUIZ_SUBMITTED": f"{learner_name} submitted a quiz in {course_label}",
        "POLL_VOTED": f"{learner_name} voted in a poll",
        "FLASHCARD_FLIPPED": f"{learner_name} flipped a flashcard",
        "RESOURCE_DOWNLOADED": f"{learner_name} downloaded a resource",
    }
    return labels.get(event_type, f"{learner_name} triggered {event_type.lower().replace('_', ' ')}")
