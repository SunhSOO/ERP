"""Database engine, session, and the declarative base.

ADR-004 makes PostgreSQL the source of truth for business data. Sessions are
synchronous: FastAPI runs a plain ``def`` endpoint in a threadpool, so blocking
database calls there do not stall the event loop. Mixing ``async def`` endpoints
with a blocking driver would, which is why route handlers that touch the
database are written as ``def``.

``LEP_DATABASE_URL`` is the whole configuration surface. Without it the
application refuses to start rather than silently falling back to something that
loses data on restart.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Declarative base for every table in the application."""


def database_url() -> str:
    url = os.getenv("LEP_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "LEP_DATABASE_URL이 없다. 데이터베이스 없이 뜨면 회원가입과 프로젝트가 "
            "재시작에 사라진다."
        )
    return url


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def engine() -> Engine:
    """The process-wide engine, created on first use.

    Lazy so that importing the application does not require a reachable
    database — the architecture tests and the boundary checker import modules
    without one.
    """

    global _engine, _session_factory
    if _engine is None:
        _engine = create_engine(
            database_url(),
            # A dead connection after a database restart otherwise surfaces as a
            # confusing error on the next request.
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            future=True,
        )
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def session_factory() -> sessionmaker[Session]:
    if _session_factory is None:
        engine()
    assert _session_factory is not None
    return _session_factory


@contextmanager
def session_scope() -> Iterator[Session]:
    """A transaction that commits on success and rolls back on any exception."""

    session = session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency. One transaction per request."""

    with session_scope() as session:
        yield session


def as_utc(value: datetime) -> datetime:
    """Return an aware UTC datetime.

    PostgreSQL gives back timezone-aware values for ``TIMESTAMPTZ``; SQLite,
    which the tests use, gives back naive ones. Comparing the two raises, and
    the failure surfaces far from its cause, so every read of a stored timestamp
    goes through here.
    """

    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
