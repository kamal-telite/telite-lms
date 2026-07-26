from __future__ import annotations

from typing import Final


class AssignmentStatus:
    NOT_SUBMITTED: Final[str] = "not_submitted"
    DRAFT: Final[str] = "draft"
    SUBMITTED: Final[str] = "submitted"
    UNDER_REVIEW: Final[str] = "under_review"
    APPROVED: Final[str] = "approved"
    GRADED: Final[str] = "graded"
    REJECTED: Final[str] = "rejected"
    RESUBMISSION_REQUIRED: Final[str] = "resubmission_required"

    PENDING_VERIFICATION: Final[str] = "pending_verification"
    RESUBMITTED: Final[str] = "resubmitted"
    RETURNED: Final[str] = "returned"


DISPLAY_LABELS: Final[dict[str, str]] = {
    AssignmentStatus.NOT_SUBMITTED: "Not Submitted",
    AssignmentStatus.DRAFT: "Draft",
    AssignmentStatus.SUBMITTED: "Submitted",
    AssignmentStatus.UNDER_REVIEW: "Under Review",
    AssignmentStatus.APPROVED: "Approved",
    AssignmentStatus.GRADED: "Graded",
    AssignmentStatus.REJECTED: "Rejected",
    AssignmentStatus.RESUBMISSION_REQUIRED: "Resubmission Required",
    AssignmentStatus.PENDING_VERIFICATION: "Under Review",
    AssignmentStatus.RESUBMITTED: "Under Review",
    AssignmentStatus.RETURNED: "Resubmission Required",
}


def normalize_status(status: str | None) -> str:
    value = (status or "").strip().lower()
    if not value:
        return AssignmentStatus.NOT_SUBMITTED
    mapping = {
        AssignmentStatus.NOT_SUBMITTED: AssignmentStatus.NOT_SUBMITTED,
        AssignmentStatus.DRAFT: AssignmentStatus.DRAFT,
        AssignmentStatus.SUBMITTED: AssignmentStatus.SUBMITTED,
        AssignmentStatus.UNDER_REVIEW: AssignmentStatus.UNDER_REVIEW,
        AssignmentStatus.APPROVED: AssignmentStatus.APPROVED,
        AssignmentStatus.GRADED: AssignmentStatus.GRADED,
        AssignmentStatus.REJECTED: AssignmentStatus.REJECTED,
        AssignmentStatus.RESUBMISSION_REQUIRED: AssignmentStatus.RESUBMISSION_REQUIRED,
        AssignmentStatus.PENDING_VERIFICATION: AssignmentStatus.UNDER_REVIEW,
        AssignmentStatus.RESUBMITTED: AssignmentStatus.UNDER_REVIEW,
        AssignmentStatus.RETURNED: AssignmentStatus.RESUBMISSION_REQUIRED,
        "idle": AssignmentStatus.NOT_SUBMITTED,
        "loading": AssignmentStatus.NOT_SUBMITTED,
        "error": AssignmentStatus.NOT_SUBMITTED,
        "submitted": AssignmentStatus.SUBMITTED,
        "pending_verification": AssignmentStatus.UNDER_REVIEW,
        "resubmitted": AssignmentStatus.UNDER_REVIEW,
        "approved": AssignmentStatus.APPROVED,
        "graded": AssignmentStatus.GRADED,
        "rejected": AssignmentStatus.REJECTED,
        "returned": AssignmentStatus.RESUBMISSION_REQUIRED,
        "draft": AssignmentStatus.DRAFT,
    }
    return mapping.get(value, AssignmentStatus.NOT_SUBMITTED)


def status_label(status: str | None) -> str:
    return DISPLAY_LABELS.get(normalize_status(status), DISPLAY_LABELS[AssignmentStatus.NOT_SUBMITTED])


def can_resubmit(status: str | None) -> bool:
    return normalize_status(status) in {AssignmentStatus.DRAFT, AssignmentStatus.REJECTED, AssignmentStatus.RESUBMISSION_REQUIRED}
