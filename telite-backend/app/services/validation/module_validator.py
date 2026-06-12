from typing import List
from app.services.validation.base_validator import BaseValidator
from app.services.validation.schemas import ValidationResultItem, FixTarget

class ModuleValidator(BaseValidator):
    def validate(self, section, module, m_idx, blocks) -> List[ValidationResultItem]:
        results = []
        
        sec_title = section.title or f"Section #{section.sort_order + 1}"
        mod_title = module.title or f"Module #{m_idx + 1}"
        
        fix_target = FixTarget(section_title=sec_title, module_title=mod_title, module_id=module.id)
        
        if not module.title or not module.title.strip():
            results.append(ValidationResultItem(
                type="missing_title",
                severity="error",
                section_id=section.id,
                module_id=module.id,
                message=f"Module #{m_idx + 1} in '{sec_title}' is missing a title.",
                fix_target=fix_target
            ))
            
        if not blocks:
            results.append(ValidationResultItem(
                type="empty_module",
                severity="error",
                section_id=section.id,
                module_id=module.id,
                message=f"Module '{mod_title}' is empty.",
                fix_target=fix_target
            ))
            
        return results
