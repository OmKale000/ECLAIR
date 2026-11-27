"""Unit tests for database session management and transactions."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from eclair.database.database import create_db_engine, init_db
from eclair.database.models.query import QueryModel
from eclair.database.session import DatabaseSessionManager, get_session
from eclair.exceptions import ModuleError


@pytest.fixture
def engine():
    eng = create_db_engine("sqlite:///:memory:")
    init_db(eng)
    yield eng
    eng.dispose()


def test_session_commit(engine):
    manager = DatabaseSessionManager(engine=engine)
    with manager.session() as sess:
        query = QueryModel(query_id="q-sess-1", question="What is ECLAIR?")
        sess.add(query)

    # Verify committed in separate session
    with manager.session() as sess:
        saved = sess.get(QueryModel, "q-sess-1")
        assert saved is not None
        assert saved.question == "What is ECLAIR?"


def test_session_rollback_on_exception(engine):
    manager = DatabaseSessionManager(engine=engine)

    with pytest.raises(ValueError, match="Intentional failure"):
        with manager.session() as sess:
            query = QueryModel(query_id="q-rollback-1", question="Rollback question")
            sess.add(query)
            sess.flush()
            raise ValueError("Intentional failure")

    # Verify not committed
    with manager.session() as sess:
        saved = sess.get(QueryModel, "q-rollback-1")
        assert saved is None


def test_session_database_error_wrapped(engine):
    manager = DatabaseSessionManager(engine=engine)

    with pytest.raises(ModuleError) as exc_info:
        with manager.session() as sess:
            # Execute invalid SQL to trigger SQLAlchemyError
            sess.execute(text("SELECT * FROM non_existent_table_xyz"))

    assert exc_info.value.code == "database_transaction_error"


def test_get_session_standalone(engine):
    with get_session(engine=engine) as sess:
        query = QueryModel(query_id="q-standalone-1", question="Standalone test")
        sess.add(query)

    with get_session(engine=engine) as sess:
        saved = sess.get(QueryModel, "q-standalone-1")
        assert saved is not None
        assert saved.query_id == "q-standalone-1"
