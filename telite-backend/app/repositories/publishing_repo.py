import copy
import copy
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.course_version import CourseVersion
from app.models.course_section import CourseSection
from app.models.course_module import CourseModule
from app.models.lesson_block import LessonBlock
from app.models.media_asset import MediaAsset
from app.repositories.base_repo import BaseRepository
from app.models.builder_activity_log import BuilderActivityLog

class PublishingRepository(BaseRepository):
    def get_course(self, course_id: str, org_id: int) -> Course | None:
        stmt = select(Course).where(Course.id == course_id, Course.org_id == org_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def update_course_status(self, course: Course, status: str) -> None:
        course.status = status
        self.session.flush()

    def get_versions(self, course_id: str, org_id: int):
        stmt = (
            select(CourseVersion)
            .where(CourseVersion.course_id == course_id, CourseVersion.org_id == org_id)
            .order_by(CourseVersion.version_number.desc())
        )
        return self.session.execute(stmt).scalars().all()

    def get_version(self, version_id: str, org_id: int) -> CourseVersion | None:
        stmt = select(CourseVersion).where(
            CourseVersion.id == version_id, CourseVersion.org_id == org_id
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def create_version(self, course_id: str, org_id: int, version_number: int, parent_version_id: str | None = None, snapshot: dict | None = None, created_by: str | None = None) -> CourseVersion:
        import uuid
        version = CourseVersion(
            id=uuid.uuid4().hex,
            course_id=course_id,
            org_id=org_id,
            version_number=version_number,
            parent_version_id=parent_version_id,
            snapshot_json=snapshot,
            status="draft",
            created_by=created_by,
        )
        self.session.add(version)
        self.session.flush()
        return version

    def update_version_status(self, version: CourseVersion, status: str, user_id: str | None = None) -> None:
        version.status = status
        if status == "published" and user_id:
            version.published_by = user_id
            version.published_at = datetime.now(timezone.utc)
        self.session.flush()

    def log_activity(self, course_id: str, user_id: str, org_id: int, action: str, payload: str = "{}") -> BuilderActivityLog:
        log = BuilderActivityLog(course_id=course_id, user_id=user_id, org_id=org_id, action=action, payload=payload)
        self.session.add(log)
        self.session.flush()
        return log

    def build_snapshot(self, course_id: str, org_id: int) -> dict:
        course = self.get_course(course_id, org_id)
        if not course: raise ValueError("Course not found")

        sections = self.session.execute(
            select(CourseSection).where(CourseSection.course_id == course_id, CourseSection.org_id == org_id, CourseSection.deleted_at.is_(None)).order_by(CourseSection.sort_order, CourseSection.id)
        ).scalars().all()

        modules = self.session.execute(
            select(CourseModule).where(CourseModule.course_id == course_id, CourseModule.org_id == org_id, CourseModule.deleted_at.is_(None)).order_by(CourseModule.section_id, CourseModule.sort_order, CourseModule.id)
        ).scalars().all()

        module_ids = [module.id for module in modules]
        blocks = []
        if module_ids:
            blocks = self.session.execute(
                select(LessonBlock).where(LessonBlock.module_id.in_(module_ids), LessonBlock.org_id == org_id, LessonBlock.deleted_at.is_(None)).order_by(LessonBlock.module_id, LessonBlock.sort_order, LessonBlock.id)
            ).scalars().all()

        blocks_by_module = {}
        for block in blocks:
            settings = copy.deepcopy(block.metadata_json) if block.metadata_json else {}
            
            # Resolve Question Bank references (Hybrid Model)
            if block.block_type == "quiz" and "questions" in settings:
                from app.models.question import QuestionVersion
                
                hydrated_questions = []
                for q in settings["questions"]:
                    if q.get("type") == "bank_reference":
                        version_id = q.get("question_version_id") or q.get("version_id")
                        if version_id:
                            q_version = self.session.execute(
                                select(QuestionVersion).where(
                                    QuestionVersion.id == version_id,
                                    QuestionVersion.org_id == org_id
                                )
                            ).scalar_one_or_none()
                            
                            if not q_version:
                                raise ValueError(f"Referenced QuestionVersion {version_id} not found.")
                            if q_version.status != "PUBLISHED":
                                raise ValueError(f"Cannot publish course: Quiz block references non-PUBLISHED QuestionVersion {version_id}.")

                            options = copy.deepcopy(q_version.options_json or [])
                            correct_answers = copy.deepcopy(q_version.correct_answer_json or [])
                            correct_option_id = correct_answers[0] if correct_answers else None

                            # Hydrate the full payload into the question object
                            q = {
                                "source": "question_bank",
                                "id": f"qbank-{q_version.question_id}-v{q_version.id}",
                                "text": q_version.question_text,
                                "options": options,
                                "correct_option_id": correct_option_id,
                                "question_id": q_version.question_id,
                                "version_id": q_version.id,
                                "question_type": q_version.question_type,
                                "question_text": q_version.question_text,
                                "options_json": q_version.options_json,
                                "correct_answer_json": q_version.correct_answer_json,
                                "points": q_version.points,
                                "hydrated_at": datetime.now(timezone.utc).isoformat()
                            }
                    hydrated_questions.append(q)
                settings["questions"] = hydrated_questions
            blocks_by_module.setdefault(block.module_id, []).append({
                "id": block.id,
                "module_id": block.module_id,
                "block_type": block.block_type,
                "content": block.content,
                "media_asset_id": block.media_asset_id,
                "sort_order": block.sort_order,
                "settings": settings,
                "metadata_json": copy.deepcopy(settings),
            })

        modules_by_section = {}
        for module in modules:
            modules_by_section.setdefault(module.section_id, []).append({
                "id": module.id,
                "section_id": module.section_id,
                "title": module.title,
                "module_type": module.module_type,
                "status": module.status,
                "content_url": module.content_url,
                "sort_order": module.sort_order,
                "blocks": blocks_by_module.get(module.id, []),
            })

        sections_list = [
            {
                "id": section.id,
                "title": section.title,
                "sort_order": section.sort_order,
                "minimum_time_seconds": section.minimum_time_seconds or 0,
                "modules": modules_by_section.get(section.id, []),
            }
            for section in sections
        ]

        orphaned_modules = modules_by_section.get(None, [])
        if orphaned_modules:
            sections_list.append({
                "id": 0,
                "title": "Unassigned Modules",
                "sort_order": 9999,
                "modules": orphaned_modules,
            })

        return {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "course": {"id": course.id, "name": course.name, "status": course.status},
            "sections": sections_list,
        }

    def restore_snapshot(self, course_id: str, org_id: int, snapshot: dict, user_id: str) -> dict:
        return {"restored": True, "message": "Restore functionally mocked."}

    def snapshot_summary(self, snapshot: dict) -> dict:
        if not snapshot: return {}
        sections = snapshot.get("sections", [])
        modules = sum([len(s.get("modules", [])) for s in sections])
        blocks = sum([sum([len(m.get("blocks", [])) for m in s.get("modules", [])]) for s in sections])
        return {"sections": len(sections), "modules": modules, "blocks": blocks}
