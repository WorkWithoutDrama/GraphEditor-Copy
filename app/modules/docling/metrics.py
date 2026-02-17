"""Observability: histograms and counter per plan H3 (docling_parse_seconds, etc.)."""
from collections import defaultdict
from typing import Any

# In-memory store: name -> list of observed values (for histograms) or count (for counter)
_histograms: dict[str, list[float]] = defaultdict(list)
_counters: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))


def record_parse_seconds(value: float) -> None:
    _histograms["docling_parse_seconds"].append(value)


def record_export_seconds(value: float) -> None:
    _histograms["docling_export_seconds"].append(value)


def record_chunk_seconds(value: float) -> None:
    _histograms["docling_chunk_seconds"].append(value)


def record_chunks_per_document(value: float) -> None:
    _histograms["chunks_per_document"].append(value)


def record_ingest_failure(error_code: str) -> None:
    _counters["ingest_failures_total"][error_code] += 1


def get_histogram(name: str) -> list[float]:
    return list(_histograms.get(name, []))


def get_failure_counts() -> dict[str, int]:
    return dict(_counters.get("ingest_failures_total", {}))


def reset_metrics() -> None:
    _histograms.clear()
    _counters.clear()
