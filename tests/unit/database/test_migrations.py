"""Unit tests for Alembic database migration execution."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


@pytest.fixture
def temp_db_config(tmp_path):
    db_file = tmp_path / "test_migration.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    repo_root = Path(__file__).resolve().parents[3]
    ini_path = repo_root / "deployment" / "migrations" / "alembic" / "alembic.ini"

    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(repo_root / "deployment" / "migrations" / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)

    yield cfg, db_url


def test_alembic_upgrade_and_downgrade(temp_db_config):
    cfg, db_url = temp_db_config

    # Test upgrade to head
    command.upgrade(cfg, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    expected_tables = {
        "queries",
        "claims",
        "evidence",
        "verifications",
        "confidences",
        "consensus_records",
        "risks",
        "decisions",
        "feedbacks",
        "audit_logs",
    }
    assert expected_tables.issubset(set(tables))

    # Verify column presence on queries table
    columns = {c["name"] for c in inspector.get_columns("queries")}
    assert {"query_id", "question", "final_answer", "created_at"}.issubset(columns)

    # Test downgrade to base
    command.downgrade(cfg, "base")

    inspector = inspect(engine)
    tables_after = inspector.get_table_names()
    for t in expected_tables:
        assert t not in tables_after

    engine.dispose()
