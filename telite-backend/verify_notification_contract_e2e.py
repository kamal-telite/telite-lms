"""Verify Notification Engine N5A payload, route, and idempotency contracts."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from app.core.notification_payloads import (  # noqa: E402
    assignment_graded_metadata,
    course_authoring_metadata,
    course_published_idempotency_key,
    enrollment_notification_metadata,
    task_notification_metadata,
    validate_notification_payload,
)
from app.db.engine import get_platform_session  # noqa: E402
from app.models.notification import NotificationType  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.repositories.notification_repo import NotificationRepository  # noqa: E402


def _pass(value: bool) -> str:
    return "PASS" if value else "FAIL"


def _write_report(rows: list[dict], *, duplicate_passed: bool, metadata_object_passed: bool) -> None:
    root = Path(__file__).resolve().parents[1]
    report_path = root / "Project_docs" / "NOTIFICATION_N5A_VERIFICATION.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    matrix = "\n".join(
        "| {type} | {source_type} | {source_id} | {route} | {route_name} | {ownership} | {idempotency} | {passed} |".format(
            **row
        )
        for row in rows
    )
    report_path.write_text(
        f"""# Notification N5A Verification

## Scope

N5A hardens the existing Notification Engine V1 contract before any new producers are added.

## Verification Results

- metadata_json returned as object: {_pass(metadata_object_passed)}
- every active route validates against the frontend route registry: {_pass(all(row["passed"] == "PASS" for row in rows))}
- course_published duplicate prevention for the same course version: {_pass(duplicate_passed)}

## Producer Compliance Matrix

| Type | Source Type | Source ID | Route | Route Name | Ownership Verified | Idempotency Required | Pass |
| ---- | ----------- | --------- | ----- | ---------- | ------------------ | -------------------- | ---- |
{matrix}

## Route Contract

Valid notification routes must use mounted frontend route families only:

- `/learner/*`
- `/categories/{{slug}}/*`
- `/platform-admin/*`
- `/super-admin/*`

Unsupported producer routes remain blocked:

- `/api/*`
- `/courses/{{id}}`
- `/authoring/courses/{{id}}`

## Publish Idempotency

`course_published` uses this preferred stable key:

`user_id + course_published + course_version_id`

Fallback, only when no course version id exists:

