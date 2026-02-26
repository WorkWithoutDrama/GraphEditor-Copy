"""Workspace ORM model."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin


class Workspace(Base, IdMixin, TimestampMixin):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    sources: Mapped[list["Source"]] = relationship(
        "Source",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
