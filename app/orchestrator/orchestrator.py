"""MVP Orchestrator: run_file_ingestion and process_one_chunk."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.config import DBConfig
from app.db.models.chunk import Chunk
from app.db.models.document import Document
from app.db.models.embedding import EmbeddingSet
from app.db.models.source import Source, SourceVersion
from app.db.repositories.chunk_repo import ChunkRepo
from app.db.repositories.embedding_repo import EmbeddingSetRepo
from app.db.repositories.pipeline_run_repo import (
    ChunkExtractionRepo,
    ChunkRunRepo,
    PipelineRunRepo,
)
from app.db.repositories.source_repo import SourceRepo, SourceVersionRepo
from app.db.repositories.workspace_repo import WorkspaceRepo
from app.db.session import init_db, session_scope
from app.embeddings import EmbedSettings, OllamaEmbedClient
from app.llm import LLMService
from app.llm.settings import LLMSettings
from app.llm.types import LLMMessage, LLMRequest, LLMProfile
from app.modules.docling.adapters import (
    ChunkRepoAdapter,
    DocumentRepoAdapter,
    ExtractRunsAdapter,
    LocalFileStoreAdapter,
    LocalSourceContentAdapter,
)
from app.modules.docling.artifacts import export_artifacts_and_persist_document
from app.modules.docling.chunking import chunk_document
from app.modules.docling.converter import run_conversion
from app.modules.docling.service import DOCLING_EXTRACTOR_VERSION
from app.modules.docling.settings import DoclingSettings
from app.orchestrator.contracts import EmbeddingClientPort, VectorStorePort
from app.orchestrator.errors import OrchestratorError
from app.orchestrator.models import ChunkExtractionV1
from app.orchestrator.settings import MVPOrchestratorSettings
from app.vectorstore.collections import compute_collection_name
from app.vectorstore.client import build_qdrant_client
from app.vectorstore.models import ChunkPayload, ChunkPoint
from app.vectorstore.repo import QdrantVectorStoreRepo
from app.vectorstore.settings import VectorStoreSettings

logger = logging.getLogger(__name__)


def _compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _docling_phase(
    workspace_id: str,
    source_version_id: str,
    file_path: Path,
) -> tuple[str | None, str | None]:
    """Run docling conversion + export + chunk. Returns (document_id, extract_run_id) or (None, run_id)."""
    from app.db.repositories.extract_run_repo import ExtractRunRepo

    init_db()
    with session_scope() as session:
        extract_runs = ExtractRunsAdapter(session)
        run = extract_runs.get_or_create_run(
            workspace_id=workspace_id,
            source_version_id=source_version_id,
            extractor="docling",
            extractor_version=DOCLING_EXTRACTOR_VERSION,
            status="RUNNING",
        )
        run_id = run.id if hasattr(run, "id") else run.get("id")
        from datetime import datetime, timezone
        extract_runs.update_run_status(run_id, "RUNNING", started_at=datetime.now(timezone.utc))

    with session_scope() as session:
        source_content = LocalSourceContentAdapter(session)
        extract_runs = ExtractRunsAdapter(session)
        document_repo = DocumentRepoAdapter(session)
        chunk_repo = ChunkRepoAdapter(session)
        file_store = LocalFileStoreAdapter(str(Path.cwd() / "data" / "docling_artifacts"))
        settings = DoclingSettings()

        job = {
            "workspace_id": workspace_id,
            "source_version_id": source_version_id,
            "extractor": "docling",
            "extractor_version": DOCLING_EXTRACTOR_VERSION,
            "embedding_set_id": "",
            "source_path": str(file_path),
        }

        docling_doc = run_conversion(job, source_content, extract_runs, run_id, settings)
        if not docling_doc:
            return None, run_id

        document_id = export_artifacts_and_persist_document(
            docling_doc,
            source_version_id,
            "docling",
            DOCLING_EXTRACTOR_VERSION,
            file_store,
            document_repo,
            extract_runs,
            run_id,
            settings,
        )
        if not document_id:
            return None, run_id

        chunker_version, count = chunk_document(
            docling_doc,
            document_id,
            chunk_repo,
            file_store,
            extract_runs,
            run_id,
            None,
            settings,
            embedding_set_id="",
        )
        if not chunker_version:
            return None, run_id

    return document_id, run_id


class MVPOrchestrator:
    """Orchestrates file ingestion: Docling -> LLM extract -> Embed -> Qdrant."""

    def __init__(
        self,
        orch_settings: MVPOrchestratorSettings | None = None,
        llm_settings: LLMSettings | None = None,
        embed_settings: EmbedSettings | None = None,
        embed_client: EmbeddingClientPort | None = None,
        vector_store: VectorStorePort | None = None,
    ) -> None:
        self._orch = orch_settings or MVPOrchestratorSettings()
        self._llm_settings = llm_settings or LLMSettings()
        self._embed_settings = embed_settings or EmbedSettings()
        self._llm = LLMService(settings=self._llm_settings)
        self._embed = embed_client or OllamaEmbedClient(self._embed_settings)
        self._vector = vector_store or self._default_vector_store()

    def _default_vector_store(self) -> QdrantVectorStoreRepo:
        client = build_qdrant_client(VectorStoreSettings())
        return QdrantVectorStoreRepo(client, VectorStoreSettings())

    async def run_file_ingestion(
        self,
        workspace_id: str,
        file_path: Path,
        *,
        force_reprocess: bool | None = None,
    ) -> str:
        """Run full pipeline: file -> parse -> chunk -> LLM extract -> embed -> persist. Returns run_id."""
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise OrchestratorError(f"File not found: {file_path}", code="FILE_NOT_FOUND")

        force = force_reprocess if force_reprocess is not None else self._orch.force_reprocess
        init_db()

        content_sha256 = _compute_sha256(file_path)
        storage_uri = str(file_path)

        workspace_id, source_version_id, document_id = await asyncio.to_thread(
            self._ensure_source_and_version,
            workspace_id,
            file_path.name,
            content_sha256,
            storage_uri,
        )

        doc_id, _ = await asyncio.to_thread(
            _docling_phase,
            workspace_id,
            source_version_id,
            file_path,
        )
        if not doc_id:
            raise OrchestratorError("Docling conversion failed", code="DOCLING_FAILED")

        document_id = doc_id
        run_id, chunk_ids, workspace_id_out = await asyncio.to_thread(
            self._create_pipeline_run,
            workspace_id,
            document_id,
            force,
        )
        if not chunk_ids:
            await asyncio.to_thread(self._finalize_run, run_id, "DONE")
            return run_id

        sem = asyncio.Semaphore(self._orch.max_concurrency)
        embed_spec = await asyncio.to_thread(
            self._ensure_embedding_set,
            workspace_id_out,
        )

        async def process(chunk_id: str) -> None:
            async with sem:
                await self._process_one_chunk(
                    run_id=run_id,
                    chunk_id=chunk_id,
                    workspace_id=workspace_id_out,
                    document_id=document_id,
                    embedding_set=embed_spec,
                )

        await asyncio.gather(*(process(cid) for cid in chunk_ids))

        await asyncio.to_thread(self._finalize_run_from_chunk_runs, run_id)
        return run_id

    def _ensure_source_and_version(
        self,
        workspace_id: str,
        source_name: str,
        content_sha256: str,
        storage_uri: str,
    ) -> tuple[str, str, str | None]:
        with session_scope() as session:
            ws_repo = WorkspaceRepo()
            src_repo = SourceRepo()
            ver_repo = SourceVersionRepo()

            ws = ws_repo.get_by_name(session, workspace_id)
            if not ws:
                ws = ws_repo.create(session, workspace_id)
            workspace_id = ws.id if hasattr(ws, "id") else ws.get("id")

            src = src_repo.create(
                session,
                workspace_id=workspace_id,
                source_type="file",
                title=source_name,
            )
            source_id = src.id if hasattr(src, "id") else src.get("id")

            from datetime import datetime, timezone
            ver = ver_repo.create_or_get(
                session,
                source_id=source_id,
                content_sha256=content_sha256,
                storage_uri=storage_uri,
                ingested_at=datetime.now(timezone.utc),
            )
            source_version_id = ver.id if hasattr(ver, "id") else ver.get("id")

        return workspace_id, source_version_id, None

    def _create_pipeline_run(
        self,
        workspace_id: str,
        document_id: str,
        force: bool,
    ) -> tuple[str, list[str], str]:
        with session_scope() as session:
            chunk_repo = ChunkRepo()
            pipeline_repo = PipelineRunRepo()
            chunk_run_repo = ChunkRunRepo()

            chunks = chunk_repo.list_by_document(session, document_id)
            chunk_ids = [c[0] for c in chunks]

            if not force:
                from app.db.models.pipeline_run import PipelineRun
                existing = session.execute(
                    select(PipelineRun).where(
                        PipelineRun.document_id == document_id,
                        PipelineRun.status.in_(["DONE", "DONE_WITH_ERRORS"]),
                    ).order_by(PipelineRun.started_at.desc()).limit(1)
                ).scalar_one_or_none()
                if existing:
                    return existing.id, [], workspace_id

            run = pipeline_repo.create(
                session,
                workspace_id=workspace_id,
                document_id=document_id,
                prompt_name=self._orch.prompt_name,
            )
            run_id = run.id

            chunk_run_repo.bulk_ensure(session, run_id, chunk_ids)
            pending = chunk_run_repo.list_pending(session, run_id)
            to_process = [p.chunk_id for p in pending]

        return run_id, to_process, workspace_id

    def _ensure_embedding_set(self, workspace_id: str) -> "EmbeddingSetSpec":
        from uuid import NAMESPACE_DNS, uuid5
        from app.vectorstore.collections import EmbeddingSetSpecValue
        from app.vectorstore.settings import VectorStoreSettings
        vs_settings = VectorStoreSettings()
        deterministic_id = str(uuid5(NAMESPACE_DNS, f"{workspace_id}:{self._orch.default_embedding_set_name}"))
        coll_name = compute_collection_name(
            workspace_id,
            deterministic_id,
            vs_settings.schema_version,
        )
        with session_scope() as session:
            existing = session.execute(
                select(EmbeddingSet).where(
                    EmbeddingSet.workspace_id == workspace_id,
                    EmbeddingSet.name == self._orch.default_embedding_set_name,
                )
            ).scalar_one_or_none()
            if existing:
                return EmbeddingSetSpecValue(
                    id=existing.id,
                    workspace_id=existing.workspace_id,
                    qdrant_collection=existing.qdrant_collection,
                    dims=existing.dims,
                    distance=existing.distance,
                )
            es = EmbeddingSet(
                id=deterministic_id,
                workspace_id=workspace_id,
                name=self._orch.default_embedding_set_name,
                model=self._embed_settings.ollama_model,
                dims=self._embed_settings.dims,
                distance="Cosine",
                qdrant_collection=coll_name,
            )
            session.add(es)
            session.flush()
            return EmbeddingSetSpecValue(
                id=es.id,
                workspace_id=es.workspace_id,
                qdrant_collection=es.qdrant_collection,
                dims=es.dims,
                distance=es.distance,
            )

    async def _process_one_chunk(
        self,
        run_id: str,
        chunk_id: str,
        workspace_id: str,
        document_id: str,
        embedding_set: "EmbeddingSetSpec",
    ) -> None:
        chunk_text, chunk_index, chunk_hash = await asyncio.to_thread(
            self._load_chunk,
            chunk_id,
        )
        if not chunk_text:
            await asyncio.to_thread(
                self._mark_chunk_error,
                run_id,
                chunk_id,
                error_message="Chunk has no text",
            )
            return

        t0 = asyncio.get_event_loop().time()
        try:
            req = LLMRequest(
                messages=[
                    LLMMessage(
                        role="system",
                        content="Extract structured information from the document chunk. Respond with valid JSON only.",
                    ),
                    LLMMessage(role="user", content=chunk_text[:8000]),
                ],
                profile=LLMProfile.AUTO,
                response_format={"type": "json_object"},
                metadata={"workspace_id": workspace_id, "pipeline_run_id": run_id},
            )
            resp = await self._llm.chat(req, workspace_id=workspace_id)
            latency_ms = int((asyncio.get_event_loop().time() - t0) * 1000)

            parsed = None
            validation_err = None
            try:
                parsed = ChunkExtractionV1.model_validate_json(resp.text)
            except Exception as e:
                validation_err = str(e)[:4096]

            parsed_json = parsed.model_dump_json() if parsed else None
            usage_json = resp.usage.model_dump_json() if resp.usage else None

            await asyncio.to_thread(
                self._persist_extraction,
                chunk_id,
                run_id,
                raw_text=resp.text,
                parsed_json=parsed_json,
                usage_json=usage_json,
                validation_error=validation_err,
                model=resp.model,
            )

            vectors = await self._embed.embed_texts([chunk_text])
            if not vectors:
                raise OrchestratorError("Embed returned empty", code="EMBED_FAILED")

            now = datetime.now(timezone.utc)
            point = ChunkPoint(
                id=UUID(chunk_id),
                vector=vectors[0],
                payload=ChunkPayload(
                    workspace_id=workspace_id,
                    document_id=document_id,
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    embedded_at=now,
                    chunk_hash=chunk_hash,
                ),
            )
            await self._vector.ensure_collection(embedding_set)
            await self._vector.upsert_points(embedding_set, [point])

            await asyncio.to_thread(
                self._mark_chunk_done,
                run_id,
                chunk_id,
                latency_ms=latency_ms,
            )

            with session_scope() as session:
                from app.db.repositories.embedding_repo import ChunkEmbeddingRepo
                ce_repo = ChunkEmbeddingRepo()
                ce_repo.upsert_pointers(session, embedding_set.id, [(chunk_id, chunk_id)])

        except Exception as e:
            logger.exception("process_one_chunk failed: chunk_id=%s", chunk_id)
            await asyncio.to_thread(
                self._mark_chunk_error,
                run_id,
                chunk_id,
                error_type=type(e).__name__,
                error_message=str(e)[:4096],
            )
            if self._orch.stop_on_first_error:
                raise

    def _load_chunk(self, chunk_id: str) -> tuple[str, int, str]:
        with session_scope() as session:
            row = session.get(Chunk, chunk_id)
            if not row:
                return "", 0, ""
            return (row.text or "")[:65536], row.chunk_index, row.chunk_hash or ""

    def _persist_extraction(
        self,
        chunk_id: str,
        run_id: str,
        *,
        raw_text: str | None = None,
        parsed_json: str | None = None,
        usage_json: str | None = None,
        validation_error: str | None = None,
        model: str | None = None,
    ) -> None:
        with session_scope() as session:
            repo = ChunkExtractionRepo()
            repo.upsert(
                session,
                chunk_id=chunk_id,
                run_id=run_id,
                prompt_name=self._orch.prompt_name,
                raw_text=raw_text,
                parsed_json=parsed_json,
                usage_json=usage_json,
                validation_error=validation_error,
                model=model,
            )

    def _mark_chunk_done(self, run_id: str, chunk_id: str, *, latency_ms: int | None = None) -> None:
        with session_scope() as session:
            ChunkRunRepo().mark_done(session, run_id, chunk_id, latency_ms=latency_ms)

    def _mark_chunk_error(
        self,
        run_id: str,
        chunk_id: str,
        *,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with session_scope() as session:
            ChunkRunRepo().mark_error(
                session,
                run_id,
                chunk_id,
                error_type=error_type,
                error_message=error_message,
            )

    def _finalize_run(self, run_id: str, status: str, error_summary: str | None = None) -> None:
        with session_scope() as session:
            PipelineRunRepo().finalize(session, run_id, status, error_summary=error_summary)

    def _finalize_run_from_chunk_runs(self, run_id: str) -> None:
        with session_scope() as session:
            from app.db.models.pipeline_run import ChunkRun
            rows = session.execute(
                select(ChunkRun).where(ChunkRun.run_id == run_id)
            ).scalars().all()
            done = sum(1 for r in rows if r.status == "DONE")
            errors = sum(1 for r in rows if r.status == "ERROR")
            total = len(rows)
            if errors > 0 and not self._orch.stop_on_first_error:
                status = "DONE_WITH_ERRORS"
                err_sum = f"{errors}/{total} chunks failed"
            elif errors == total:
                status = "FAILED"
                err_sum = "All chunks failed"
            else:
                status = "DONE"
                err_sum = None
            PipelineRunRepo().finalize(session, run_id, status, error_summary=err_sum)
