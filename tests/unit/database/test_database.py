"""Unit tests for database engine and connection management."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from eclair.database.database import (
    DEFAULT_DEV_DATABASE_URL,
    create_db_engine,
    drop_db,
    init_db,
    resolve_database_url,
    sanitize_database_url,
)
from eclair.exceptions import ConfigurationError


def test_sanitize_database_url():
    url_with_pass = "postgresql://user:secretpass@localhost:5432/eclair_db"
    sanitized = sanitize_database_url(url_with_pass)
    assert "secretpass" not in sanitized
    assert ":***@" in sanitized

    url_without_pass = "sqlite:///:memory:"
    assert sanitize_database_url(url_without_pass) == "sqlite:///:memory:"


def test_resolve_database_url_precedence(monkeypatch):
    # 1. Explicit override
    assert resolve_database_url("sqlite:///explicit.db") == "sqlite:///explicit.db"

    # 2. Config attribute
    class DummyConfig:
        database_url = "sqlite:///config.db"

    assert resolve_database_url(config=DummyConfig()) == "sqlite:///config.db"

    # 3. Environment variable ECLAIR_DATABASE_URL
    monkeypatch.setenv("ECLAIR_DATABASE_URL", "sqlite:///env_eclair.db")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert resolve_database_url() == "sqlite:///env_eclair.db"

    # 4. Environment variable DATABASE_URL
    monkeypatch.delenv("ECLAIR_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///env_generic.db")
    assert resolve_database_url() == "sqlite:///env_generic.db"

    # 5. Default fallback
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert resolve_database_url() == DEFAULT_DEV_DATABASE_URL


def test_resolve_database_url_empty_raises():
    with pytest.raises(ConfigurationError):
        resolve_database_url(url="   ")


def test_create_db_engine_and_init():
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)

    # Verify tables were created
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
        table_names = {row[0] for row in result}
        assert "queries" in table_names
        assert "claims" in table_names
        assert "evidence" in table_names
        assert "verifications" in table_names
        assert "confidences" in table_names
        assert "audit_logs" in table_names

    drop_db(engine)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
        table_names = {row[0] for row in result}
        assert "queries" not in table_names
