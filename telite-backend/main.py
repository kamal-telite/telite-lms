"""Compatibility entrypoint for local tools and `uvicorn main:app`."""

from app.main import app, create_app

__all__ = ["app", "create_app"]
