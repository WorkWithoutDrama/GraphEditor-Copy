"""Pytest config and fixtures for db module tests."""
import os
import tempfile
import pytest

from app.db.base import Base
from app.db.config import DBConfig
from app.db.engine import create_engine_from_config, create_async_engine_from_config
from app.db.session import init_db

# Import models so Base.metadata has all tables
import app.db.models  # noqa: F401


@pytest.fixture
def temp_db_url() -> str:
    """SQLite URL for a temporary file (WAL-friendly)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield f"sqlite:///{path}"
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def db_config(temp_db_url: str) -> DBConfig:
    """DBConfig pointing to temp SQLite file."""
    return DBConfig(db_url=temp_db_url, echo_sql=False)


@pytest.fixture
def sync_engine(db_config: DBConfig):
    """Sync engine for temp DB."""
    return create_engine_from_config(db_config)


@pytest.fixture
def async_engine(db_config: DBConfig):
    """Async engine for temp DB."""
    return create_async_engine_from_config(db_config)


@pytest.fixture
def db_with_tables(sync_engine):
    """Create all tables on the engine (for tests that need schema)."""
    Base.metadata.create_all(sync_engine)
    return sync_engine
