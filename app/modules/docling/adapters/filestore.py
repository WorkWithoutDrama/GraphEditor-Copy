"""File store adapter for derived outputs (docling JSON, plain text, markdown)."""
import os
from pathlib import Path


class LocalFileStoreAdapter:
    """Writes to local directory; key -> path. Returns file:// URI."""

    def __init__(self, base_dir: str | Path) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, key: str, data: bytes) -> str:
        path = self._base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path.as_uri()

    def open_stream(self, uri: str):
        from urllib.request import url2pathname
        from urllib.parse import urlparse
        parsed = urlparse(uri)
        if parsed.scheme == "file":
            path = url2pathname(parsed.path)
            return open(path, "rb")
        raise ValueError(f"Unsupported URI scheme: {uri}")
