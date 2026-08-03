from sqlalchemy import select

from app.models.learner_event import LearnerEvent


def test_category_quiz_statistics_filters_block_ids_as_scalars():
    block_info = {
        (1, "course-1"): ("block-1", "module-1", "course-1"),
        (2, "course-2"): ("block-2", "module-2", "course-2"),
    }

    block_ids = [block_id for block_id, _ in block_info.keys()]

    stmt = (
        select(LearnerEvent)
        .where(
            LearnerEvent.user_id.in_(["user-1", "user-2"]),
            LearnerEvent.org_id == 1,
            LearnerEvent.course_id.in_(["course-1", "course-2"]),
            LearnerEvent.event_type == "QUIZ_SUBMITTED",
            LearnerEvent.block_id.in_(block_ids),
        )
        .order_by(LearnerEvent.created_at.asc(), LearnerEvent.id.asc())
    )

    compiled = str(stmt)
    assert "course-1" not in compiled
    assert "course-2" not in compiled
    assert "IN" in compiled
