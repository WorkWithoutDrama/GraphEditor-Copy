"""Docling module: file ingest → parse → artifacts → chunking → persistence → handoff to embeddings."""
from app.modules.docling.settings import DoclingSettings
from app.modules.docling.service import DoclingService

__all__ = ["DoclingSettings", "DoclingService"]
