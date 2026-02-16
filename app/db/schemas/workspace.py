"""Workspace DTOs and Create schema."""
from pydantic import BaseModel, ConfigDict


class WorkspaceDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str


class WorkspaceCreate(BaseModel):
    name: str
