"""Database engine, session factory and declarative base.

Synchronous SQLAlchemy is used deliberately: scaling is horizontal (many small
single-purpose containers), so a simple, robust sync stack is preferable to an
async one with more moving parts. FastAPI runs sync dependencies in a
threadpool, which is more than sufficient at this granularity.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


_engine = create_engine(
    settings.database_url,
    pool_size=settings.api_db_pool_size,
    max_overflow=settings.api_db_max_overflow,
    pool_pre_ping=True,
    echo=settings.api_db_echo,
    future=True,
)

SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False, future=True)


def get_engine():
    return _engine


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session with commit/rollback."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
