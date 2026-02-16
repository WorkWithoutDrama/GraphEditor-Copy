"""SQLAlchemy Base, mixins, and naming conventions."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Naming conventions for constraints/indexes — keeps Alembic diffs stable
convention = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base with shared metadata and conventions."""

    metadata = metadata


class IdMixin:
    """Mixin providing TEXT primary key id (UUID string)."""

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))


class TimestampMixin:
    """Mixin providing created_at and updated_at in UTC."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.datetime("now"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
        server_default=func.datetime("now"),
    )
