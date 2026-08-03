"""Management API endpoints - modularized for maintainability.

This module consolidates all management-related API endpoints into a single router
while maintaining separation of concerns across multiple sub-modules:

- schemas: Pydantic models for request/response validation
- utils: Shared utility functions (role checks, access control)
- categories: Category CRUD operations
- admins: Admin user management and invitations
- courses: Course CRUD and cover image management
- learners: Learner invitation endpoints
- users: User management and activity queries
"""

from fastapi import APIRouter

from app.api.routes.management import categories, admins, courses, learners, users

# Create the main management router
management_router = APIRouter(tags=["Management"])

# Include all sub-routers
management_router.include_router(categories.categories_router)
management_router.include_router(admins.admins_router)
management_router.include_router(courses.courses_router)
management_router.include_router(learners.learners_router)
management_router.include_router(users.users_router)

# Export the main router for use in the main app
__all__ = ["management_router"]
