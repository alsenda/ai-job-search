"""Database engine and session management.

The same code path serves SQLite (local development) and Postgres/Neon
(production); only the connection URL differs.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Create the process-wide engine lazily (so tests can override settings first)."""
    settings = get_settings()
    url = settings.sqlalchemy_url
    if url.startswith("sqlite"):
        # FastAPI may handle requests on different threads than the one that
        # opened the connection; SQLite forbids that unless told otherwise.
        return create_engine(url, connect_args={"check_same_thread": False})
    # pool_pre_ping revalidates pooled connections, which matters on serverless
    # where idle connections are routinely dropped by the platform.
    return create_engine(url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Session factory bound to the engine."""
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: yield a session and always close it afterwards."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Create all tables if they do not exist yet (idempotent)."""
    # Imported here so every model class is registered on Base.metadata
    # before create_all runs.
    from app import models

    models.Base.metadata.create_all(bind=get_engine())
