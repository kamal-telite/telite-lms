from typing import List
from app.services.validation.base_validator import BaseValidator
from app.services.validation.schemas import ValidationResultItem, FixTarget
from app.models.media_asset import MediaAsset

class BlockValidator(BaseValidator):
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
        
        if b_type == "heading" and (not block.content or not block.content.strip()):
            results.append(ValidationResultItem(
                type="missing_content",
                severity="error",
                section_id=section.id,
                module_id=module.id,
                block_id=block.id,
                message=f"Heading block #{b_num} in '{mod_title}' is missing a title.",
                fix_target=fix_target
            ))
            
        if b_type in ["image", "video", "audio", "pdf", "scorm"]:
            settings = block.metadata_json or {}
            asset_id = block.media_asset_id or settings.get("asset_id")
            url = settings.get("url")
            
            if not asset_id and not url:
                results.append(ValidationResultItem(
                    type="missing_media",
                    severity="error",
                    section_id=section.id,
                    module_id=module.id,
                    block_id=block.id,
                    message=f"{b_type.upper()} block #{b_num} in '{mod_title}' is missing media.",
                    fix_target=fix_target
                ))
            elif asset_id:
                asset = self.db.query(MediaAsset).filter(
                    MediaAsset.id == asset_id,
                    MediaAsset.org_id == self.org_id,
                    MediaAsset.deleted_at.is_(None)
                ).first()
                if not asset:
                    results.append(ValidationResultItem(
                        type="broken_media",
                        severity="error",
                        section_id=section.id,
                        module_id=module.id,
                        block_id=block.id,
                        message=f"{b_type.upper()} block #{b_num} references a media asset that no longer exists.",
                        fix_target=fix_target
                    ))
            elif url:
                results.append(ValidationResultItem(
                    type="external_media",
                    severity="warning",
                    section_id=section.id,
                    module_id=module.id,
                    block_id=block.id,
                    message=f"{b_type.upper()} block #{b_num} uses an external URL instead of the Media Library.",
                    fix_target=fix_target
                ))
                
        if b_type == "embed":
            settings = block.metadata_json or {}
            url = settings.get("url")
            if not url or not url.strip():
                results.append(ValidationResultItem(
                    type="missing_url",
                    severity="error",
                    section_id=section.id,
                    module_id=module.id,
                    block_id=block.id,
                    message=f"Embed block #{b_num} in '{mod_title}' is missing a URL.",
                    fix_target=fix_target
                ))
                
        if b_type == "assignment":
            settings = block.metadata_json or {}
            if not block.content or not block.content.strip():
                results.append(ValidationResultItem(
                    type="missing_content",
                    severity="error",
                    section_id=section.id,
                    module_id=module.id,
                    block_id=block.id,
                    message=f"Assignment block #{b_num} in '{mod_title}' is missing a title.",
                    fix_target=fix_target
                ))
            if not settings.get("instructions") or not settings["instructions"].strip():
                results.append(ValidationResultItem(
                    type="missing_instructions",
                    severity="error",
                    section_id=section.id,
                    module_id=module.id,
                    block_id=block.id,
                    message=f"Assignment block #{b_num} in '{mod_title}' is missing instructions.",
                    fix_target=fix_target
                ))
                
        if b_type == "quiz_reference":
            settings = block.metadata_json or {}
            if not settings.get("quiz_id"):
                results.append(ValidationResultItem(
                    type="missing_quiz",
                    severity="error",
                    section_id=section.id,
                    module_id=module.id,
                    block_id=block.id,
                    message=f"Quiz Reference block #{b_num} in '{mod_title}' has no quiz selected.",
                    fix_target=fix_target
                ))

        return results
