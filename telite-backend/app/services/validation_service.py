from sqlalchemy.orm import Session
from app.repositories.course_repo import CourseRepository
from app.repositories.builder_repo import BuilderRepository
from app.models.media_asset import MediaAsset

class ValidationService:
    def __init__(self, db: Session):
        self.db = db
        self.course_repo = CourseRepository(db)
        self.builder_repo = BuilderRepository(db)
    
    def validate_course_tree(self, course_id: str, org_id: int) -> dict:
        errors = []
        warnings = []
        infos = []
        
        course = self.course_repo.get_by_id(course_id)
        if not course or course.org_id != org_id:
            errors.append({
                "type": "course_not_found",
                "severity": "error",
                "message": "Course not found."
            })
            return {"is_valid": False, "readiness_score": 0, "errors": errors, "warnings": warnings}
            
        if not course.name or not course.name.strip():
            errors.append({
                "type": "missing_title",
                "severity": "error",
                "message": "Course is missing a title.",
                "fix_target": {"section_title": "Course"}
            })
            
        if not course.description or not course.description.strip():
            warnings.append({
                "type": "missing_description",
                "severity": "warning",
                "message": "Course is missing a description.",
                "fix_target": {"section_title": "Course Settings"}
            })
            
        if not course.thumbnail_asset_id and not course.thumbnail_url:
            warnings.append({
                "type": "no_thumbnail",
                "severity": "warning",
                "message": "Course is missing a thumbnail.",
                "fix_target": {"section_title": "Course Settings"}
            })
            
        if not course.tags:
            infos.append({
                "type": "no_tags",
                "severity": "info",
                "message": "Adding tags helps learners discover this course.",
                "fix_target": {"section_title": "Course Settings"}
            })
            
        if not course.estimated_duration:
            infos.append({
                "type": "no_estimated_duration",
                "severity": "info",
                "message": "Providing an estimated duration helps set learner expectations.",
                "fix_target": {"section_title": "Course Settings"}
            })
            
        sections = self.builder_repo.get_sections(course_id, org_id)
        modules = self.builder_repo.get_modules(course_id, org_id)
        
        if not sections:
            errors.append({
                "type": "missing_sections",
                "severity": "error",
                "message": "Course has no sections.",
                "fix_target": {"section_title": "Course"}
            })
            
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

        total_modules = 0
        valid_modules = 0
        
        for section in sections:
            if not section.title or not section.title.strip():
                errors.append({
                    "type": "missing_title",
                    "severity": "error",
                    "section_id": section.id,
                    "message": f"Section #{section.sort_order + 1} is missing a title.",
                    "fix_target": {"section_title": f"Section #{section.sort_order + 1}"}
                })
                
            sec_modules = modules_by_section.get(section.id, [])
            if not sec_modules:
                errors.append({
                    "type": "missing_modules",
                    "severity": "error",
                    "section_id": section.id,
                    "message": f"Section '{section.title or f'Section #{section.sort_order + 1}'}' has no modules.",
                    "fix_target": {"section_title": section.title or f"Section #{section.sort_order + 1}"}
                })
                
            for m_idx, mod in enumerate(sec_modules):
                total_modules += 1
                mod_errors_count = len(errors)
                
                fix_target = {
                    "section_title": section.title or f"Section #{section.sort_order + 1}",
                    "module_title": mod.title or f"Module #{m_idx + 1}"
                }
                
                if not mod.title or not mod.title.strip():
                    errors.append({
                        "type": "missing_title",
                        "severity": "error",
                        "section_id": section.id,
                        "module_id": mod.id,
                        "message": f"Module #{m_idx + 1} in '{fix_target['section_title']}' is missing a title.",
                        "fix_target": fix_target
                    })
                    
                blocks = self.builder_repo.get_blocks(mod.id, org_id)
                if not blocks:
                    errors.append({
                        "type": "empty_module",
                        "severity": "error",
                        "section_id": section.id,
                        "module_id": mod.id,
                        "message": f"Module '{fix_target['module_title']}' is empty.",
                        "fix_target": fix_target
                    })
                    
                for b_idx, block in enumerate(blocks):
                    b_num = b_idx + 1
                    b_type = block.block_type
                    b_fix = fix_target.copy()
                    
                    if b_type == "heading" and (not block.content or not block.content.strip()):
                        errors.append({
                            "type": "missing_content",
                            "severity": "error",
                            "section_id": section.id,
                            "module_id": mod.id,
                            "block_id": block.id,
                            "message": f"Heading block #{b_num} in '{fix_target['module_title']}' is missing a title.",
                            "fix_target": b_fix
                        })
                    
                    if b_type in ["image", "video", "audio", "pdf", "scorm"]:
                        settings = block.metadata_json or {}
                        asset_id = block.media_asset_id or settings.get("asset_id")
                        url = settings.get("url")
                        
                        if not asset_id and not url:
                            errors.append({
                                "type": "missing_media",
                                "severity": "error",
                                "section_id": section.id,
                                "module_id": mod.id,
                                "block_id": block.id,
                                "message": f"{b_type.upper()} block #{b_num} in '{fix_target['module_title']}' is missing media.",
                                "fix_target": b_fix
                            })
                        elif asset_id:
                            if b_type == "image" and not settings.get("alt_text"):
                                warnings.append({
                                    "type": "missing_alt_text",
                                    "severity": "warning",
                                    "section_id": section.id,
                                    "module_id": mod.id,
                                    "block_id": block.id,
                                    "message": f"Image block #{b_num} is missing alt text for accessibility.",
                                    "fix_target": b_fix
                                })
                            # DB media check
                            asset = self.db.query(MediaAsset).filter(
                                MediaAsset.id == asset_id,
                                MediaAsset.org_id == org_id,
                                MediaAsset.deleted_at.is_(None)
                            ).first()
                            if not asset:
                                errors.append({
                                    "type": "broken_media",
                                    "severity": "error",
                                    "section_id": section.id,
                                    "module_id": mod.id,
                                    "block_id": block.id,
                                    "message": f"{b_type.upper()} block #{b_num} references a media asset that no longer exists.",
                                    "fix_target": b_fix
                                })
                        elif url:
                            warnings.append({
                                "type": "external_media",
                                "severity": "warning",
                                "section_id": section.id,
                                "module_id": mod.id,
                                "block_id": block.id,
                                "message": f"{b_type.upper()} block #{b_num} uses an external URL instead of the Media Library.",
                                "fix_target": b_fix
                            })
                            
                    if b_type == "embed":
                        settings = block.metadata_json or {}
                        url = settings.get("url")
                        if not url or not url.strip():
                            errors.append({
                                "type": "missing_url",
                                "severity": "error",
                                "section_id": section.id,
                                "module_id": mod.id,
                                "block_id": block.id,
                                "message": f"Embed block #{b_num} in '{fix_target['module_title']}' is missing a URL.",
                                "fix_target": b_fix
                            })
                            
                    if b_type == "assignment":
                        settings = block.metadata_json or {}
                        if not block.content or not block.content.strip():
                            errors.append({
                                "type": "missing_content",
                                "severity": "error",
                                "section_id": section.id,
                                "module_id": mod.id,
                                "block_id": block.id,
                                "message": f"Assignment block #{b_num} in '{fix_target['module_title']}' is missing a title.",
                                "fix_target": b_fix
                            })
                        if not settings.get("instructions") or not settings["instructions"].strip():
                            errors.append({
                                "type": "missing_instructions",
                                "severity": "error",
                                "section_id": section.id,
                                "module_id": mod.id,
                                "block_id": block.id,
                                "message": f"Assignment block #{b_num} in '{fix_target['module_title']}' is missing instructions.",
                                "fix_target": b_fix
                            })
                            
                    if b_type == "quiz_reference":
                        settings = block.metadata_json or {}
                        if not settings.get("quiz_id"):
                            errors.append({
                                "type": "missing_quiz",
                                "severity": "error",
                                "section_id": section.id,
                                "module_id": mod.id,
                                "block_id": block.id,
                                "message": f"Quiz Reference block #{b_num} in '{fix_target['module_title']}' has no quiz selected.",
                                "fix_target": b_fix
                            })

                if len(errors) == mod_errors_count:
                    valid_modules += 1

        if total_modules > 0 and total_modules < 3:
            warnings.append({
                "type": "low_content_volume",
                "severity": "warning",
                "message": "Course has very few modules. Consider adding more content.",
                "fix_target": {"section_title": "Syllabus"}
            })

        score = int((valid_modules / total_modules) * 100) if total_modules > 0 else (100 if not errors else 0)
        
        return {
            "is_valid": len(errors) == 0,
            "readiness_score": score,
            "errors": errors,
            "warnings": warnings,
            "infos": infos
        }
