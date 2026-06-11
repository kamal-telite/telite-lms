from sqlalchemy.orm import Session
from app.repositories.course_repo import CourseRepository
from app.repositories.builder_repo import BuilderRepository

from app.services.validation.schemas import ValidationResult, ValidationSummary, ValidationResultItem
from app.services.validation.course_validator import CourseValidator
from app.services.validation.module_validator import ModuleValidator
from app.services.validation.block_validator import BlockValidator
from app.services.validation.accessibility_validator import AccessibilityValidator

class ValidationEngine:
    def __init__(self, db: Session):
        self.db = db
        self.course_repo = CourseRepository(db)
        self.builder_repo = BuilderRepository(db)
        
    def run(self, course_id: str, org_id: int) -> ValidationResult:
        results = []
        
        course = self.course_repo.get_by_id(course_id)
        if not course or course.org_id != org_id:
            results.append(ValidationResultItem(
                type="course_not_found",
                severity="error",
                message="Course not found."
            ))
            return ValidationResult(
                summary=ValidationSummary(errors=1, warnings=0, infos=0, score=0),
                results=results
            )
            
        sections = self.builder_repo.get_sections(course_id, org_id)
        modules = self.builder_repo.get_modules(course_id, org_id)
        
        modules_by_section = {s.id: [] for s in sections}
        for m in modules:
            if m.section_id in modules_by_section:
                modules_by_section[m.section_id].append(m)
            elif m.section_id is None and m.section is not None:
                # Need to match by sort_order
                for s in sections:
                    if s.sort_order == m.section:
                        modules_by_section[s.id].append(m)
                        break

        # Validators
        course_validator = CourseValidator(self.db, org_id)
        module_validator = ModuleValidator(self.db, org_id)
        block_validator = BlockValidator(self.db, org_id)
        accessibility_validator = AccessibilityValidator(self.db, org_id)
        
        # 1. Course level
        results.extend(course_validator.validate(course, sections))
        
        total_modules = 0
        valid_modules = 0
        
        for section in sections:
            sec_modules = modules_by_section.get(section.id, [])
            
            for m_idx, mod in enumerate(sec_modules):
                total_modules += 1
                mod_errors_before = sum(1 for r in results if r.severity == "error")
                
                # 2. Module level
                blocks = self.builder_repo.get_blocks(mod.id, org_id)
                results.extend(module_validator.validate(section, mod, m_idx, blocks))
                
                # 3. Block level
                for b_idx, block in enumerate(blocks):
                    results.extend(block_validator.validate(section, mod, block, b_idx))
                    results.extend(accessibility_validator.validate(section, mod, block, b_idx))
                
                mod_errors_after = sum(1 for r in results if r.severity == "error")
                if mod_errors_before == mod_errors_after:
                    valid_modules += 1

        if total_modules > 0 and total_modules < 3:
            results.append(ValidationResultItem(
                type="low_content_volume",
                severity="warning",
                message="Course has very few modules. Consider adding more content."
            ))

        # Summarize
        errors = sum(1 for r in results if r.severity == "error")
        warnings = sum(1 for r in results if r.severity == "warning")
        infos = sum(1 for r in results if r.severity == "info")
        
        score = int((valid_modules / total_modules) * 100) if total_modules > 0 else (100 if not errors else 0)
        
        summary = ValidationSummary(
            errors=errors,
            warnings=warnings,
            infos=infos,
            score=score
        )
        
        return ValidationResult(summary=summary, results=results)
