import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

import app.services.assignment_storage as assignment_storage
from app.services.assignment_storage import LocalStorageProvider


def make_upload(filename, content, content_type):
    return UploadFile(filename=filename, file=BytesIO(content), headers={"content-type": content_type})


def test_local_assignment_storage_uploads_under_org_block_and_learner(tmp_path):
    provider = LocalStorageProvider(root=tmp_path)
    upload = make_upload("My Essay.pdf", b"%PDF-1.4 assignment", "application/pdf")

    stored = asyncio.run(
        provider.upload(org_id=7, block_id=11, learner_id="learner@example.com", file=upload)
    )

    resolved = provider.resolve(stored.file_path)
    assert resolved.is_file()
    assert resolved.read_bytes() == b"%PDF-1.4 assignment"
    assert stored.file_path.startswith("7/assignments/11/learner_example.com/")
    assert stored.original_filename == "My Essay.pdf"
    assert stored.mime_type == "application/pdf"
    assert stored.file_size == len(b"%PDF-1.4 assignment")


def test_local_assignment_storage_rejects_disallowed_file_types(tmp_path):
    provider = LocalStorageProvider(root=tmp_path)
    upload = make_upload("payload.exe", b"not allowed", "application/octet-stream")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(provider.upload(org_id=1, block_id=2, learner_id="learner", file=upload))

    assert exc.value.status_code == 400
    assert "File type" in exc.value.detail


def test_local_assignment_storage_blocks_path_traversal_on_download(tmp_path):
    provider = LocalStorageProvider(root=tmp_path)
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(HTTPException) as exc:
        provider.resolve("../outside.txt")

    assert exc.value.status_code == 404


def test_local_assignment_storage_enforces_max_file_size(tmp_path, monkeypatch):
    provider = LocalStorageProvider(root=tmp_path)
    monkeypatch.setattr(assignment_storage, "MAX_ASSIGNMENT_FILE_BYTES", 4)
    upload = make_upload("oversized.pdf", b"12345", "application/pdf")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(provider.upload(org_id=1, block_id=2, learner_id="learner", file=upload))

    assert exc.value.status_code == 400
    assert "too large" in exc.value.detail


def test_local_assignment_storage_duplicate_uploads_get_unique_paths(tmp_path):
    provider = LocalStorageProvider(root=tmp_path)
    first = make_upload("essay.pdf", b"first", "application/pdf")
    second = make_upload("essay.pdf", b"second", "application/pdf")

    stored_first = asyncio.run(provider.upload(org_id=1, block_id=2, learner_id="learner", file=first))
    stored_second = asyncio.run(provider.upload(org_id=1, block_id=2, learner_id="learner", file=second))

    assert stored_first.file_path != stored_second.file_path
    assert provider.resolve(stored_first.file_path).read_bytes() == b"first"
    assert provider.resolve(stored_second.file_path).read_bytes() == b"second"


def test_local_assignment_storage_delete_removes_file(tmp_path):
    provider = LocalStorageProvider(root=tmp_path)
    upload = make_upload("essay.pdf", b"delete me", "application/pdf")
    stored = asyncio.run(provider.upload(org_id=1, block_id=2, learner_id="learner", file=upload))

    provider.delete(stored.file_path)

    with pytest.raises(HTTPException) as exc:
        provider.resolve(stored.file_path)
    assert exc.value.status_code == 404


def test_local_assignment_storage_calls_antivirus_hook(tmp_path, monkeypatch):
    provider = LocalStorageProvider(root=tmp_path)
    scanned = {}

    def fake_scan(filename, contents):
        scanned["filename"] = filename
        scanned["contents"] = contents

    monkeypatch.setattr(assignment_storage, "_scan_file_for_threats", fake_scan)
    upload = make_upload("scan-me.pdf", b"scan payload", "application/pdf")

    asyncio.run(provider.upload(org_id=1, block_id=2, learner_id="learner", file=upload))

    assert scanned == {"filename": "scan-me.pdf", "contents": b"scan payload"}
