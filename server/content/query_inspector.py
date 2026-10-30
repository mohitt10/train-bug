from flask import Blueprint, jsonify, request

from query_monitor import get_query_history
from .reports import moderator_required
from .responses import error_response

inspector_bp = Blueprint("query_inspector", __name__, url_prefix="/query-inspector")
ALLOWED_OPERATIONS = {"SELECT", "INSERT", "UPDATE", "DELETE", "MERGE", "WITH", "UNKNOWN"}
PUBLIC_QUERY_FIELDS = (
    "query_id",
    "request_id",
    "timestamp",
    "endpoint",
    "action",
    "operation",
    "statement",
    "status",
    "duration_ms",
    "affected_rows",
    "error_summary",
)


def _public_entry(entry):
    return {field: entry.get(field) for field in PUBLIC_QUERY_FIELDS}


@inspector_bp.get("/queries")
@moderator_required
def list_queries():
    try:
        limit = int(request.args.get("limit", 50))
    except (TypeError, ValueError):
        return error_response("VALIDATION_ERROR", "limit must be an integer.", 400)
    if not 1 <= limit <= 100:
        return error_response("VALIDATION_ERROR", "limit must be between 1 and 100.", 400)

    operation = request.args.get("operation")
    if operation:
        operation = operation.upper()
        if operation not in ALLOWED_OPERATIONS:
            return error_response("VALIDATION_ERROR", "Unsupported SQL operation filter.", 400)

    request_id = request.args.get("request_id")
    endpoint = request.args.get("endpoint")
    if (request_id and len(request_id) > 80) or (endpoint and len(endpoint) > 300):
        return error_response("VALIDATION_ERROR", "Inspector filter is too long.", 400)

    entries = reversed(get_query_history())
    filtered = [
        entry
        for entry in entries
        if (not operation or entry.get("operation") == operation)
        and (not request_id or entry.get("request_id") == request_id)
        and (not endpoint or endpoint.lower() in (entry.get("endpoint") or "").lower())
    ]
    return jsonify({"items": [_public_entry(entry) for entry in filtered[:limit]]}), 200


@inspector_bp.get("/queries/<query_id>")
@moderator_required
def get_query(query_id: str):
    for entry in reversed(get_query_history()):
        if entry.get("query_id") == query_id:
            return jsonify(_public_entry(entry)), 200
    return error_response("NOT_FOUND", "Query record not found.", 404)
