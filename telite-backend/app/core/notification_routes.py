"""Notification route registry and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationRoute:
    route: str
    route_name: str

    def to_metadata(self) -> dict[str, str]:
        return {"route": self.route, "route_name": self.route_name}


UNSUPPORTED_ROUTE_PREFIXES = (
    "/api/",
    "/authoring/courses/",
    "/courses/",
)

SUPPORTED_ROUTE_PREFIXES = (
    "/learner",
    "/categories/",
    "/platform-admin",
    "/super-admin",
)


def learner_course_route(course_id: str) -> NotificationRoute:
    return NotificationRoute(
        route=f"/learner/courses/{course_id}",
        route_name="learner_course",
    )


def learner_assignment_route(course_id: str, block_id: int | str) -> NotificationRoute:
    return NotificationRoute(
        route=f"/learner/courses/{course_id}/assignments/{block_id}",
        route_name="learner_assignment",
    )


def learner_tasks_route() -> NotificationRoute:
    return NotificationRoute(route="/learner/tasks", route_name="learner_tasks")


def learner_courses_route() -> NotificationRoute:
    return NotificationRoute(route="/learner/courses", route_name="learner_courses")


def learner_paths_route() -> NotificationRoute:
    return NotificationRoute(route="/learner/paths", route_name="learner_paths")


def learner_certificates_route() -> NotificationRoute:
    return NotificationRoute(route="/learner/certificates", route_name="learner_certificates")


def category_course_builder_route(category_slug: str, course_id: str) -> NotificationRoute:
    if not category_slug:
        raise ValueError("category_slug is required for course authoring routes")
    return NotificationRoute(
        route=f"/categories/{category_slug}/builder/{course_id}",
        route_name="category_course_builder",
    )


def validate_notification_route(route: str) -> None:
    if not route:
        raise ValueError("notification metadata must include route")
    if any(route.startswith(prefix) for prefix in UNSUPPORTED_ROUTE_PREFIXES):
        raise ValueError(f"unsupported notification route: {route}")
    if not any(route == prefix.rstrip("/") or route.startswith(prefix) for prefix in SUPPORTED_ROUTE_PREFIXES):
        raise ValueError(f"notification route is not mounted in the frontend: {route}")
