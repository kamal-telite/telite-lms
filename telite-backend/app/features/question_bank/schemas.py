from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class QuestionBankCreate(BaseModel):
    name: str


class QuestionBankResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class QuestionCreate(BaseModel):
    category_id: Optional[int] = None
    tag_ids: List[int] = []
    question_type: str
    question_text: str
    points: int = 1
    options_json: List[Dict[str, Any]] = []
    correct_answer_json: List[str] = []


class QuestionUpdateDraft(BaseModel):
    category_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None
    question_type: Optional[str] = None
    question_text: Optional[str] = None
    points: Optional[int] = None
    options_json: Optional[List[Dict[str, Any]]] = None
    correct_answer_json: Optional[List[str]] = None


class CategoryCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None


class TagCreate(BaseModel):
    name: str


class TagUpdate(BaseModel):
    name: str


class ImportJobCreate(BaseModel):
    file_key: str
    category_id: Optional[int] = None
    tag_ids: List[int] = []


class StaleCheckRequest(BaseModel):
    items: List[Dict[str, int]]
