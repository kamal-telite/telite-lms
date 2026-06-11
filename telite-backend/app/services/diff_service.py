"""Diff Service for computing snapshot deltas."""

import difflib
import html
from typing import Dict, Any, List

class DiffService:
    @staticmethod
    def compute(source: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
        """
        Computes the structural diff between two snapshot dictionaries.
        Finds added, removed, and modified items by ID, returning a list of typed delta events.
        """
        events = []
        summary = {
            "sections_added": 0,
            "sections_removed": 0,
            "modules_added": 0,
            "modules_removed": 0,
            "blocks_added": 0,
            "blocks_removed": 0,
            "blocks_changed": 0
        }
        
        # Flatten source
        src_sections = {s["id"]: s for s in source.get("sections", [])}
        src_modules = {}
        src_blocks = {}
        for s in source.get("sections", []):
            for m in s.get("modules", []):
                src_modules[m["id"]] = m
                for b in m.get("blocks", []):
                    src_blocks[b["id"]] = b
                    
        # Flatten target
        tgt_sections = {s["id"]: s for s in target.get("sections", [])}
        tgt_modules = {}
        tgt_blocks = {}
        for s in target.get("sections", []):
            for m in s.get("modules", []):
                tgt_modules[m["id"]] = m
                for b in m.get("blocks", []):
                    tgt_blocks[b["id"]] = b
                    
        # Compare Sections
        src_sec_keys = set(src_sections.keys())
        tgt_sec_keys = set(tgt_sections.keys())
        
        for k in tgt_sec_keys - src_sec_keys:
            events.append({"type": "section_added", "section_title": tgt_sections[k].get("title"), "section_id": k})
            summary["sections_added"] += 1
            
        for k in src_sec_keys - tgt_sec_keys:
            events.append({"type": "section_removed", "section_title": src_sections[k].get("title"), "section_id": k})
            summary["sections_removed"] += 1
            
        for k in src_sec_keys.intersection(tgt_sec_keys):
            s_src = src_sections[k]
            s_tgt = tgt_sections[k]
            if s_src.get("title") != s_tgt.get("title"):
                events.append({
                    "type": "section_renamed", 
                    "section_id": k,
                    "old_title": s_src.get("title"),
                    "new_title": s_tgt.get("title")
                })
            if s_src.get("sort_order") != s_tgt.get("sort_order"):
                events.append({
                    "type": "section_reordered", 
                    "section_id": k,
                    "section_title": s_tgt.get("title")
                })
                
        # Compare Modules
        src_mod_keys = set(src_modules.keys())
        tgt_mod_keys = set(tgt_modules.keys())
        
        for k in tgt_mod_keys - src_mod_keys:
            events.append({"type": "module_added", "module_title": tgt_modules[k].get("title"), "module_id": k})
            summary["modules_added"] += 1
            
        for k in src_mod_keys - tgt_mod_keys:
            events.append({"type": "module_removed", "module_title": src_modules[k].get("title"), "module_id": k})
            summary["modules_removed"] += 1
            
        for k in src_mod_keys.intersection(tgt_mod_keys):
            m_src = src_modules[k]
            m_tgt = tgt_modules[k]
            if m_src.get("title") != m_tgt.get("title"):
                events.append({
                    "type": "module_renamed", 
                    "module_id": k,
                    "old_title": m_src.get("title"),
                    "new_title": m_tgt.get("title")
                })
            if m_src.get("section_id") != m_tgt.get("section_id"):
                events.append({
                    "type": "module_moved", 
                    "module_id": k,
                    "module_title": m_tgt.get("title")
                })
            elif m_src.get("sort_order") != m_tgt.get("sort_order"):
                events.append({
                    "type": "module_reordered", 
                    "module_id": k,
                    "module_title": m_tgt.get("title")
                })

        # Compare Blocks
        src_blk_keys = set(src_blocks.keys())
        tgt_blk_keys = set(tgt_blocks.keys())
        
        for k in tgt_blk_keys - src_blk_keys:
            events.append({"type": "block_added", "block_type": tgt_blocks[k].get("block_type"), "block_id": k, "module_id": tgt_blocks[k].get("module_id")})
            summary["blocks_added"] += 1
            
        for k in src_blk_keys - tgt_blk_keys:
            events.append({"type": "block_removed", "block_type": src_blocks[k].get("block_type"), "block_id": k, "module_id": src_blocks[k].get("module_id")})
            summary["blocks_removed"] += 1
            
        for k in src_blk_keys.intersection(tgt_blk_keys):
            b_src = src_blocks[k]
            b_tgt = tgt_blocks[k]
            block_changed = False
            
            if b_src.get("sort_order") != b_tgt.get("sort_order") or b_src.get("module_id") != b_tgt.get("module_id"):
                events.append({
                    "type": "block_reordered", 
                    "block_id": k,
                    "block_type": b_tgt.get("block_type")
                })
                block_changed = True
                
            if b_src.get("media_asset_id") != b_tgt.get("media_asset_id"):
                events.append({
                    "type": "media_changed",
                    "block_id": k,
                    "block_type": b_tgt.get("block_type"),
                    "old_asset": b_src.get("media_asset_id"),
                    "new_asset": b_tgt.get("media_asset_id")
                })
                block_changed = True
                
            if b_src.get("metadata_json") != b_tgt.get("metadata_json"):
                b_type = b_tgt.get("block_type")
                ev_type = "block_settings_changed"
                if b_type == "quiz":
                    ev_type = "quiz_changed"
                elif b_type == "assignment":
                    ev_type = "assignment_changed"
                elif b_type == "scorm":
                    ev_type = "scorm_changed"
                    
                events.append({
                    "type": ev_type,
                    "block_id": k,
                    "block_type": b_type
                })
                block_changed = True

            if b_src.get("content") != b_tgt.get("content"):
                old_text = str(b_src.get("content") or "")
                new_text = str(b_tgt.get("content") or "")
                diff_html = DiffService._compute_text_diff(old_text, new_text)
                events.append({
                    "type": "block_content_changed",
                    "block_id": k,
                    "block_type": b_tgt.get("block_type"),
                    "diff_html": diff_html
                })
                block_changed = True
                
            if block_changed:
                summary["blocks_changed"] += 1

        return {
            "summary": summary,
            "events": events
        }
        
    @staticmethod
    def _compute_text_diff(old_text: str, new_text: str) -> str:
        """
        Computes a word-level inline HTML diff between old_text and new_text.
        Uses difflib.SequenceMatcher.
        """
        def tokenize(text):
            import re
            return [t for t in re.split(r'(\s+)', text) if t]
            
        old_tokens = tokenize(old_text)
        new_tokens = tokenize(new_text)
        
        matcher = difflib.SequenceMatcher(None, old_tokens, new_tokens)
        result = []
        
        for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
            if opcode == 'equal':
                result.append(html.escape("".join(old_tokens[i1:i2])))
            elif opcode == 'insert':
                result.append(f'<ins style="background-color: #dcfce7; text-decoration: none;">{html.escape("".join(new_tokens[j1:j2]))}</ins>')
            elif opcode == 'delete':
                result.append(f'<del style="background-color: #fee2e2; text-decoration: line-through;">{html.escape("".join(old_tokens[i1:i2]))}</del>')
            elif opcode == 'replace':
                result.append(f'<del style="background-color: #fee2e2; text-decoration: line-through;">{html.escape("".join(old_tokens[i1:i2]))}</del>')
                result.append(f'<ins style="background-color: #dcfce7; text-decoration: none;">{html.escape("".join(new_tokens[j1:j2]))}</ins>')
                
        return "".join(result)
