"""
SQLAlchemy engine, session factory, and DB utilities.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from src.config import get_settings

settings = get_settings()

_IS_SQLITE = settings.database_url.startswith("sqlite")

connect_args = {"check_same_thread": False} if _IS_SQLITE else {}

# Use NullPool for SQLite (no pooling needed), QueuePool for others
poolclass = NullPool if _IS_SQLITE else QueuePool
pool_args = {} if _IS_SQLITE else {"pool_size": 5, "max_overflow": 10}

engine: Engine = create_engine(
    settings.database_url,
    poolclass=poolclass,
    **pool_args,
    future=True,
    echo=settings.api_debug,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)

Base = declarative_base()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Provide a transactional scope around a series of operations.
    """

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def db_healthcheck() -> bool:
    """
    Execute a lightweight query to ensure the database is reachable.
    """

    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
