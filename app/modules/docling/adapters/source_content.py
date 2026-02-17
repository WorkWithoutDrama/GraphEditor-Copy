"""Source content adapter: read raw file from SourceVersion storage."""
from urllib.parse import urlparse
from urllib.request import url2pathname

from sqlalchemy.orm import Session

from app.db.repositories.source_repo import SourceVersionRepo


class LocalSourceContentAdapter:
    """Resolves SourceVersion.storage_uri and opens as local file. Supports file:// or path."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._source_version_repo = SourceVersionRepo()

    def open_raw_stream(self, source_version_id: str):
        """Return file-like for raw content. Caller must close."""
        dto = self._source_version_repo.get(self._session, source_version_id)
        if not dto:
            raise FileNotFoundError(f"SourceVersion not found: {source_version_id}")
        uri = dto.storage_uri
        if uri.startswith("file://"):
            parsed = urlparse(uri)
            path = url2pathname(parsed.path)
            return open(path, "rb")
        return open(uri, "rb")
