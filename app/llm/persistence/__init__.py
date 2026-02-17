"""LLM runs persistence: models and repo. Uses app.db.base.Base."""
from app.llm.persistence.models import LLMRun
from app.llm.persistence.repo import LLMRunRepo

__all__ = ["LLMRun", "LLMRunRepo"]
