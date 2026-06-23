"""Pure builders and validators for notification payload contracts."""

from __future__ import annotations

from typing import Any

from app.core.notification_routes import (
    NotificationRoute,
    category_course_builder_route,
    learner_assignment_route,
    learner_certificates_route,
    learner_courses_route,
    learner_course_route,
    learner_paths_route,
    learner_tasks_route,
    validate_notification_route,
)


ACTIVE_NOTIFICATION_TYPES = {
    "task_assigned",
    "task_approved",
    "task_rejected",
    "task_revision_requested",
    "enrollment_created",
    "course_published",
    "course_rejected",
    "assignment_graded",
    "certificate_awarded",
    "learning_path_assigned",
    "learning_path_unlocked",
    "learning_path_completed",
}


def _metadata(route: NotificationRoute, **values: Any) -> dict[str, Any]:
    payload = route.to_metadata()
    payload.update({key: value for key, value in values.items() if value is not None})
    validate_notification_payload(payload)
    return payload


def validate_notification_payload(metadata: dict[str, Any] | None) -> None:
    if not isinstance(metadata, dict):
        raise ValueError("notification metadata_json must be an object")
    route = metadata.get("route")
    route_name = metadata.get("route_name")
    if not isinstance(route, str) or not route:
        raise ValueError("notification metadata_json.route is required")
    if not isinstance(route_name, str) or not route_name:
        raise ValueError("notification metadata_json.route_name is required")
    validate_notification_route(route)


def task_notification_metadata(task_id: str, assignment_id: int | str | None = None) -> dict[str, Any]:
    return _metadata(
        learner_tasks_route(),
        task_id=task_id,
        assignment_id=assignment_id,
    )


def enrollment_notification_metadata(course_id: str) -> dict[str, Any]:
    return _metadata(
        learner_course_route(course_id),
        course_id=course_id,
    )


def assignment_graded_metadata(
    *,
    course_id: str,
    block_id: int | str,
    submission_id: int | str,
) -> dict[str, Any]:
    return _metadata(
        learner_assignment_route(course_id, block_id),
        course_id=course_id,
        block_id=block_id,
        submission_id=submission_id,
    )


def certificate_awarded_metadata(
    *,
    course_id: str,
    certificate_id: str,
    verification_token: str,
) -> dict[str, Any]:
    return _metadata(
        learner_certificates_route(),
        course_id=course_id,
        certificate_id=certificate_id,
        verification_token=verification_token,
    )


def learning_path_unlocked_metadata(
    *,
    path_id: int | str,
    course_id: str,
) -> dict[str, Any]:
    return _metadata(
        learner_courses_route(),
        path_id=path_id,
        course_id=course_id,
    )


def learning_path_assigned_metadata(*, path_id: int | str) -> dict[str, Any]:
    return _metadata(
        learner_paths_route(),
        path_id=path_id,
    )


def learning_path_completed_metadata(*, path_id: int | str) -> dict[str, Any]:
    return _metadata(
        learner_paths_route(),
        path_id=path_id,
    )


def course_authoring_metadata(
    *,
    category_slug: str,
    course_id: str,
    course_version_id: str | None = None,
    version_number: int | None = None,
) -> dict[str, Any]:
    return _metadata(
        category_course_builder_route(category_slug, course_id),
        course_id=course_id,
        course_version_id=course_version_id,
        version_number=version_number,
    )


def course_published_idempotency_key(
    *,
    user_id: str,
    course_version_id: str | None = None,
    course_id: str | None = None,
    version_number: int | None = None,
) -> str:
    if course_version_id:
        return f"{user_id}:course_published:{course_version_id}"
    if course_id and version_number is not None:
        return f"{user_id}:course_published:{course_id}:v{version_number}"
    raise ValueError("course_published idempotency requires course_version_id or course_id + version_number")


def certificate_awarded_idempotency_key(*, user_id: str, certificate_id: str) -> str:
    if not user_id or not certificate_id:
        raise ValueError("certificate_awarded idempotency requires user_id and certificate_id")
    return f"{user_id}:certificate_awarded:{certificate_id}"


def learning_path_unlocked_idempotency_key(*, user_id: str, path_id: int | str, course_id: str) -> str:
    if not user_id or not path_id or not course_id:
        raise ValueError("learning_path_unlocked idempotency requires user_id, path_id, and course_id")
    return f"{user_id}:learning_path_unlocked:{path_id}:{course_id}"


def learning_path_assigned_idempotency_key(*, user_id: str, path_id: int | str) -> str:
    if not user_id or not path_id:
        raise ValueError("learning_path_assigned idempotency requires user_id and path_id")
    return f"{user_id}:learning_path_assigned:{path_id}"


def learning_path_completed_idempotency_key(*, user_id: str, path_id: int | str) -> str:
    if not user_id or not path_id:
        raise ValueError("learning_path_completed idempotency requires user_id and path_id")
    return f"{user_id}:learning_path_completed:{path_id}"
