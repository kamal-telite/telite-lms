from typing import List, Optional
from pydantic import BaseModel

class FixTarget(BaseModel):
    section_title: Optional[str] = None
    module_title: Optional[str] = None
    module_id: Optional[int] = None
    block_id: Optional[int] = None

class ValidationResultItem(BaseModel):
    type: str
    severity: str # "error", "warning", "info"
    message: str
    section_id: Optional[int] = None
    module_id: Optional[int] = None
    block_id: Optional[int] = None
    fix_target: Optional[FixTarget] = None

class ValidationSummary(BaseModel):
    errors: int = 0
    warnings: int = 0
    infos: int = 0
    score: int = 100

class ValidationResult(BaseModel):
    summary: ValidationSummary
    results: List[ValidationResultItem]
