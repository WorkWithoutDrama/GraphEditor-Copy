"""Worker: consumes docling.extract jobs, runs conversion → export → chunking → persist → embed enqueue (plan B5, Phase C)."""
import logging

from app.db.session import session_scope
from app.modules.docling.adapters.jobs import get_in_memory_queues
from app.modules.docling.factory import create_docling_service

logger = logging.getLogger(__name__)


def process_one_docling_extract_job(job: dict) -> None:
    """Process a single docling.extract job: run_extract in its own session."""
    with session_scope() as session:
        service = create_docling_service(session)
        service.run_extract(job)


def worker_tick() -> int:
    """
    Consume all pending docling.extract jobs from the in-memory queue and process each.
    Returns the number of jobs processed.
    """
    queues = get_in_memory_queues()
    pending = queues.get("docling.extract", [])
    if not pending:
        return 0
    # Drain the list (worker owns consumption)
    jobs = list(pending)
    del pending[:]
    for job in jobs:
        try:
            process_one_docling_extract_job(job)
        except Exception as e:
            logger.exception("Worker failed to process docling.extract job: %s", e)
    return len(jobs)
