from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any

from fastapi import HTTPException


H5P_MIME_TYPES = {
    "application/x-h5p",
    "application/zip",
    "application/zip-compressed",
    "application/x-zip-compressed",
    "application/octet-stream",
}

MAX_H5P_PACKAGE_BYTES = 500 * 1024 * 1024
MAX_H5P_EXTRACTED_BYTES = 1024 * 1024 * 1024
MAX_H5P_FILES = 10_000
H5P_VERSION_MANIFEST = "h5p_versions.json"

_BLOCKED_SUFFIXES = {
    ".bat",
    ".cmd",
    ".com",
    ".dll",
    ".exe",
    ".msi",
    ".ps1",
    ".scr",
    ".sh",
}


@dataclass(frozen=True)
class H5PValidationResult:
    title: str | None
    main_library: str | None
    language: str | None
    file_count: int
    extracted_bytes: int


def is_h5p_asset(filename: str | None, mime_type: str | None) -> bool:
    return bool(filename and filename.lower().endswith(".h5p")) or (mime_type or "") in H5P_MIME_TYPES


def assert_h5p_asset(filename: str | None, mime_type: str | None) -> None:
    if not is_h5p_asset(filename, mime_type):
        raise HTTPException(status_code=400, detail="Asset is not an H5P package")


def validate_h5p_package_bytes(
    contents: bytes,
    *,
    filename: str,
    mime_type: str,
) -> H5PValidationResult:
    assert_h5p_asset(filename, mime_type)
    if len(contents) > MAX_H5P_PACKAGE_BYTES:
        raise HTTPException(status_code=400, detail="H5P package is too large")
    if not contents.startswith(b"PK"):
        raise HTTPException(status_code=400, detail="Invalid H5P package: not a zip file")

    try:
        with zipfile.ZipFile(BytesIO(contents), "r") as zip_ref:
            return _validate_zip_members(zip_ref)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Invalid H5P package: corrupted zip file") from exc


def install_h5p_package(
    package_path: Path,
    *,
    contents: bytes,
    filename: str,
    mime_type: str,
    extract_root: Path,
) -> H5PValidationResult:
    result = validate_h5p_package_bytes(contents, filename=filename, mime_type=mime_type)
    extract_tmp = extract_root.with_name(f"{extract_root.name}.tmp")
    shutil.rmtree(extract_tmp, ignore_errors=True)
    extract_tmp.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(BytesIO(contents), "r") as zip_ref:
            for member in zip_ref.infolist():
                if member.is_dir():
                    continue
                target = _safe_member_target(extract_tmp, member.filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zip_ref.open(member, "r") as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)

        shutil.rmtree(extract_root, ignore_errors=True)
        extract_tmp.replace(extract_root)
        package_path.write_bytes(contents)
    except Exception:
        shutil.rmtree(extract_tmp, ignore_errors=True)
        package_path.unlink(missing_ok=True)
        raise

    return result


def update_h5p_version_manifest(
    org_dir: Path,
    *,
    asset_id: int,
    asset_version: int,
    stored_name: str,
    metadata: H5PValidationResult | None = None,
) -> dict[str, Any]:
    manifest_path = org_dir / H5P_VERSION_MANIFEST
    manifest = _read_manifest(manifest_path)
    asset_key = str(asset_id)
    asset_versions = manifest.setdefault(asset_key, {})
    asset_versions[str(asset_version)] = {
        "stored_name": stored_name,
        "title": metadata.title if metadata else None,
        "main_library": metadata.main_library if metadata else None,
        "file_count": metadata.file_count if metadata else None,
        "extracted_bytes": metadata.extracted_bytes if metadata else None,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def resolve_h5p_extract_dir(
    org_dir: Path,
    *,
    asset_id: int,
    asset_version: int | None,
    current_stored_name: str,
    current_asset_version: int,
) -> Path:
    version = asset_version or current_asset_version
    manifest = _read_manifest(org_dir / H5P_VERSION_MANIFEST)
    stored_name = (
        manifest.get(str(asset_id), {})
        .get(str(version), {})
        .get("stored_name")
    )
    if not stored_name and version == current_asset_version:
        stored_name = current_stored_name
    if not stored_name:
        raise HTTPException(status_code=404, detail="H5P asset version not found")
    return org_dir / "h5p_extracted" / stored_name


def safe_h5p_file_path(extract_dir: Path, file_path: str | None) -> Path:
    relative = (file_path or "h5p.json").strip("/") or "h5p.json"
    target = (extract_dir / relative).resolve()
    try:
        target.relative_to(extract_dir.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Access denied") from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found in H5P package")
    return target


def h5p_manifest_metadata(contents: bytes) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(BytesIO(contents), "r") as zip_ref:
            with zip_ref.open("h5p.json", "r") as manifest_file:
                manifest = json.loads(manifest_file.read().decode("utf-8"))
    except Exception:
        return {}
    return {
        "h5p_title": manifest.get("title"),
        "h5p_main_library": manifest.get("mainLibrary"),
        "h5p_language": manifest.get("language"),
    }


def _validate_zip_members(zip_ref: zipfile.ZipFile) -> H5PValidationResult:
    members = zip_ref.infolist()
    files = [member for member in members if not member.is_dir()]
    if len(files) > MAX_H5P_FILES:
        raise HTTPException(status_code=400, detail="Invalid H5P package: too many files")

    total_size = 0
    names = set()
    for member in files:
        _safe_member_path(member.filename)
        suffix = Path(member.filename).suffix.lower()
        if suffix in _BLOCKED_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"Invalid H5P package: blocked file type {suffix}")
        total_size += int(member.file_size or 0)
        if total_size > MAX_H5P_EXTRACTED_BYTES:
            raise HTTPException(status_code=400, detail="Invalid H5P package: extracted content too large")
        names.add(member.filename.replace("\\", "/"))

    if "h5p.json" not in names:
        raise HTTPException(status_code=400, detail="Invalid H5P package: missing h5p.json")
    if "content/content.json" not in names:
        raise HTTPException(status_code=400, detail="Invalid H5P package: missing content/content.json")

    try:
        manifest = json.loads(zip_ref.read("h5p.json").decode("utf-8"))
        json.loads(zip_ref.read("content/content.json").decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid H5P package: malformed JSON manifest") from exc

    if not isinstance(manifest, dict) or not manifest.get("mainLibrary"):
        raise HTTPException(status_code=400, detail="Invalid H5P package: missing mainLibrary")

    return H5PValidationResult(
        title=manifest.get("title"),
        main_library=manifest.get("mainLibrary"),
        language=manifest.get("language"),
        file_count=len(files),
        extracted_bytes=total_size,
    )


def _safe_member_target(root: Path, member_name: str) -> Path:
    relative = _safe_member_path(member_name)
    target = (root / relative).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid H5P package: unsafe path") from exc
    return target


def _safe_member_path(member_name: str) -> Path:
    normalized = member_name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or not normalized or normalized.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid H5P package: unsafe path")
    return Path(*path.parts)


def _read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}
