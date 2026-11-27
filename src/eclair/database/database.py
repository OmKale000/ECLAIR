"""Database engine and connection management for M14 Provenance & Database."""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from eclair.config import EclairConfig
from eclair.database.models import Base
from eclair.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

DEFAULT_DEV_DATABASE_URL = "sqlite:///:memory:"


def sanitize_database_url(url: str) -> str:
    """Mask credentials in database URL to prevent credential leaking in logs.

    Args:
        url: Database connection string.

    Returns:
        Sanitized database URL with masked password.
    """
    try:
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
            return parsed._replace(netloc=netloc).geturl()
        return url
    except Exception:
        return "<sanitized_database_url>"


def resolve_database_url(
    url: str | None = None,
    config: EclairConfig | None = None,
) -> str:
    """Resolve the database connection URL from parameters, config, or environment.

    Resolution precedence:
    1. Explicit `url` parameter.
    2. Attribute `database_url` on provided `EclairConfig` instance.
    3. Environment variable `ECLAIR_DATABASE_URL`.
    4. Environment variable `DATABASE_URL`.
    5. Safe default: SQLite in-memory for testing/local execution.

    Args:
        url: Optional direct URL override.
        config: Optional shared ECLAIR configuration instance.

    Returns:
        Resolved database connection URL.

    Raises:
        ConfigurationError: If the resolved URL is invalid.
    """
    if url is not None:
        if not url.strip():
            raise ConfigurationError("Database URL cannot be empty or whitespace", code="db_url_empty")
        resolved = url.strip()
    elif config is not None and hasattr(config, "database_url") and getattr(config, "database_url"):
        resolved = str(getattr(config, "database_url")).strip()
    else:
        env_url = os.getenv("ECLAIR_DATABASE_URL") or os.getenv("DATABASE_URL")
        if env_url and env_url.strip():
            resolved = env_url.strip()
        else:
            resolved = DEFAULT_DEV_DATABASE_URL

    if not resolved:
        raise ConfigurationError("Database URL could not be resolved", code="db_url_missing")

    return resolved


def create_db_engine(
    url: str | None = None,
    config: EclairConfig | None = None,
    echo: bool = False,
    **kwargs: Any,
) -> Engine:
    """Create a configured SQLAlchemy 2 engine.

    Args:
        url: Optional connection string override.
        config: Optional shared ECLAIR configuration.
        echo: Whether to enable SQL echo.
        **kwargs: Additional parameters passed to `create_engine`.

    Returns:
        Configured SQLAlchemy Engine.
    """
    db_url = resolve_database_url(url=url, config=config)
    sanitized = sanitize_database_url(db_url)
    logger.debug("Creating database engine with URL: %s", sanitized)

    engine_kwargs: dict[str, Any] = {"echo": echo}

    if db_url.startswith("sqlite"):
        # SQLite specific optimizations for thread safety and memory persistence
        connect_args = kwargs.pop("connect_args", {})
        connect_args.setdefault("check_same_thread", False)
        engine_kwargs["connect_args"] = connect_args
        if ":memory:" in db_url:
            engine_kwargs.setdefault("poolclass", StaticPool)

    engine_kwargs.update(kwargs)
    return create_engine(db_url, **engine_kwargs)


def init_db(engine: Engine) -> None:
    """Create all database tables defined by M14 models.

    Args:
        engine: SQLAlchemy Engine instance.
    """
    Base.metadata.create_all(bind=engine)


def drop_db(engine: Engine) -> None:
    """Drop all tables defined by M14 models (for test teardown).

    Args:
        engine: SQLAlchemy Engine instance.
    """
    Base.metadata.drop_all(bind=engine)