`user_id + course_published + source_id + version_number`
""",
        encoding="utf-8",
    )
    print(f"Wrote verification report: {report_path}")


def run() -> None:
    uid = uuid.uuid4().hex[:8]
    course_id = f"course-{uid}"
    course_version_id = f"version-{uid}"
    block_id = 1400
    submission_id = 2400
    task_id = f"task-{uid}"
    assignment_id = f"task-assignment-{uid}"
    user_id = f"notif-user-{uid}"

    with get_platform_session() as db:
        org = Organization(
            name=f"N5A Notification Contract {uid}",
            slug=f"n5a-notification-{uid}",
            plan="enterprise",
            status="active",
            type="school",
            domain=f"n5a-{uid}.example.com",
        )
        db.add(org)
        db.flush()
        org_id = org.id

        repo = NotificationRepository(db)
        definitions = [
            {
                "type": NotificationType.TASK_ASSIGNED,
                "title": "New task assigned",
                "body": "New task assigned.",
                "source_type": "task",
                "source_id": task_id,
                "metadata": task_notification_metadata(task_id, assignment_id),
                "ownership": "recipient_user_id",
                "idempotency": "No",
            },
            {
                "type": NotificationType.TASK_APPROVED,
                "title": "Task approved",
                "body": "Your task has been approved.",
                "source_type": "task",
                "source_id": task_id,
                "metadata": task_notification_metadata(task_id, assignment_id),
                "ownership": "assignment_learner_id",
                "idempotency": "No",
            },
            {
                "type": NotificationType.TASK_REJECTED,
                "title": "Task rejected",
                "body": "Your task was rejected.",
                "source_type": "task",
                "source_id": task_id,
                "metadata": task_notification_metadata(task_id, assignment_id),
                "ownership": "assignment_learner_id",
                "idempotency": "No",
            },
            {
                "type": NotificationType.TASK_REVISION_REQUESTED,
                "title": "Revision requested",
                "body": "Revision requested on your task.",
                "source_type": "task",
                "source_id": task_id,
                "metadata": task_notification_metadata(task_id, assignment_id),
                "ownership": "assignment_learner_id",
                "idempotency": "No",
            },
            {
                "type": NotificationType.ENROLLMENT_CREATED,
                "title": "Course Enrollment",
                "body": "You have been enrolled.",
                "source_type": "course",
                "source_id": course_id,
                "metadata": enrollment_notification_metadata(course_id),
                "ownership": "learner_user_id",
                "idempotency": "No",
            },
            {
                "type": NotificationType.COURSE_REJECTED,
                "title": "Course Requires Changes",
                "body": "Your course was returned for revision.",
                "source_type": "course",
                "source_id": course_id,
                "metadata": course_authoring_metadata(category_slug="n5a", course_id=course_id),
                "ownership": "course_author_id",
                "idempotency": "No",
            },
            {
                "type": NotificationType.ASSIGNMENT_GRADED,
                "title": "Assignment Graded",
                "body": "Your assignment has been graded.",
                "source_type": "assignment",
                "source_id": str(submission_id),
                "metadata": assignment_graded_metadata(
                    course_id=course_id,
                    block_id=block_id,
                    submission_id=submission_id,
                ),
                "ownership": "submission_user_id",
                "idempotency": "No",
            },
        ]

        rows: list[dict] = []
        metadata_object_passed = True
        for definition in definitions:
            notif = repo.create(
                user_id=user_id,
                org_id=org_id,
                title=definition["title"],
                body=definition["body"],
                notif_type=definition["type"],
                source_type=definition["source_type"],
                source_id=definition["source_id"],
                metadata=definition["metadata"],
            )
            payload = notif.to_dict()
            metadata = payload["metadata_json"]
            metadata_object_passed = metadata_object_passed and isinstance(metadata, dict)
            try:
                validate_notification_payload(metadata)
                passed = "PASS"
            except ValueError:
                passed = "FAIL"
            rows.append(
                {
                    "type": getattr(definition["type"], "value", definition["type"]),
                    "source_type": definition["source_type"],
                    "source_id": definition["source_id"],
                    "route": metadata.get("route"),
                    "route_name": metadata.get("route_name"),
                    "ownership": definition["ownership"],
                    "idempotency": definition["idempotency"],
                    "passed": passed,
                }
            )

        publish_metadata = course_authoring_metadata(
            category_slug="n5a",
            course_id=course_id,
            course_version_id=course_version_id,
            version_number=3,
        )
        idempotency_key = course_published_idempotency_key(
            user_id=user_id,
            course_version_id=course_version_id,
        )
        first = repo.create_once(
            user_id=user_id,
            org_id=org_id,
            title="Course Published",
            body="Your course has been published.",
            notif_type=NotificationType.COURSE_PUBLISHED,
            source_type="course",
            source_id=course_id,
            metadata=publish_metadata,
            idempotency_key=idempotency_key,
        )
        second = repo.create_once(
            user_id=user_id,
            org_id=org_id,
            title="Course Published",
            body="Your course has been published.",
            notif_type=NotificationType.COURSE_PUBLISHED,
            source_type="course",
            source_id=course_id,
            metadata=publish_metadata,
            idempotency_key=idempotency_key,
        )
        duplicate_passed = first.id == second.id
        publish_payload = first.to_dict()
        metadata_object_passed = metadata_object_passed and isinstance(publish_payload["metadata_json"], dict)
        rows.append(
            {
                "type": "course_published",
                "source_type": "course",
                "source_id": course_id,
                "route": publish_payload["metadata_json"].get("route"),
                "route_name": publish_payload["metadata_json"].get("route_name"),
                "ownership": "course_author_id",
                "idempotency": "Yes: user_id + course_version_id",
                "passed": _pass(duplicate_passed),
            }
        )
        db.commit()

    _write_report(rows, duplicate_passed=duplicate_passed, metadata_object_passed=metadata_object_passed)

    failed = [row for row in rows if row["passed"] != "PASS"]
    if failed or not duplicate_passed or not metadata_object_passed:
        print("N5A verification failed")
        print(f"Failed rows: {failed}")
        sys.exit(1)

    print("N5A notification contract verification passed.")


if __name__ == "__main__":
    run()
