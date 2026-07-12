"""Runtime environment helpers shared across the backend."""

from __future__ import annotations

import os

_PRODUCTION_ENVS = frozenset({"production", "prod", "staging"})


def get_environment() -> str:
    return os.getenv("ENVIRONMENT", "development").lower().strip()


def is_production_like() -> bool:
    return get_environment() in _PRODUCTION_ENVS


def is_development() -> bool:
    return get_environment() == "development"


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


def get_api_base_url() -> str:
    """Get the base URL for the API (used for absolute URLs in media responses)."""
    return os.getenv("API_BASE_URL", "").rstrip("/")

