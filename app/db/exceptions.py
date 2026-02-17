"""DB-specific exceptions for clearer error handling."""


class DbError(Exception):
    """Base exception for DB layer errors."""


class NotFoundError(DbError):
    """Requested entity was not found."""


class ConflictError(DbError):
    """Uniqueness or constraint violation (e.g. duplicate key)."""
