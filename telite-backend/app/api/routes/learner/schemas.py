"""Learner API schemas and request/response models."""

from typing import List, Optional
from pydantic import BaseModel


class CourseListResponse(BaseModel):
    id: str
    name: str
    description: str
    slug: str
    status: str
    enrolled_count: int
    completion_rate: float
    modules_count: int
    tier: str
    cover_image_url: Optional[str] = None
    category_slug: Optional[str] = None


class ModuleProgressUpdate(BaseModel):
    module_id: int
    status: str
    last_block_id: Optional[str] = None
    video_position_seconds: Optional[int] = None


class ProgressMutationRequest(BaseModel):
    course_id: str
    module_updates: List[ModuleProgressUpdate]


class LearnerEventPayload(BaseModel):
    event_type: str
    course_id: Optional[str] = None
    module_id: Optional[int] = None
    block_id: Optional[int] = None
    payload_json: dict = {}


class LearnerEventsBatchRequest(BaseModel):
    events: List[LearnerEventPayload]


class HeartbeatRequest(BaseModel):
    course_id: str
    module_id: Optional[int] = None
    block_id: Optional[int] = None
    time_spent_seconds: int


class LearningSessionStartRequest(BaseModel):
    course_id: str
    module_id: Optional[int] = None
    block_id: Optional[int] = None


class LearningSessionHeartbeatRequest(BaseModel):
    session_id: int
    course_id: str
    module_id: Optional[int] = None
    block_id: Optional[int] = None
    active_seconds: int


class LearningSessionEndRequest(BaseModel):
    session_id: int
    reason: Optional[str] = "ended"


class AccessValidationRequest(BaseModel):
    target_type: str
    target_id: int


class QuizSubmitRequest(BaseModel):
    answers: dict


class PollVoteRequest(BaseModel):
    option_id: int
