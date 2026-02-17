"""Orchestrator-specific exceptions."""


class OrchestratorError(Exception):
    """Base exception for orchestrator failures."""

    def __init__(self, message: str, *, code: str = "ORCHESTRATOR_ERROR") -> None:
        super().__init__(message)
        self.code = code
