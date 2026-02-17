"""Chunk DoclingDocument with HybridChunker; enforce max tokens; persist via ChunkRepoPort."""
import json
import logging
import time
from typing import Any

from app.modules.docling.ids import chunk_hash, chunker_version_hash
from app.modules.docling.schemas import ChunkCreate
from app.modules.docling import metrics as docling_metrics

logger = logging.getLogger(__name__)


def _chunk_settings_dict(settings: Any) -> dict:
    return {
        "chunker": getattr(settings, "chunker", "hybrid"),
        "target_tokens": getattr(settings, "target_tokens", 800),
        "max_tokens": getattr(settings, "max_tokens", 1000),
        "overlap_tokens": getattr(settings, "overlap_tokens", 80),
    }


def _tokenizer(settings: Any, tokenizer_resolver: Any, embedding_set_id: str):
    if tokenizer_resolver and embedding_set_id:
        try:
            return tokenizer_resolver(embedding_set_id)
        except Exception:
            pass
    return None


def _count_tokens(text: str, tokenizer: Any) -> int:
    if tokenizer and hasattr(tokenizer, "count_tokens"):
        return tokenizer.count_tokens(text)
    return len(text.split()) * 2


def chunk_document(
    docling_doc: Any,
    document_id: str,
    chunk_repo: Any,
    file_store: Any,
    extract_runs_port: Any,
    run_id: str,
    tokenizer_resolver: Any,
    settings: Any,
    embedding_set_id: str = "",
) -> tuple[str | None, int]:
    """Chunk docling_doc, enforce max_tokens, bulk_upsert_chunks, update run to CHUNKED. Returns (chunker_version, chunk_count)."""
    from app.modules.docling import errors as docling_errors

    max_tokens = getattr(settings, "max_tokens", 1000)
    enforce_hard = getattr(settings, "enforce_max_tokens_hard", True)
    max_chunks = getattr(settings, "max_chunks_per_document", 10_000)
    batch_rows = getattr(settings, "chunk_batch_rows", 200)
    batch_max_bytes = getattr(settings, "chunk_batch_max_bytes", 5 * 1024 * 1024)

    chunk_settings = _chunk_settings_dict(settings)
    chunker_version = chunker_version_hash(chunk_settings)
    tokenizer = _tokenizer(settings, tokenizer_resolver, embedding_set_id)

    t0 = time.perf_counter()
    try:
        chunker, chunk_iter = _run_chunker(docling_doc, settings, tokenizer)
        chunks_with_text = list(_contextualize_and_enforce_max_tokens(
            chunker, chunk_iter, settings, tokenizer, max_tokens, enforce_hard, chunker_version
        ))
    except Exception as e:
        docling_metrics.record_ingest_failure(str(docling_errors.DoclingErrorCode.CHUNK_FAILED))
        extract_runs_port.update_run_status(
            run_id, "FAILED",
            error_code=docling_errors.DoclingErrorCode.CHUNK_FAILED,
            error_message=str(e)[:4096],
        )
        return None, 0
    finally:
        docling_metrics.record_chunk_seconds(time.perf_counter() - t0)

    if len(chunks_with_text) > max_chunks:
        docling_metrics.record_ingest_failure(str(docling_errors.DoclingErrorCode.TOO_MANY_CHUNKS))
        extract_runs_port.update_run_status(
            run_id, "FAILED",
            error_code=docling_errors.DoclingErrorCode.TOO_MANY_CHUNKS,
            error_message=f"Chunk count {len(chunks_with_text)} exceeds max {max_chunks}",
        )
        return None, 0

    docling_metrics.record_chunks_per_document(float(len(chunks_with_text)))

    chunk_creates = []
    for idx, (text, page_start, page_end, meta) in enumerate(chunks_with_text):
        h = chunk_hash(chunker_version, idx, text)
        meta_json_str = json.dumps(meta, ensure_ascii=False, separators=(",", ":")) if meta else None
        chunk_creates.append(ChunkCreate(
            chunk_index=idx,
            chunk_hash=h,
            text=text[:65535] if len(text) > 65535 else text,
            text_uri=None,
            page_start=page_start,
            page_end=page_end,
            meta_json=meta_json_str,
        ))

    chunk_repo.bulk_upsert_chunks(
        document_id,
        chunk_creates,
        batch_rows=batch_rows,
        batch_max_bytes=batch_max_bytes,
    )
    extract_runs_port.update_run_status(run_id, "CHUNKED", chunker_version=chunker_version)
    return chunker_version, len(chunk_creates)


