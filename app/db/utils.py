"""DB utilities: stable JSON serialization, IntegrityError → ConflictError."""
import json
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.db.exceptions import ConflictError


def json_serialize(obj: Any) -> str:
    """Stable JSON for DB TEXT columns: sort_keys, no extra whitespace, UTC datetimes."""
    return json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=_json_default,
    )


def _json_default(o: Any) -> Any:
    if isinstance(o, (datetime, date)):
        if isinstance(o, datetime) and o.tzinfo is None:
            o = o.replace(tzinfo=timezone.utc)
        elif isinstance(o, datetime):
            o = o.astimezone(timezone.utc)
        return o.isoformat()
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def wrap_integrity_error(fn):
    """Decorator that wraps IntegrityError in ConflictError."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except IntegrityError as e:
            raise ConflictError(f"Constraint violation: {e.orig}") from e
    return wrapper
