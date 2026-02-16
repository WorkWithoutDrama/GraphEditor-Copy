"""DB configuration (pydantic-settings)."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DBConfig(BaseSettings):
    """Database configuration. Load from env with prefix DB_ or from .env."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_url: str = Field(default="sqlite:///./data/app.db", description="Database URL")
    echo_sql: bool = Field(default=False, description="Echo SQL statements")
    # pool_pre_ping has no effect on SQLite (NullPool); used when migrating to Postgres.
    pool_pre_ping: bool = Field(default=True, description="Pre-ping connections (Postgres only)")
    sqlite_busy_timeout_ms: int = Field(default=5000, description="SQLite busy timeout in ms")
    sqlite_journal_mode: str = Field(default="WAL", description="SQLite journal_mode PRAGMA")
    sqlite_synchronous: str = Field(default="NORMAL", description="SQLite synchronous PRAGMA")
    sqlite_foreign_keys: bool = Field(default=True, description="SQLite foreign_keys PRAGMA")
