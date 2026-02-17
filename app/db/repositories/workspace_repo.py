"""Workspace repository."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.workspace import Workspace
from app.db.schemas.workspace import WorkspaceCreate, WorkspaceDTO


class WorkspaceRepo:
    def create(self, session: Session, name: str) -> WorkspaceDTO:
        w = Workspace(name=name)
        session.add(w)
        session.flush()
        return WorkspaceDTO.model_validate(w)

    def get(self, session: Session, id: str) -> WorkspaceDTO | None:
        row = session.get(Workspace, id)
        return WorkspaceDTO.model_validate(row) if row else None

    def get_by_name(self, session: Session, name: str) -> WorkspaceDTO | None:
        row = session.execute(select(Workspace).where(Workspace.name == name)).scalar_one_or_none()
        return WorkspaceDTO.model_validate(row) if row else None
