"""Helpers for redacting user identifiers in logs and audit messages."""

from __future__ import annotations


def mask_identifier(identifier: str | None) -> str:
    """Return a stable, human-useful redaction for email/username identifiers."""
    value = (identifier or "").strip().lower()
    if not value:
        return "<empty>"

    if "@" in value:
        local, domain = value.split("@", 1)
        if not local:
            masked_local = "*"
        elif len(local) == 1:
            masked_local = f"{local[0]}***"
        else:
            masked_local = f"{local[0]}***{local[-1]}"
        return f"{masked_local}@{domain}"

    if len(value) <= 2:
        return f"{value[0]}***"
    return f"{value[0]}***{value[-1]}"