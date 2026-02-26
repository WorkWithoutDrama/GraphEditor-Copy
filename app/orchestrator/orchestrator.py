"""MVP Orchestrator: run_file_ingestion using Stage 1 extraction."""
from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from uuid import uuid4

from app.db.repositories.source_repo import SourceRepo, SourceVersionRepo
from app.db.repositories.workspace_repo import WorkspaceRepo
from app.db.session import init_db, session_scope
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
from app.orchestrator.errors import OrchestratorError
from app.orchestrator.settings import MVPOrchestratorSettings
from app.stage1 import run_stage1_extract
from app.stage1.config import Stage1Config

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
    """Orchestrates file ingestion: Docling -> Stage 1 extract (claims) -> persist."""

    def __init__(
        self,
        orch_settings: MVPOrchestratorSettings | None = None,
    ) -> None:
        self._orch = orch_settings or MVPOrchestratorSettings()

    async def run_file_ingestion(
        self,
        workspace_id: str,
        file_path: Path,
        *,
        force_reprocess: bool | None = None,
    ) -> str:
        """Run full pipeline: file -> parse -> chunk -> Stage 1 extract (claims). Returns run_id."""
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise OrchestratorError(f"File not found: {file_path}", code="FILE_NOT_FOUND")

        force = force_reprocess if force_reprocess is not None else self._orch.force_reprocess
        init_db()

        content_sha256 = _compute_sha256(file_path)
        storage_uri = str(file_path)

        workspace_id, source_version_id, _ = await asyncio.to_thread(
            self._ensure_source_and_version,
            workspace_id,
            file_path.name,
            content_sha256,
            storage_uri,
        )

        document_id, _ = await asyncio.to_thread(
            _docling_phase,
            workspace_id,
            source_version_id,
            file_path,
        )
        if not document_id:
            raise OrchestratorError("Docling conversion failed", code="DOCLING_FAILED")

        config = Stage1Config(
            model_id=self._orch.stage1_model_id,
            force_nonce=str(uuid4()) if force else None,
        )
        result = await asyncio.to_thread(
            run_stage1_extract,
            document_id,
            config,
            pending_only=False,
        )
        if result.status == "FAILED" and result.error_summary:
            raise OrchestratorError(
                result.error_summary,
                code="STAGE1_FAILED",
            )
        return result.run_id

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
