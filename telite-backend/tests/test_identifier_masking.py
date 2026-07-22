import logging
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import MultipleResultsFound

from app.core.identifier_masking import mask_identifier
from app.repositories.user_repo import IdentifierCollisionError, UserRepository


def test_mask_identifier_redacts_email_local_part():
    assert mask_identifier("Sensitive.User@example.com") == "s***r@example.com"


def test_mask_identifier_redacts_username():
    assert mask_identifier("globaladmin") == "g***n"


def test_auth_collision_log_masks_identifier(monkeypatch, caplog):
    monkeypatch.setenv("TELITE_DB_BACKEND", "sqlite")
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.side_effect = MultipleResultsFound("collision")
    session.execute.return_value = result
    repo = UserRepository(session)

    with caplog.at_level(logging.ERROR, logger="app.repositories.user_repo"):
        with pytest.raises(IdentifierCollisionError):
            repo.get_by_identifier_for_auth("same@test.com")

    log_text = caplog.text
    assert "same@test.com" not in log_text
    assert "s***e@test.com" in log_text
    assert "MultipleResultsFound" in log_text


def test_general_lookup_collision_masks_identifier(monkeypatch, caplog):
    monkeypatch.setenv("TELITE_DB_BACKEND", "sqlite")
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.side_effect = MultipleResultsFound("collision")
    session.execute.return_value = result
    repo = UserRepository(session)

    with caplog.at_level(logging.ERROR, logger="app.repositories.user_repo"):
        with pytest.raises(IdentifierCollisionError):
            repo.get_by_identifier("same@test.com")

    log_text = caplog.text
    assert "same@test.com" not in log_text
    assert "s***e@test.com" in log_text
    assert "MultipleResultsFound" in log_text