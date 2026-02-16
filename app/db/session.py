"""Session factories and context managers (async-first)."""
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import create_engine

from app.db.config import DBConfig
from app.db.engine import create_engine_from_config, create_async_engine_from_config

# Module-level engines/session factories — set by init_db()
_async_engine = None
_sync_engine = None
AsyncSessionLocal = None
SessionLocal = None


def init_db(cfg: DBConfig | None = None) -> None:
    """Initialize engines and session factories. Call once at app startup."""
    global _async_engine, _sync_engine, AsyncSessionLocal, SessionLocal
    cfg = cfg or DBConfig()
    _async_engine = create_async_engine_from_config(cfg)
    _sync_engine = create_engine_from_config(cfg)
    AsyncSessionLocal = async_sessionmaker(
        bind=_async_engine,
        class_=AsyncSession,
        autoflush=True,
        expire_on_commit=True,
        autocommit=False,
        autobegin=True,
    )
    SessionLocal = sessionmaker(
        bind=_sync_engine,
        autoflush=True,
        expire_on_commit=True,
        autocommit=False,
        autobegin=True,
    )


def get_async_engine():
    return _async_engine


def get_sync_engine():
    return _sync_engine


@asynccontextmanager
async def async_session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Primary async session context: commit on success, rollback + re-raise on exception."""
    if AsyncSessionLocal is None:
        init_db()
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@contextmanager
def session_scope() -> Generator:
    """Sync fallback session context: commit on success, rollback on exception."""
    if SessionLocal is None:
        init_db()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
