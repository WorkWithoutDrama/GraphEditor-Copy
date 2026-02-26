"""Testable clock for timestamps."""
from datetime import datetime, timezone
from typing import Callable

# Default: real UTC now. Tests can override.
_utc_now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)


def set_utc_now(fn: Callable[[], datetime]) -> None:
    global _utc_now
    _utc_now = fn


def utc_now() -> datetime:
    return _utc_now()
