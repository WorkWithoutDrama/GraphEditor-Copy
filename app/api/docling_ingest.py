"""Docling ingest API: POST /documents/ingest. Uses sync session."""
from flask import Blueprint, request, jsonify

from app.db.session import session_scope
from app.db.repositories.source_repo import SourceVersionRepo
from app.modules.docling.factory import create_docling_service
from app.modules.docling.settings import DoclingSettings

bp = Blueprint("docling_ingest", __name__, url_prefix="/api")


@bp.route("/documents/ingest", methods=["POST"])
def ingest():
    """POST /api/documents/ingest. Body: workspace_id, source_version_id, embedding_set_id."""
    data = request.get_json(force=True, silent=True) or {}
    workspace_id = data.get("workspace_id")
    source_version_id = data.get("source_version_id")
    embedding_set_id = data.get("embedding_set_id")
    if not workspace_id or not source_version_id or not embedding_set_id:
        return jsonify({"error": "workspace_id, source_version_id, embedding_set_id required"}), 400

    with session_scope() as session:
        version_repo = SourceVersionRepo()
        if version_repo.get(session, source_version_id) is None:
            return jsonify({"error": "SourceVersion not found"}), 404

        settings = DoclingSettings()
        service = create_docling_service(session, settings=settings)
        response = service.enqueue_extract(
            workspace_id=workspace_id,
            source_version_id=source_version_id,
            embedding_set_id=embedding_set_id,
        )
    return jsonify(response.model_dump()), 202


