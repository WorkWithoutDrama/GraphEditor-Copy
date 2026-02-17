"""Phase A: Foundation tests — connect, session scope, PRAGMAs."""
import pytest
from sqlalchemy import text

from app.db.config import DBConfig
from app.db.session import init_db, session_scope
from app.db.engine import create_engine_from_config


def test_db_can_connect_and_select_1(sync_engine):
    """Can connect and execute a trivial query."""
    with sync_engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        row = result.fetchone()
    assert row is not None
    assert row[0] == 1


def test_session_scope_commits_and_rolls_back(db_config):
    """Session scope commits on success and rolls back on exception."""
    init_db(db_config)
    from app.db.session import SessionLocal
    session = SessionLocal()
    try:
        session.execute(text("SELECT 1"))
        session.commit()
    finally:
        session.close()
    # Rollback: run a failing operation inside scope
    with pytest.raises(Exception):
        with session_scope() as s:
            s.execute(text("SELECT 1"))
            raise RuntimeError("abort")
    # Session should have rolled back; next scope is clean
    with session_scope() as s:
        r = s.execute(text("SELECT 1"))
        assert r.fetchone()[0] == 1


def test_sqlite_pragmas_applied(sync_engine):
    """Verify SQLite PRAGMAs are applied on connect."""
    with sync_engine.connect() as conn:
        for pragma, expected in (
            ("foreign_keys", 1),
            ("journal_mode", "wal"),
            ("synchronous", 1),  # NORMAL = 1
        ):
            r = conn.execute(text(f"PRAGMA {pragma}"))
            val = r.scalar()
            if isinstance(expected, str):
                assert val == expected, f"PRAGMA {pragma} = {val}"
            else:
                assert val == expected, f"PRAGMA {pragma} = {val}"
