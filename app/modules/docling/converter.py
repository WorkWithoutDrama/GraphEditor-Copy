"""Docling conversion: raw input -> DoclingDocument. Only module that imports docling for conversion."""
import io
import logging
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import Any

from app.modules.docling import errors as docling_errors
from app.modules.docling import metrics as docling_metrics

logger = logging.getLogger(__name__)

# Lazy converter singleton per process
_converter_instance: Any = None


def _get_converter(settings: Any):
    global _converter_instance
    if _converter_instance is not None:
        return _converter_instance
    from docling.document_converter import DocumentConverter
    _converter_instance = DocumentConverter()
    return _converter_instance


def run_conversion(
    job: dict[str, Any],
    source_content_port: Any,
    extract_runs_port: Any,
    run_id: str,
    settings: Any,
):
    """Load raw stream, run DocumentConverter, update run to PARSED or FAILED. Returns DoclingDocument or None."""
    from datetime import datetime, timezone

    source_version_id = job["source_version_id"]
    max_file_size = getattr(settings, "max_file_size_bytes", 20_000_000)
    max_num_pages = getattr(settings, "max_num_pages", 200)

    try:
        stream = source_content_port.open_raw_stream(source_version_id)
    except FileNotFoundError as e:
        extract_runs_port.update_run_status(
            run_id, "FAILED",
            error_code=docling_errors.DoclingErrorCode.STORAGE_READ_FAILED,
            error_message=str(e)[:4096],
            finished_at=datetime.now(tz=timezone.utc),
        )
        return None
    except Exception as e:
        extract_runs_port.update_run_status(
            run_id, "FAILED",
            error_code=docling_errors.DoclingErrorCode.STORAGE_READ_FAILED,
            error_message=str(e)[:4096],
            finished_at=datetime.now(tz=timezone.utc),
        )
        return None

    try:
        raw_bytes = stream.read()
        stream.close()
    except Exception as e:
        extract_runs_port.update_run_status(
            run_id, "FAILED",
            error_code=docling_errors.DoclingErrorCode.STORAGE_READ_FAILED,
            error_message=str(e)[:4096],
            finished_at=datetime.now(tz=timezone.utc),
        )
        return None

    if len(raw_bytes) > max_file_size:
        extract_runs_port.update_run_status(
            run_id, "FAILED",
            error_code=docling_errors.DoclingErrorCode.FILE_TOO_LARGE,
            error_message=f"File size {len(raw_bytes)} exceeds max {max_file_size}",
            finished_at=datetime.now(tz=timezone.utc),
        )
        return None

    parse_timeout = getattr(settings, "parse_timeout_seconds", 300.0)
    converter = _get_converter(settings)
    source: Path | Any

    def _do_convert() -> Any:
        if len(raw_bytes) > 2 * 1024 * 1024:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".bin")
            tmp.write(raw_bytes)
            tmp.close()
            source = Path(tmp.name)
            try:
                return converter.convert(
                    source,
                    max_file_size=max_file_size,
                    max_num_pages=max_num_pages,
                )
            finally:
                Path(tmp.name).unlink(missing_ok=True)
        try:
            from docling.datamodel.document_stream import DocumentStream
            source = DocumentStream(io.BytesIO(raw_bytes))
        except ImportError:
            source = io.BytesIO(raw_bytes)
        return converter.convert(
            source,
            max_file_size=max_file_size,
            max_num_pages=max_num_pages,
        )

    t0 = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_do_convert)
            result = fut.result(timeout=parse_timeout)
    except FuturesTimeoutError:
        docling_metrics.record_ingest_failure(str(docling_errors.DoclingErrorCode.TIMEOUT_PARSE))
        extract_runs_port.update_run_status(
            run_id, "FAILED",
            error_code=docling_errors.DoclingErrorCode.TIMEOUT_PARSE,
            error_message=f"Parse exceeded {parse_timeout}s",
            finished_at=datetime.now(tz=timezone.utc),
        )
        return None
    except Exception as e:
        code = docling_errors.DoclingErrorCode.PARSE_FAILED
        if "page" in str(e).lower():
            code = docling_errors.DoclingErrorCode.TOO_MANY_PAGES
        docling_metrics.record_ingest_failure(str(code))
        extract_runs_port.update_run_status(
            run_id, "FAILED",
            error_code=code,
            error_message=str(e)[:4096],
            finished_at=datetime.now(tz=timezone.utc),
        )
        return None
    finally:
        docling_metrics.record_parse_seconds(time.perf_counter() - t0)

    if not result or not getattr(result, "document", None):
        docling_metrics.record_ingest_failure(str(docling_errors.DoclingErrorCode.PARSE_FAILED))
        extract_runs_port.update_run_status(
            run_id, "FAILED",
            error_code=docling_errors.DoclingErrorCode.PARSE_FAILED,
            error_message="Conversion produced no document",
            finished_at=datetime.now(tz=timezone.utc),
        )
        return None

    extract_runs_port.update_run_status(run_id, "PARSED")
    return result.document
