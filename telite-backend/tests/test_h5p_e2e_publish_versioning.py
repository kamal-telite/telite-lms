from types import SimpleNamespace

from app.repositories.publishing_repo import freeze_h5p_block_settings


def _h5p_block(settings: dict | None = None):
    return SimpleNamespace(
        block_type="h5p",
        media_asset_id=45,
        metadata_json=settings or {},
    )


def _h5p_asset(version: int, filename: str):
    return SimpleNamespace(
        id=45,
        asset_version=version,
        filename=filename,
        mime_type="application/x-h5p",
        deleted_at=None,
    )


def _published_snapshot(settings: dict) -> dict:
    return {
        "sections": [
            {
                "id": 1,
                "title": "Section 1",
                "modules": [
                    {
                        "id": 10,
                        "title": "Module 1",
                        "blocks": [
                            {
                                "id": 100,
                                "block_type": "h5p",
                                "media_asset_id": 45,
                                "settings": settings,
                            }
                        ],
                    }
                ],
            }
        ]
    }


def _snapshot_h5p_settings(snapshot: dict) -> dict:
    return snapshot["sections"][0]["modules"][0]["blocks"][0]["settings"]


def test_h5p_publish_replace_republish_freezes_asset_version():
    block = _h5p_block()

    first_publish_settings = freeze_h5p_block_settings(block, _h5p_asset(1, "activity_v1.h5p"))
    published_v1 = _published_snapshot(first_publish_settings)

    replaced_asset = _h5p_asset(2, "activity_v2.h5p")

    assert _snapshot_h5p_settings(published_v1)["asset_id"] == 45
    assert _snapshot_h5p_settings(published_v1)["asset_version"] == 1
    assert _snapshot_h5p_settings(published_v1)["filename"] == "activity_v1.h5p"

    republish_settings = freeze_h5p_block_settings(_h5p_block(), replaced_asset)
    published_v2 = _published_snapshot(republish_settings)

    assert _snapshot_h5p_settings(published_v1)["asset_version"] == 1
    assert _snapshot_h5p_settings(published_v1)["filename"] == "activity_v1.h5p"
    assert _snapshot_h5p_settings(published_v2)["asset_version"] == 2
    assert _snapshot_h5p_settings(published_v2)["filename"] == "activity_v2.h5p"
