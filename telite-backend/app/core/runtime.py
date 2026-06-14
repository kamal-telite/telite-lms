"""Runtime environment helpers shared across the backend."""

from __future__ import annotations

import os

_PRODUCTION_ENVS = frozenset({"production", "prod", "staging"})


def get_environment() -> str:
    return os.getenv("ENVIRONMENT", "development").lower().strip()


def is_production_like() -> bool:
    return get_environment() in _PRODUCTION_ENVS


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value
