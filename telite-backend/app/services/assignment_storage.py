from __future__ import annotations

import mimetypes
import os
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.storage_paths import assignment_upload_root

MAX_ASSIGNMENT_FILE_BYTES = int(os.getenv("TELITE_ASSIGNMENT_MAX_FILE_BYTES", str(25 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {
    # Documents & Archives
    ".pdf", ".doc", ".docx", ".zip", ".txt", ".csv", ".xlsx", ".ppt", ".pptx",
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    # C/C++
    ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp",
    # Java & JVM
    ".java", ".kt", ".scala",
    # Python
    ".py",
    # Web & JavaScript/TypeScript
    ".js", ".mjs", ".ts", ".tsx",
    ".html", ".css", ".scss",
    ".json", ".xml", ".yml", ".yaml", ".md",
    # C#
    ".cs",
    # Systems & Scripting
    ".go", ".rs", ".swift", ".php", ".rb", ".pl", ".lua", ".dart",
    # Data Science & Shell
    ".r", ".m", ".sh", ".bash", ".zsh", ".sql",
}
ALLOWED_MIME_PREFIXES = ("image/", "text/")
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/zip",
    "application/x-zip-compressed",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/json",
    "application/xml",
    "application/javascript",
    "application/x-javascript",
    "application/typescript",
    "application/x-sh",
}


@dataclass(frozen=True)
class StoredAssignmentFile:
    file_path: str
    original_filename: str
    mime_type: str
    file_size: int

    def to_public_dict(self, *, asset_id: str | None = None) -> dict:
        payload = {
            "file_path": self.file_path,
            "filename": self.original_filename,
            "original_filename": self.original_filename,
            "mime_type": self.mime_type,
            "size_bytes": self.file_size,
            "file_size": self.file_size,
        }
        if asset_id is not None:
            payload["asset_id"] = asset_id
        return payload


class StorageProvider:
    async def upload(self, *, org_id: int, block_id: int, learner_id: str, file: UploadFile) -> StoredAssignmentFile:
        raise NotImplementedError

    def resolve(self, file_path: str) -> Path:
        raise NotImplementedError

    def delete(self, file_path: str) -> None:
        raise NotImplementedError


def _assignment_upload_root() -> Path:
    return assignment_upload_root()


def _safe_filename(filename: str | None) -> str:
    value = (filename or "assignment-file").strip().replace("\\", "_").replace("/", "_")
    value = re.sub(r"[^A-Za-z0-9._ -]+", "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:180] or "assignment-file"


def _validate_file(filename: str, mime_type: str, size: int) -> None:
    suffix = Path(filename).suffix.lower()
    if size <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if size > MAX_ASSIGNMENT_FILE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is too large")
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type is not allowed")
    if mime_type not in ALLOWED_MIME_TYPES and not any(mime_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES):
        guessed, _ = mimetypes.guess_type(filename)
        if guessed not in ALLOWED_MIME_TYPES and not (guessed or "").startswith(ALLOWED_MIME_PREFIXES):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File MIME type is not allowed")


def _scan_file_for_threats(filename: str, contents: bytes) -> None:
    """Antivirus integration hook for V1 local storage.

    Production deployments can wire this boundary to ClamAV, an EDR agent, or
    an object-storage malware scanning pipeline without changing assignment
    API/service code.
    """
    return None


class LocalStorageProvider(StorageProvider):
    def __init__(self, root: Path | None = None):
        self.root = (root or _assignment_upload_root()).resolve()

    async def upload(self, *, org_id: int, block_id: int, learner_id: str, file: UploadFile) -> StoredAssignmentFile:
        original = _safe_filename(file.filename)
        mime_type = file.content_type or mimetypes.guess_type(original)[0] or "application/octet-stream"
        contents = await file.read()
        _validate_file(original, mime_type, len(contents))
        _scan_file_for_threats(original, contents)

        suffix = Path(original).suffix.lower()
        stored_name = f"{uuid4().hex}{suffix}"
        relative = Path(str(org_id)) / "assignments" / str(block_id) / _safe_filename(learner_id) / stored_name
        target = (self.root / relative).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload path") from exc

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents)
        return StoredAssignmentFile(
            file_path=relative.as_posix(),
            original_filename=original,
            mime_type=mime_type,
            file_size=len(contents),
        )

    def resolve(self, file_path: str) -> Path:
        candidate = (self.root / file_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc
        if not candidate.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return candidate

    def delete(self, file_path: str) -> None:
        try:
            candidate = self.resolve(file_path)
        except HTTPException:
            return
        candidate.unlink(missing_ok=True)


def get_storage_provider() -> StorageProvider:
    provider = os.getenv("TELITE_STORAGE_PROVIDER", "local").strip().lower()
    if provider != "local":
        raise RuntimeError(f"Unsupported TELITE_STORAGE_PROVIDER for assignments: {provider}")
    return LocalStorageProvider()
