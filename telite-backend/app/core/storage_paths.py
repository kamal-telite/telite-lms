from __future__ import annotations

import os
from pathlib import Path


def upload_root() -> Path:
    configured = os.getenv("TELITE_UPLOAD_ROOT", "").strip()
    if configured:
        return Path(configured).resolve()
    return (Path(__file__).resolve().parents[2] / "uploads").resolve()


def media_upload_root() -> Path:
    return upload_root() / "media"


def branding_upload_root() -> Path:
    return upload_root() / "branding"


def certificate_upload_root() -> Path:
    return upload_root() / "certificates"


def assignment_upload_root() -> Path:
    configured = os.getenv("TELITE_ASSIGNMENT_UPLOAD_DIR", "").strip()
    if configured:
        return Path(configured).resolve()
    return upload_root() / "organizations"
