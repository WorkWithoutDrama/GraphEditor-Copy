"""Vector store exceptions."""


class VectorStoreError(Exception):
    """Base exception for vector store operations."""


class VectorSchemaMismatchError(VectorStoreError):
    """Raised when collection vector size or distance does not match expectations.

    Indicates a migration (new collection + reindex) is required.
    """


class VectorStoreConnectionError(VectorStoreError):
    """Raised when connection to Qdrant fails (transient)."""
