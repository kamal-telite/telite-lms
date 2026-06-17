import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi import HTTPException

from app.services.h5p_service import (
    install_h5p_package,
    resolve_h5p_extract_dir,
    update_h5p_version_manifest,
    validate_h5p_package_bytes,
)


def _h5p_zip(extra_files: dict[str, bytes] | None = None, *, include_manifest: bool = True) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        if include_manifest:
            archive.writestr(
                "h5p.json",
                json.dumps({"title": "Safety Check", "mainLibrary": "H5P.TrueFalse", "language": "en"}),
            )
        archive.writestr("content/content.json", json.dumps({"question": "Ready?"}))
        for name, payload in (extra_files or {}).items():
            archive.writestr(name, payload)
    return buffer.getvalue()


def test_valid_h5p_package_validates_and_extracts(tmp_path: Path):
    contents = _h5p_zip({"libraries/H5P.TrueFalse/library.json": b"{}"})
    target = tmp_path / "valid.h5p"
    extract_root = tmp_path / "h5p_extracted" / "valid"

    result = install_h5p_package(
        target,
        contents=contents,
        filename="valid.h5p",
        mime_type="application/x-h5p",
        extract_root=extract_root,
    )

    assert result.title == "Safety Check"
    assert result.main_library == "H5P.TrueFalse"
    assert target.exists()
    assert (extract_root / "h5p.json").exists()
    assert (extract_root / "content" / "content.json").exists()


def test_malformed_h5p_zip_fails():
    with pytest.raises(HTTPException) as exc:
        validate_h5p_package_bytes(b"not a zip", filename="bad.h5p", mime_type="application/x-h5p")

    assert exc.value.status_code == 400


def test_h5p_missing_manifest_fails():
    with pytest.raises(HTTPException) as exc:
        validate_h5p_package_bytes(
            _h5p_zip(include_manifest=False),
            filename="missing.h5p",
            mime_type="application/x-h5p",
        )

    assert "missing h5p.json" in exc.value.detail


def test_h5p_zip_slip_path_fails():
    with pytest.raises(HTTPException) as exc:
        validate_h5p_package_bytes(
            _h5p_zip({"../escape.txt": b"nope"}),
            filename="slip.h5p",
            mime_type="application/x-h5p",
        )

    assert "unsafe path" in exc.value.detail


def test_h5p_blocked_file_type_fails():
    with pytest.raises(HTTPException) as exc:
        validate_h5p_package_bytes(
            _h5p_zip({"content/run.exe": b"nope"}),
            filename="blocked.h5p",
            mime_type="application/x-h5p",
        )

    assert "blocked file type" in exc.value.detail


def test_h5p_version_manifest_resolves_frozen_version(tmp_path: Path):
    metadata = install_h5p_package(
        tmp_path / "v1.h5p",
        contents=_h5p_zip(),
        filename="v1.h5p",
        mime_type="application/x-h5p",
        extract_root=tmp_path / "h5p_extracted" / "stored-v1",
    )
    update_h5p_version_manifest(
        tmp_path,
        asset_id=42,
        asset_version=1,
        stored_name="stored-v1",
        metadata=metadata,
    )
    update_h5p_version_manifest(
        tmp_path,
        asset_id=42,
        asset_version=2,
        stored_name="stored-v2",
        metadata=metadata,
    )

    resolved = resolve_h5p_extract_dir(
        tmp_path,
        asset_id=42,
        asset_version=1,
        current_stored_name="stored-v2",
        current_asset_version=2,
    )

    assert resolved == tmp_path / "h5p_extracted" / "stored-v1"
