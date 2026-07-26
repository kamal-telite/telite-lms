"""Learner API endpoints - modularized for maintainability.

This module consolidates all learner-related API endpoints into a single router
while maintaining separation of concerns across multiple sub-modules:

- schemas: Pydantic models for request/response validation
- utils: Shared utility functions (sanitization, resolution, etc.)
- courses: Course and module retrieval endpoints
- progress: Progress tracking and learning session endpoints
- events: Event recording and access validation endpoints
- quiz: Quiz submission and statistics endpoints
- resume: Course resume and submission endpoints
- blocks: Block-specific endpoints (PDF, poll, resources)
"""

from fastapi import APIRouter

from app.api.routes.learner import courses, progress, events, quiz, resume, blocks

# Create the main learner router
learner_router = APIRouter(prefix="/learner", tags=["Learner APIs"])

# Include all sub-routers
learner_router.include_router(courses.learner_courses_router)
learner_router.include_router(progress.learner_progress_router)
learner_router.include_router(events.learner_events_router)
learner_router.include_router(quiz.learner_quiz_router)
learner_router.include_router(resume.learner_resume_router)
learner_router.include_router(blocks.learner_blocks_router)

# Export the main router for use in the main app
__all__ = ["learner_router"]