def _run_chunker(docling_doc: Any, settings: Any, tokenizer: Any):
    """Return (chunker, chunk_iterator) or (None, fallback_iterator)."""
    chunker_name = getattr(settings, "chunker", "hybrid")
    try:
        from docling.chunking import HybridChunker
        from docling.chunking import HierarchicalChunker
    except ImportError:
        try:
            from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
            from docling_core.transforms.chunker.hierarchical_chunker import HierarchicalChunker
        except ImportError:
            HybridChunker = None
            HierarchicalChunker = None

    if HybridChunker is None:
        return None, _fallback_chunk_by_text(docling_doc, settings)

    target = getattr(settings, "target_tokens", 800)
    max_tok = getattr(settings, "max_tokens", 1000)
    overlap = getattr(settings, "overlap_tokens", 80)
    if chunker_name == "hybrid" and HybridChunker:
        chunker = HybridChunker(
            tokenizer=tokenizer,
            target_tokens=target,
            max_tokens=max_tok,
            overlap_tokens=overlap,
        )
    elif HierarchicalChunker:
        chunker = HierarchicalChunker(
            tokenizer=tokenizer,
            target_tokens=target,
            max_tokens=max_tok,
            overlap_tokens=overlap,
        )
    else:
        return None, _fallback_chunk_by_text(docling_doc, settings)

    chunk_iter = chunker.chunk(dl_doc=docling_doc)
    return chunker, chunk_iter


def _contextualize_and_enforce_max_tokens(chunker: Any, chunk_iter, settings: Any, tokenizer: Any, max_tokens: int, enforce_hard: bool, chunker_version: str):
    """Contextualize each chunk; if over max_tokens, split; yield (text, page_start, page_end, meta)."""
    for ch in chunk_iter:
        if chunker and hasattr(chunker, "contextualize"):
            text = chunker.contextualize(chunk=ch)
        else:
            text = getattr(ch, "text", None) or getattr(ch, "content", None) or str(ch)
        page_start = getattr(ch, "page_start", None) or getattr(ch, "page_no", None)
        page_end = getattr(ch, "page_end", None) or page_start
        meta = {"chunker_version": chunker_version, "source_artifact": "structure_json_uri"}
        n = _count_tokens(text, tokenizer)
        meta["token_count"] = n
        if enforce_hard and n > max_tokens:
            for sub_text in _split_text_by_tokens(text, max_tokens, tokenizer):
                yield (sub_text, page_start, page_end, {**meta, "token_count": _count_tokens(sub_text, tokenizer)})
        else:
            yield (text, page_start, page_end, meta)


def _split_text_by_tokens(text: str, max_tokens: int, tokenizer: Any) -> list[str]:
    """Split by paragraphs then by token windows; each chunk stays <= max_tokens (by token count)."""
    parts = text.split("\n\n")
    out = []
    buf = []
    buf_tokens = 0
    for p in parts:
        n = _count_tokens(p, tokenizer)
        if buf_tokens + n > max_tokens and buf:
            out.append("\n\n".join(buf))
            buf = []
            buf_tokens = 0
        if n > max_tokens:
            # Split paragraph by token count: add words until we would exceed max_tokens
            words = p.split()
            i = 0
            while i < len(words):
                chunk_words = []
                chunk_tokens = 0
                while i < len(words):
                    w = words[i]
                    add = _count_tokens(w, tokenizer)
                    if chunk_tokens + add > max_tokens and chunk_words:
                        break
                    chunk_words.append(w)
                    chunk_tokens += add
                    i += 1
                if chunk_words:
                    out.append(" ".join(chunk_words))
        else:
            buf.append(p)
            buf_tokens += n
    if buf:
        out.append("\n\n".join(buf))
    return out


def _fallback_chunk_by_text(docling_doc: Any, settings: Any):
    """No chunker available: export full text as one chunk."""
    text = docling_doc.export_to_text() if hasattr(docling_doc, "export_to_text") else ""
    if not text:
        return
    yield type("Chunk", (), {"text": text, "page_start": None, "page_end": None, "page_no": None})()
