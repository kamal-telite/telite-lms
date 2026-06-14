from typing import List
from app.services.validation.base_validator import BaseValidator
from app.services.validation.schemas import ValidationResultItem, FixTarget

class CourseValidator(BaseValidator):
    def validate(self, course, sections) -> List[ValidationResultItem]:
        results = []
        
        if not course.name or not course.name.strip():
            results.append(ValidationResultItem(
                type="missing_title",
                severity="error",
                message="Course is missing a title.",
                fix_target=FixTarget(section_title="Course Settings")
            ))
            
        if not course.description or not course.description.strip():
            results.append(ValidationResultItem(
                type="missing_description",
                severity="warning",
                message="Course is missing a description.",
                fix_target=FixTarget(section_title="Course Settings")
            ))

        thumbnail_asset_id = getattr(course, "thumbnail_asset_id", None)
        thumbnail_url = getattr(course, "thumbnail_url", None)
        if (hasattr(course, "thumbnail_asset_id") or hasattr(course, "thumbnail_url")) and not thumbnail_asset_id and not thumbnail_url:
            results.append(ValidationResultItem(
                type="no_thumbnail",
                severity="warning",
                message="Course is missing a thumbnail.",
                fix_target=FixTarget(section_title="Course Settings")
            ))

        tags = getattr(course, "tags", None)
        if hasattr(course, "tags") and not tags:
            results.append(ValidationResultItem(
                type="no_tags",
                severity="info",
                message="Adding tags helps learners discover this course.",
                fix_target=FixTarget(section_title="Course Settings")
            ))

        estimated_duration = getattr(course, "estimated_duration", None)
        hours = getattr(course, "hours", None)
        if hasattr(course, "estimated_duration") and not estimated_duration:
            results.append(ValidationResultItem(
                type="no_estimated_duration",
                severity="info",
                message="Providing an estimated duration helps set learner expectations.",
                fix_target=FixTarget(section_title="Course Settings")
            ))
        elif hasattr(course, "hours") and not hours:
            results.append(ValidationResultItem(
                type="no_estimated_duration",
                severity="info",
                message="Providing course hours helps set learner expectations.",
                fix_target=FixTarget(section_title="Course Settings")
            ))
            
        if not sections:
            results.append(ValidationResultItem(
                type="missing_sections",
                severity="error",
                message="Course has no sections.",
                fix_target=FixTarget(section_title="Syllabus")
            ))
            
        for section in sections:
            if not section.title or not section.title.strip():
                results.append(ValidationResultItem(
                    type="missing_title",
                    severity="error",
                    section_id=section.id,
                    message=f"Section #{section.sort_order + 1} is missing a title.",
                    fix_target=FixTarget(section_title=f"Section #{section.sort_order + 1}")
                ))
                
        return results
