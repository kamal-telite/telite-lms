"""Host-based domain context for platform versus tenant requests."""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Request


def _csv_env(name: str, defaults: tuple[str, ...]) -> set[str]:
    raw_value = os.getenv(name, "")
    values = [item.strip().lower() for item in raw_value.split(",") if item.strip()]
    return set(values or defaults)


PLATFORM_DOMAINS = _csv_env(
    "TELITE_PLATFORM_DOMAINS",
    ("platform.telite.com", "localhost", "127.0.0.1"),
)


@dataclass(frozen=True)
class DomainContext:
    host: str
    is_platform: bool
    tenant_domain: str | None


def resolve_domain_context(request: Request) -> DomainContext:
    host_header = request.headers.get("host", "")
    host = host_header.split(":")[0].strip().lower()
    is_platform = host in PLATFORM_DOMAINS
    return DomainContext(
        host=host,
        is_platform=is_platform,
        tenant_domain=None if is_platform else host or None,
    )
