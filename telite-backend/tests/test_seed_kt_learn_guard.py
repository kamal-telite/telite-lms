import pytest

from scripts import seed_kt_learn as seed


def test_seed_guard_blocks_production_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(RuntimeError, match="production-like"):
        seed.validate_seed_target("postgresql+psycopg://postgres@localhost:5432/telite_backend")


def test_seed_guard_blocks_staging_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")

    with pytest.raises(RuntimeError, match="production-like"):
        seed.validate_seed_target("postgresql+psycopg://postgres@localhost:5432/telite_backend")


def test_seed_guard_blocks_protected_database_target(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")

    with pytest.raises(RuntimeError, match="protected database target"):
        seed.validate_seed_target("postgresql+psycopg://postgres@localhost:5432/telite_production")


def test_seed_guard_allows_development_target(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")

    seed.validate_seed_target("postgresql+psycopg://postgres@localhost:55432/telite_backend")


def test_seed_engine_creation_validates_before_connecting(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")

    def fail_create_engine(_db_url):
        raise AssertionError("create_engine should not be called for blocked targets")

    monkeypatch.setattr(seed, "create_engine", fail_create_engine)

    with pytest.raises(RuntimeError, match="production-like"):
        seed.create_seed_engine("postgresql+psycopg://postgres@localhost:5432/telite_backend")
