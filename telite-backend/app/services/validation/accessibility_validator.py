from typing import List
from sqlalchemy.orm import Session
from app.services.validation.base_validator import BaseValidator
from app.services.validation.schemas import ValidationResultItem, FixTarget

class AccessibilityValidator(BaseValidator):
    def validate(self, section, module, block, b_idx) -> List[ValidationResultItem]:
        results = []
        
        sec_title = section.title or f"Section #{section.sort_order + 1}"
        mod_title = module.title or f"Module #{module.sort_order + 1}"
        b_num = b_idx + 1
        b_type = block.block_type
        
        fix_target = FixTarget(
            section_title=sec_title, 
            module_title=mod_title, 
            module_id=module.id,
            block_id=block.id
        )
        
        if b_type == "image":
            settings = block.metadata_json or {}
            if not settings.get("alt_text"):
                results.append(ValidationResultItem(
                    type="missing_alt_text",
                    severity="warning",
                    section_id=section.id,
                    module_id=module.id,
                    block_id=block.id,
                    message=f"Image block #{b_num} is missing alt text for accessibility.",
                    fix_target=fix_target
                ))
                
        if b_type == "video" or b_type == "audio":
            settings = block.metadata_json or {}
            if not settings.get("transcript_url"):
                results.append(ValidationResultItem(
                    type="missing_transcript",
                    severity="warning",
                    section_id=section.id,
                    module_id=module.id,
                    block_id=block.id,
                    message=f"{b_type.capitalize()} block #{b_num} is missing a transcript URL for accessibility.",
                    fix_target=fix_target
                ))
                
        return results
