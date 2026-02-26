"""Export DoclingDocument to file store and persist Document (structure_json_uri, plain_text_uri, stats)."""
import json
import logging
import time
from typing import Any

from app.modules.docling import metrics as docling_metrics

logger = logging.getLogger(__name__)


def export_artifacts_and_persist_document(
    docling_doc: Any,
    source_version_id: str,
    extractor: str,
    extractor_version: str,
    file_store: Any,
    document_repo: Any,
    extract_runs_port: Any,
    run_id: str,
    settings: Any,
) -> str | None:
    """Export JSON (required), plain text, optional markdown; write to file_store; get_or_create Document with URIs; update run to ARTIFACTS_STORED. Returns document_id or None."""
    store_json = getattr(settings, "store_docling_json", True)
    store_md = getattr(settings, "store_docling_md", False)
    if not store_json:
        docling_metrics.record_ingest_failure("EXPORT_FAILED")
        extract_runs_port.update_run_status(run_id, "FAILED", error_code="EXPORT_FAILED", error_message="store_docling_json is False")
        return None

    t0 = time.perf_counter()
    try:
        doc_dict = docling_doc.export_to_dict()
        json_bytes = json.dumps(doc_dict, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except Exception as e:
        docling_metrics.record_ingest_failure("EXPORT_FAILED")
        extract_runs_port.update_run_status(
            run_id, "FAILED",
            error_code="EXPORT_FAILED",
            error_message=str(e)[:4096],
        )
        return None
    finally:
        docling_metrics.record_export_seconds(time.perf_counter() - t0)

    key_json = f"docling/{source_version_id}/{extractor_version}/structure.json"
    structure_uri = file_store.put_bytes(key_json, json_bytes)

    plain_uri = None
    try:
        text = docling_doc.export_to_text()
        if text:
            plain_uri = file_store.put_bytes(
                f"docling/{source_version_id}/{extractor_version}/plain.txt",
                text.encode("utf-8"),
            )
    except Exception:
        pass

    md_uri = None
    if store_md:
        try:
            md = docling_doc.export_to_markdown()
            if md:
                md_uri = file_store.put_bytes(
                    f"docling/{source_version_id}/{extractor_version}/doc.md",
                    md.encode("utf-8"),
                )
        except Exception:
            pass

    page_count = 0
    if hasattr(docling_doc, "num_pages"):
        try:
            page_count = docling_doc.num_pages() if callable(docling_doc.num_pages) else docling_doc.num_pages
        except Exception:
            pass
    stats = {
        "parser": {"name": "docling", "version": extractor_version},
        "conversion": {"page_count": page_count},
    }
    if md_uri:
        stats.setdefault("artifacts", {})["markdown_uri"] = md_uri

    doc = document_repo.get_or_create_document(
        source_version_id=source_version_id,
        extractor=extractor,
        extractor_version=extractor_version,
        structure_json_uri=structure_uri,
        plain_text_uri=plain_uri,
        stats=stats,
    )
    document_id = getattr(doc, "id", None) or (doc.get("id") if isinstance(doc, dict) else None)
    extract_runs_port.update_run_status(run_id, "ARTIFACTS_STORED")
    return document_id
