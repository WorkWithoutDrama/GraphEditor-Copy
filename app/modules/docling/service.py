"""Docling service: enqueue_extract, run_extract, get_status, rechunk, backfill. No SQLAlchemy, no Docling imports here."""
import json
import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from app.modules.docling.ids import idempotency_key
from app.modules.docling.schemas import (
    DoclingExtractPayload,
    EmbedDocumentChunksPayload,
    IngestResponse,
)

logger = logging.getLogger(__name__)

# Docling runtime version for extractor_version (pin in requirements)
DOCLING_EXTRACTOR_VERSION = "2.73.1"


def _docling_extractor_version() -> str:
    try:
        import docling
        return getattr(docling, "__version__", DOCLING_EXTRACTOR_VERSION)
    except Exception:
        return DOCLING_EXTRACTOR_VERSION


class DoclingService:
    """Orchestrates ingest: enqueue, run_extract (worker), get_status. Depends on ports only."""

    def __init__(
        self,
        *,
        document_repo: Any,
        extract_runs: Any,
        chunk_repo: Any,
        file_store: Any,
        job_publisher: Any,
        source_content: Any,
        tokenizer_resolver: Any = None,
        settings: Any = None,
    ) -> None:
        self._document_repo = document_repo
        self._extract_runs = extract_runs
        self._chunk_repo = chunk_repo
        self._file_store = file_store
        self._job_publisher = job_publisher
        self._source_content = source_content
        self._tokenizer_resolver = tokenizer_resolver
        self._settings = settings

    def enqueue_extract(
        self,
        workspace_id: str,
        source_version_id: str,
        embedding_set_id: str,
        trace_id: str | None = None,
    ) -> IngestResponse:
        """Create/update extract_runs to QUEUED and publish docling.extract job. Returns response."""
        extractor = "docling"
        extractor_version = _docling_extractor_version()
        run = self._extract_runs.get_or_create_run(
            workspace_id=workspace_id,
            source_version_id=source_version_id,
            extractor=extractor,
            extractor_version=extractor_version,
            status="QUEUED",
            trace_id=trace_id,
        )
        job_id = str(uuid4())
        created_at = datetime.now(tz=timezone.utc).isoformat()
        key = idempotency_key(
            workspace_id, source_version_id, "docling.extract", extractor, extractor_version
        )
        payload = DoclingExtractPayload(
            type="docling.extract",
            job_id=job_id,
            attempt=1,
            created_at=created_at,
            trace_id=trace_id or job_id,
            idempotency_key=key,
            workspace_id=workspace_id,
            source_version_id=source_version_id,
            extractor=extractor,
            extractor_version=extractor_version,
            embedding_set_id=embedding_set_id,
        )
        self._job_publisher.publish("docling.extract", payload.model_dump(mode="json"))
        return IngestResponse(
            source_version_id=source_version_id,
            extractor=extractor,
            extractor_version=extractor_version,
            status="QUEUED",
        )

    def run_extract(self, job: dict[str, Any]) -> None:
        """Worker entry: conversion -> export -> chunking -> persist -> embed enqueue."""
        import time as _time
        from app.modules.docling.converter import run_conversion
        from app.modules.docling.artifacts import export_artifacts_and_persist_document
        from app.modules.docling.chunking import chunk_document
        from app.modules.docling import errors as docling_errors
        from app.modules.docling import metrics as docling_metrics

        workspace_id = job["workspace_id"]
        source_version_id = job["source_version_id"]
        extractor = job.get("extractor", "docling")
        extractor_version = job.get("extractor_version", DOCLING_EXTRACTOR_VERSION)
        embedding_set_id = job["embedding_set_id"]
        run_id = None
        run = self._extract_runs.get_run(
            workspace_id, source_version_id, extractor, extractor_version
        )
        if run:
            run_id = run.id
        if not run_id:
            run = self._extract_runs.get_or_create_run(
                workspace_id, source_version_id, extractor, extractor_version, status="RUNNING"
            )
            run_id = run.id

        started_at = datetime.now(tz=timezone.utc)
        self._extract_runs.update_run_status(run_id, "RUNNING", started_at=started_at)
        run_start = _time.perf_counter()
        document_id: str | None = None
        chunk_count: int | None = None

        try:
            # Phase C: convert
            docling_doc = run_conversion(
                job,
                self._source_content,
                self._extract_runs,
                run_id,
                self._settings,
            )
            if docling_doc is None:
                return
            logger.info(
                "docling checkpoint",
                extra={
                    "stage": "PARSED",
                    "source_version_id": source_version_id,
                    "duration_ms": int((_time.perf_counter() - run_start) * 1000),
                },
            )

            # Phase D: export artifacts and persist Document
            t_d = _time.perf_counter()
            document_id = export_artifacts_and_persist_document(
                docling_doc,
                source_version_id,
                extractor,
                extractor_version,
                self._file_store,
                self._document_repo,
                self._extract_runs,
                run_id,
                self._settings,
            )
            if document_id is None:
                return
            logger.info(
                "docling checkpoint",
                extra={
                    "document_id": document_id,
                    "stage": "ARTIFACTS_STORED",
                    "source_version_id": source_version_id,
                    "duration_ms": int((_time.perf_counter() - t_d) * 1000),
                },
            )

            # Phase E + F: chunk and persist
            t_e = _time.perf_counter()
            chunker_version, chunk_count = chunk_document(
                docling_doc,
                document_id,
                self._chunk_repo,
                self._file_store,
                self._extract_runs,
                run_id,
                self._tokenizer_resolver,
                self._settings,
                embedding_set_id=embedding_set_id,
            )
            if chunker_version is None:
                return
            logger.info(
                "docling checkpoint",
                extra={
                    "document_id": document_id,
                    "stage": "CHUNKED",
                    "source_version_id": source_version_id,
                    "duration_ms": int((_time.perf_counter() - t_e) * 1000),
                    "chunk_count": chunk_count,
                },
            )

            # Phase G: handoff to embeddings
            self._publish_embed_job(
                job, workspace_id, embedding_set_id, document_id, chunker_version
            )
            self._extract_runs.update_run_status(run_id, "EMBED_ENQUEUED")
            self._extract_runs.update_run_status(run_id, "COMPLETED", finished_at=datetime.now(tz=timezone.utc))
            logger.info(
                "docling checkpoint",
                extra={
                    "document_id": document_id,
                    "stage": "COMPLETED",
                    "source_version_id": source_version_id,
                    "duration_ms": int((_time.perf_counter() - run_start) * 1000),
                    "chunk_count": chunk_count,
                },
            )
        except Exception as e:
            logger.exception("run_extract failed: %s", e)
            code = getattr(e, "error_code", docling_errors.DoclingErrorCode.PARSE_FAILED)
            docling_metrics.record_ingest_failure(str(code))
            self._extract_runs.update_run_status(
                run_id,
                "FAILED",
                error_code=str(code),
                error_message=str(e)[:4096],
                finished_at=datetime.now(tz=timezone.utc),
            )

    def _publish_embed_job(
        self,
        job: dict,
        workspace_id: str,
        embedding_set_id: str,
        document_id: str,
        chunker_version: str,
    ) -> None:
        from uuid import uuid4
        created_at = datetime.now(tz=timezone.utc).isoformat()
        trace_id = job.get("trace_id", str(uuid4()))
        key = idempotency_key(
            workspace_id,
            job.get("source_version_id", ""),
            "embeddings.embed_document_chunks",
            "docling",
            job.get("extractor_version", ""),
        )
        payload = EmbedDocumentChunksPayload(
            type="embeddings.embed_document_chunks",
            job_id=str(uuid4()),
            attempt=1,
            created_at=created_at,
            trace_id=trace_id,
            idempotency_key=key,
            workspace_id=workspace_id,
            source_version_id=job.get("source_version_id"),
            embedding_set_id=embedding_set_id,
            document_id=document_id,
            chunker_version=chunker_version,
        )
        self._job_publisher.publish("embeddings.embed_document_chunks", payload.model_dump(mode="json"))

    def get_status(
        self,
        workspace_id: str,
        source_version_id: str,
        extractor: str = "docling",
        extractor_version: str | None = None,
    ) -> dict[str, Any] | None:
        """Read extract_runs + optional Document/Chunk summary."""
        version = extractor_version or _docling_extractor_version()
        run = self._extract_runs.get_run(workspace_id, source_version_id, extractor, version)
        if not run:
            return None
        return {
            "run_id": run.id,
            "status": run.status,
            "attempt": run.attempt,
            "error_code": run.error_code,
            "error_message": run.error_message,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        }

    def rechunk(
        self,
        workspace_id: str,
        document_id: str,
        embedding_set_id: str,
        chunk_settings: dict[str, Any],
    ) -> None:
        """Rechunk document from structure JSON with new chunk_settings; persist chunks and enqueue embed job (plan I2)."""
        from app.modules.docling.chunking import chunk_document

        doc_dto = self._document_repo.get_document(document_id)
        if not doc_dto:
            raise ValueError(f"Document not found: {document_id}")
        structure_uri = getattr(doc_dto, "structure_json_uri", None)
        if not structure_uri:
            raise ValueError(
                f"Document {document_id} has no structure_json_uri; reconvert from source first."
            )
        try:
            stream = self._file_store.open_stream(structure_uri)
            data = stream.read()
            stream.close()
        except Exception as e:
            raise ValueError(f"Cannot read structure JSON for {document_id}: {e}") from e
        try:
            doc_dict = json.loads(data.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Invalid structure JSON for {document_id}: {e}") from e
        try:
            from docling_core.types.doc import DoclingDocument
            docling_doc = DoclingDocument.from_dict(doc_dict)
        except ImportError:
            from docling.datamodel.pydantic_models import DoclingDocument
            docling_doc = DoclingDocument.model_validate(doc_dict)
        except Exception as e:
            raise ValueError(f"Failed to load DoclingDocument for {document_id}: {e}") from e

        base = getattr(self._settings, "__dict__", {}) if self._settings else {}
        merged = {**base, **chunk_settings}
        rechunk_settings = SimpleNamespace(**merged)

        class _NoOpExtractRuns:
            def get_or_create_run(self, *a, **k):
                return SimpleNamespace(id="rechunk-fake")
            def get_run(self, *a, **k):
                return None
            def update_run_status(self, *a, **k):
                pass
        no_op = _NoOpExtractRuns()

        chunker_version, chunk_count = chunk_document(
            docling_doc,
            document_id,
            self._chunk_repo,
            self._file_store,
            no_op,
            "rechunk-fake",
            self._tokenizer_resolver,
            rechunk_settings,
            embedding_set_id=embedding_set_id,
        )
        if chunker_version is None:
            raise RuntimeError("Rechunk chunking failed")
        job = {
            "source_version_id": getattr(doc_dto, "source_version_id", ""),
            "trace_id": str(uuid4()),
            "extractor_version": _docling_extractor_version(),
        }
        self._publish_embed_job(
            job, workspace_id, embedding_set_id, document_id, chunker_version
        )

    def backfill(
        self,
        embedding_set_id: str,
        limit_failed_queued: int = 500,
        limit_chunked: int = 500,
    ) -> dict[str, int]:
        """Requeue FAILED/QUEUED runs as docling.extract; enqueue CHUNKED (not fully indexed) for embed (plan I4). Returns counts enqueued."""
        enqueued_extract = 0
        enqueued_embed = 0
        for run in self._extract_runs.list_by_status(
            ["FAILED", "QUEUED"], limit=limit_failed_queued
        ):
            payload = DoclingExtractPayload(
                type="docling.extract",
                job_id=str(uuid4()),
                attempt=1,
                created_at=datetime.now(tz=timezone.utc).isoformat(),
                trace_id=getattr(run, "trace_id", None) or str(uuid4()),
                idempotency_key=idempotency_key(
                    getattr(run, "workspace_id", ""),
                    getattr(run, "source_version_id", ""),
                    "docling.extract",
                    getattr(run, "extractor", "docling"),
                    getattr(run, "extractor_version", ""),
                ),
                workspace_id=getattr(run, "workspace_id", ""),
                source_version_id=getattr(run, "source_version_id", ""),
                extractor=getattr(run, "extractor", "docling"),
                extractor_version=getattr(run, "extractor_version", ""),
                embedding_set_id=embedding_set_id,
            )
            self._job_publisher.publish(
                "docling.extract", payload.model_dump(mode="json")
            )
            enqueued_extract += 1
        for run in self._extract_runs.list_by_status(
            ["CHUNKED"], limit=limit_chunked
        ):
            chunker_version = getattr(run, "chunker_version", None)
            if not chunker_version:
                continue
            docs = self._document_repo.list_documents_by_source_version(
                getattr(run, "source_version_id", "")
            )
            doc = next(
                (
                    d
                    for d in docs
                    if getattr(d, "extractor", None) == getattr(run, "extractor")
                    and getattr(d, "extractor_version", None)
                    == getattr(run, "extractor_version")
                ),
                None,
            )
            if not doc:
                continue
            document_id = getattr(doc, "id", None)
            if not document_id:
                continue
            job = {
                "source_version_id": getattr(run, "source_version_id", ""),
                "trace_id": str(uuid4()),
                "extractor_version": getattr(run, "extractor_version", ""),
            }
            self._publish_embed_job(
                job,
                getattr(run, "workspace_id", ""),
                embedding_set_id,
                document_id,
                chunker_version,
            )
            enqueued_embed += 1
        return {"enqueued_extract": enqueued_extract, "enqueued_embed": enqueued_embed}
