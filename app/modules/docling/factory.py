"""Factory for DoclingService with session-bound adapters (shared by API and worker)."""
import tempfile

from app.modules.docling.adapters import (
    ChunkRepoAdapter,
    DocumentRepoAdapter,
    ExtractRunsAdapter,
    LocalFileStoreAdapter,
    InMemoryJobPublisher,
    LocalSourceContentAdapter,
)
from app.modules.docling.service import DoclingService
from app.modules.docling.settings import DoclingSettings


def default_file_store():
    return LocalFileStoreAdapter(tempfile.gettempdir() + "/docling_artifacts")


def default_job_publisher():
    return InMemoryJobPublisher()


def create_docling_service(session, file_store=None, job_publisher=None, settings=None):
    """Build DoclingService with adapters bound to the given session."""
    settings = settings or DoclingSettings()
    file_store = file_store or default_file_store()
    job_publisher = job_publisher or default_job_publisher()
    return DoclingService(
        document_repo=DocumentRepoAdapter(session),
        extract_runs=ExtractRunsAdapter(session),
        chunk_repo=ChunkRepoAdapter(session),
        file_store=file_store,
        job_publisher=job_publisher,
        source_content=LocalSourceContentAdapter(session),
        settings=settings,
    )
