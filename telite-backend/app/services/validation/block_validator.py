from typing import List
from sqlalchemy.orm import Session
from app.services.validation.base_validator import BaseValidator
from app.services.validation.schemas import ValidationResultItem, FixTarget
from app.models.media_asset import MediaAsset
from app.services.h5p_service import is_h5p_asset

class BlockValidator(BaseValidator):
    def validate(self, section, module, block, b_idx) -> List[ValidationResultItem]:
        results = []
        
        sec_title = section.title or f"Section #{section.sort_order + 1}" if section else "Unassigned"
        sec_id = section.id if section else None
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
                section_id=sec_id,
                module_id=module.id,
                block_id=block.id,
                message=f"Heading block #{b_num} in '{mod_title}' is missing a title.",
                fix_target=fix_target
            ))
            
        if b_type in ["image", "video", "audio", "pdf", "scorm", "h5p"]:
            settings = block.metadata_json or {}
            asset_id = block.media_asset_id or settings.get("asset_id")
            url = settings.get("url")
            
            if not asset_id:
                results.append(ValidationResultItem(
                    type="missing_media",
                    severity="error",
                    section_id=sec_id,
                    module_id=module.id,
                    block_id=block.id,
                    message=f"{b_type.upper()} block #{b_num} in '{mod_title}' must use an asset from the Media Library.",
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
                        section_id=sec_id,
                        module_id=module.id,
                        block_id=block.id,
                        message=f"{b_type.upper()} block #{b_num} references a media asset that no longer exists.",
                        fix_target=fix_target
                    ))
                elif b_type == "h5p" and not is_h5p_asset(asset.filename, asset.mime_type):
                    results.append(ValidationResultItem(
                        type="invalid_h5p_asset",
                        severity="error",
                        section_id=sec_id,
                        module_id=module.id,
                        block_id=block.id,
                        message=f"H5P block #{b_num} in '{mod_title}' references a non-H5P media asset.",
                        fix_target=fix_target
                    ))
            if b_type != "h5p" and url and not asset_id:
                results.append(ValidationResultItem(
                    type="external_media",
                    severity="warning",
                    section_id=sec_id,
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
                    section_id=sec_id,
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
                    section_id=sec_id,
                    module_id=module.id,
                    block_id=block.id,
                    message=f"Assignment block #{b_num} in '{mod_title}' is missing a title.",
                    fix_target=fix_target
                ))
            if not settings.get("instructions") or not settings["instructions"].strip():
                results.append(ValidationResultItem(
                    type="missing_instructions",
                    severity="error",
                    section_id=sec_id,
                    module_id=module.id,
                    block_id=block.id,
                    message=f"Assignment block #{b_num} in '{mod_title}' is missing instructions.",
                    fix_target=fix_target
                ))
                
        if b_type == "quiz_reference":
            results.append(ValidationResultItem(
                type="deprecated_quiz_reference",
                severity="error",
                section_id=sec_id,
                module_id=module.id,
                block_id=block.id,
                message=f"Quiz Reference block #{b_num} in '{mod_title}' is deprecated. Use a Native Quiz block instead.",
                fix_target=fix_target
            ))

        if b_type in ["quiz", "native_quiz"]:
            settings = block.metadata_json or {}
            passing_score = settings.get("passing_score")
            if passing_score is None or not isinstance(passing_score, (int, float)) or passing_score < 0 or passing_score > 100:
                results.append(ValidationResultItem(type="invalid_passing_score", severity="error", section_id=sec_id, module_id=module.id, block_id=block.id, message=f"Quiz block #{b_num} in '{mod_title}' must have a passing score between 0 and 100.", fix_target=fix_target))
            max_attempts = settings.get("max_attempts", 0)
            if not isinstance(max_attempts, int) or max_attempts < 0:
                results.append(ValidationResultItem(type="invalid_max_attempts", severity="error", section_id=sec_id, module_id=module.id, block_id=block.id, message=f"Quiz block #{b_num} in '{mod_title}' must have max attempts of 0 or greater.", fix_target=fix_target))
            questions = settings.get("questions", [])
            if not questions:
                results.append(ValidationResultItem(type="missing_questions", severity="error", section_id=sec_id, module_id=module.id, block_id=block.id, message=f"Quiz block #{b_num} in '{mod_title}' has no questions.", fix_target=fix_target))
            else:
                for q_idx, q in enumerate(questions):
                    if q.get("type") == "bank_reference":
                        continue
                    if not q.get("text") or not q.get("text").strip():
                        results.append(ValidationResultItem(type="empty_question", severity="error", section_id=sec_id, module_id=module.id, block_id=block.id, message=f"Question {q_idx + 1} in Quiz block #{b_num} has empty text.", fix_target=fix_target))
                    options = q.get("options", [])
                    if len(options) < 2:
                        results.append(ValidationResultItem(type="not_enough_options", severity="error", section_id=sec_id, module_id=module.id, block_id=block.id, message=f"Question {q_idx + 1} in Quiz block #{b_num} must have at least 2 options.", fix_target=fix_target))
                    else:
                        for o_idx, opt in enumerate(options):
                            if not opt.get("text") or not opt.get("text").strip():
                                results.append(ValidationResultItem(type="empty_option", severity="error", section_id=sec_id, module_id=module.id, block_id=block.id, message=f"Option {o_idx + 1} of Question {q_idx + 1} in Quiz block #{b_num} is empty.", fix_target=fix_target))
                    option_ids = {opt.get("id") for opt in options}
                    if not q.get("correct_option_id") or q.get("correct_option_id") not in option_ids:
                        results.append(ValidationResultItem(type="missing_correct_option", severity="error", section_id=sec_id, module_id=module.id, block_id=block.id, message=f"Question {q_idx + 1} in Quiz block #{b_num} has no valid correct option selected.", fix_target=fix_target))

        if b_type == "poll":
            settings = block.metadata_json or {}
            options = settings.get("options", [])
            
            # Allow poll question text to be in block.content or settings.question
            if not block.content or not block.content.strip():
                if not settings.get("question") or not settings.get("question").strip():
                    results.append(ValidationResultItem(type="missing_poll_question", severity="error", section_id=sec_id, module_id=module.id, block_id=block.id, message=f"Poll block #{b_num} in '{mod_title}' is missing a question text.", fix_target=fix_target))
            
            if not options or len(options) < 2:
                results.append(ValidationResultItem(type="missing_options", severity="error", section_id=sec_id, module_id=module.id, block_id=block.id, message=f"Poll block #{b_num} in '{mod_title}' must have at least 2 options.", fix_target=fix_target))
            else:
                for o_idx, opt in enumerate(options):
                    if not opt.get("text") or not opt.get("text").strip():
                        results.append(ValidationResultItem(type="empty_option", severity="error", section_id=sec_id, module_id=module.id, block_id=block.id, message=f"Option {o_idx + 1} in Poll block #{b_num} is empty.", fix_target=fix_target))

        if b_type == "flashcard":
            settings = block.metadata_json or {}
            cards = settings.get("cards", [])
            if not cards:
                results.append(ValidationResultItem(type="missing_cards", severity="error", section_id=sec_id, module_id=module.id, block_id=block.id, message=f"Flashcard block #{b_num} in '{mod_title}' has no cards.", fix_target=fix_target))
            else:
                for c_idx, c in enumerate(cards):
                    if not c.get("front_text") or not c.get("front_text").strip():
                        results.append(ValidationResultItem(type="empty_card_front", severity="error", section_id=sec_id, module_id=module.id, block_id=block.id, message=f"Card {c_idx + 1} in Flashcard block #{b_num} is missing front text.", fix_target=fix_target))
                    if not c.get("back_text") or not c.get("back_text").strip():
                        results.append(ValidationResultItem(type="empty_card_back", severity="error", section_id=sec_id, module_id=module.id, block_id=block.id, message=f"Card {c_idx + 1} in Flashcard block #{b_num} is missing back text.", fix_target=fix_target))
        if b_type == "resource_collection":
            settings = block.metadata_json or {}
            resources = settings.get("resources", [])
            if not resources:
                results.append(ValidationResultItem(type="missing_resources", severity="error", section_id=sec_id, module_id=module.id, block_id=block.id, message=f"Resource block #{b_num} in '{mod_title}' has no resources.", fix_target=fix_target))

        return results
