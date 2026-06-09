from __future__ import annotations

def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    parts = [part for part in cleaned.split("-") if part]
    return "-".join(parts)


def initials(full_name: str) -> str:
    parts = [part for part in full_name.split() if part]
    return "".join(part[0] for part in parts[:2]).upper()
