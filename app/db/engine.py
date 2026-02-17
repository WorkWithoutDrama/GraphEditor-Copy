"""Engine creation with SQLite PRAGMAs."""
from sqlalchemy import event
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.db.config import DBConfig
from app.db.base import Base


def _apply_sqlite_pragmas(dbapi_conn, connection_record, cfg: DBConfig):
    # PRAGMA journal_mode cannot run inside a transaction. Engine is created
    # with isolation_level=None so we're in autocommit here.
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute(f"PRAGMA journal_mode={cfg.sqlite_journal_mode};")
        cursor.execute(f"PRAGMA foreign_keys={'ON' if cfg.sqlite_foreign_keys else 'OFF'};")
        cursor.execute(f"PRAGMA synchronous={cfg.sqlite_synchronous};")
        cursor.execute(f"PRAGMA busy_timeout={cfg.sqlite_busy_timeout_ms};")
    finally:
        cursor.close()


def create_engine_from_config(cfg: DBConfig) -> Engine:
    """Create sync SQLAlchemy engine with SQLite PRAGMAs."""
    # SQLite: isolation_level=None so connection is in autocommit when created,
    # allowing PRAGMA journal_mode=WAL to run (it cannot run inside a transaction).
    connect_args = {"isolation_level": None} if "sqlite" in cfg.db_url else {}
    engine = create_engine(
        cfg.db_url,
        echo=cfg.echo_sql,
        connect_args=connect_args,
    )
    if "sqlite" in cfg.db_url:
        event.listens_for(engine, "connect")(
            lambda c, cr: _apply_sqlite_pragmas(c, cr, cfg)
        )
    return engine


def create_async_engine_from_config(cfg: DBConfig) -> AsyncEngine:
    """Create async SQLAlchemy engine. For SQLite use sqlite+aiosqlite."""
    url = cfg.db_url
    if url.startswith("sqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    elif url.startswith("sqlite:///"):
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    connect_args = {"isolation_level": None} if "sqlite" in url else {}
    engine = create_async_engine(
        url,
        echo=cfg.echo_sql,
        connect_args=connect_args,
    )
    if "sqlite" in url:
        event.listens_for(engine.sync_engine, "connect")(
            lambda c, cr: _apply_sqlite_pragmas(c, cr, cfg)
        )
    return engine
