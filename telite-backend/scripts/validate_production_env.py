"""Validate required production environment settings before deploy/startup."""

from __future__ import annotations

import os
import re
import sys
from urllib.parse import urlparse

PLACEHOLDER_PATTERNS = (
    re.compile(r"^change-me", re.IGNORECASE),
    re.compile(r"^replace-with", re.IGNORECASE),
    re.compile(r"^(password|secret|changeme|changeit)$", re.IGNORECASE),
)

REQUIRED = (
    "TELITE_AUTH_SECRET",
    "TELITE_PASSWORD_SALT",
    "POSTGRES_PASSWORD",
    "TELITE_POSTGRES_DB",
    "TELITE_POSTGRES_USER",
    "TELITE_POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "TELITE_APP_URL",
    "TELITE_CORS_ORIGINS",
)


def _is_placeholder(value: str) -> bool:
    normalized = value.strip()
    return any(pattern.search(normalized) for pattern in PLACEHOLDER_PATTERNS)


def _require_url(name: str, value: str, errors: list[str]) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"https"} or not parsed.netloc:
        errors.append(f"{name} must be an absolute HTTPS URL")


def validate() -> list[str]:
    errors: list[str] = []

    environment = os.getenv("ENVIRONMENT", "").lower().strip()
    if environment not in {"production", "prod", "staging"}:
        errors.append("ENVIRONMENT must be production, prod, or staging")

    for name in REQUIRED:
        value = os.getenv(name, "").strip()
        if not value:
            errors.append(f"{name} is required")
        elif _is_placeholder(value):
            errors.append(f"{name} still looks like a placeholder")

    auth_secret = os.getenv("TELITE_AUTH_SECRET", "").strip()
    if auth_secret and len(auth_secret) < 32:
        errors.append("TELITE_AUTH_SECRET must be at least 32 characters")

    password_salt = os.getenv("TELITE_PASSWORD_SALT", "").strip()
    if password_salt and len(password_salt) < 16:
        errors.append("TELITE_PASSWORD_SALT must be at least 16 characters")

    app_url = os.getenv("TELITE_APP_URL", "").strip()
    if app_url:
        _require_url("TELITE_APP_URL", app_url, errors)

    cors_origins = [
        origin.strip() for origin in os.getenv("TELITE_CORS_ORIGINS", "").split(",") if origin.strip()
    ]
    if not cors_origins:
        errors.append("TELITE_CORS_ORIGINS must contain at least one HTTPS origin")
    for origin in cors_origins:
        _require_url("TELITE_CORS_ORIGINS", origin, errors)

    if os.getenv("COOKIE_SECURE", "").lower().strip() not in {"true", "1", "yes"}:
        errors.append("COOKIE_SECURE must be true in production")

    if os.getenv("COOKIE_SAMESITE", "").lower().strip() not in {"strict", "lax"}:
        errors.append("COOKIE_SAMESITE must be strict or lax")

    if os.getenv("MOODLE_MODE", "").lower().strip() == "live" and not os.getenv("MOODLE_TOKEN", "").strip():
        errors.append("MOODLE_TOKEN is required when MOODLE_MODE=live")

    if os.getenv("R2_ENABLED", "").lower().strip() in {"true", "1", "yes"}:
        for name in ("R2_ENDPOINT", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_BUCKET"):
            if not os.getenv(name, "").strip():
                errors.append(f"{name} is required when R2_ENABLED=true")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Production environment validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Production environment validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
