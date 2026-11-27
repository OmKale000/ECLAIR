"""Database session and transaction management for M14 Provenance & Database."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from eclair.database.database import create_db_engine
from eclair.exceptions import ModuleError


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a configured sessionmaker bound to the given engine.

    Args:
        engine: SQLAlchemy Engine instance.

    Returns:
        Configured sessionmaker producing Session instances.
    """
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


class DatabaseSessionManager:
    """Manages database connection lifecycle and transaction sessions."""

    def __init__(
        self,
        engine: Engine | None = None,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        """Initialize session manager.

        Args:
            engine: Optional SQLAlchemy Engine. If omitted, default engine is created.
            session_factory: Optional sessionmaker instance.
        """
        self.engine = engine or create_db_engine()
        self.session_factory = session_factory or create_session_factory(self.engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provide a transactional session scope around a series of operations.

        Yields:
            SQLAlchemy Session.

        Raises:
            ModuleError: Wrapped error if a database exception occurs.
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            raise ModuleError(
                f"Database transaction failed: {exc}",
                code="database_transaction_error",
            ) from exc
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


@contextmanager
def get_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    """Standalone context manager for acquiring a database session.

    Args:
        engine: Optional SQLAlchemy engine.

    Yields:
        Active SQLAlchemy Session.
    """
    manager = DatabaseSessionManager(engine=engine)
    with manager.session() as sess:
        yield sess
