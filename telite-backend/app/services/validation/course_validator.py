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
            
        if not course.thumbnail_asset_id and not course.thumbnail_url:
            results.append(ValidationResultItem(
                type="no_thumbnail",
                severity="warning",
                message="Course is missing a thumbnail.",
                fix_target=FixTarget(section_title="Course Settings")
            ))
            
        if not course.tags:
            results.append(ValidationResultItem(
                type="no_tags",
                severity="info",
                message="Adding tags helps learners discover this course.",
                fix_target=FixTarget(section_title="Course Settings")
            ))
            
        if not course.estimated_duration:
            results.append(ValidationResultItem(
                type="no_estimated_duration",
                severity="info",
                message="Providing an estimated duration helps set learner expectations.",
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
