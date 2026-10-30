"""Shared API helpers, introduced in Phase 2 and reusable by Phases 3 and 4.

Implements the response format from docs/api-conventions.md:
    success -> {"status": "success", "data": ...}
    error   -> {"status": "error", "error": {"code": ..., "message": ...}}
"""
from collections.abc import Mapping

from flask import jsonify, request


def success(data=None, status=200):
    return jsonify({"status": "success", "data": data}), status


def error_response(code, message, status, details=None):
    err = {"code": code, "message": message}
    if details:
        err["details"] = details
    return jsonify({"status": "error", "error": err}), status


def json_body():
    """Return the JSON request body as a dict, or None if it is missing/invalid."""
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else None


def as_dict(row, columns):
    """Turn a DB row into a JSON-safe dict.

    Accepts the shared execute_query result envelope, dict-like rows, or plain
    tuples; for tuples, `columns` must match the SELECT order.
    Datetimes become ISO-8601 strings.
    """
    if row is None:
        return None
    if isinstance(row, Mapping) and "rows" in row:
        columns = row.get("columns") or columns
        row = row.get("rows")
        if row is None:
            return None
    data = dict(row) if isinstance(row, Mapping) else dict(zip(columns, row))
    return {
        key: (value.isoformat() if hasattr(value, "isoformat") else value)
        for key, value in data.items()
    }


def as_dicts(rows, columns):
    if isinstance(rows, Mapping) and "rows" in rows:
        columns = rows.get("columns") or columns
        rows = rows.get("rows")
    return [as_dict(row, columns) for row in (rows or [])]


def get_pagination(default_limit=20, max_limit=100):
    """Read ?page=&limit= using the conventions in docs/api-conventions.md.

    Returns (page, limit, offset). Page starts at 1; limit is capped at 100.
    """
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except (TypeError, ValueError):
        page = 1
    try:
        limit = int(request.args.get("limit", default_limit))
    except (TypeError, ValueError):
        limit = default_limit
    limit = min(max(limit, 1), max_limit)
    return page, limit, (page - 1) * limit


_SQLSTATE_KINDS = {
    "23505": "unique",
    "23514": "check",
    "23503": "fk",
    "23502": "not_null",
}
_TEXT_KINDS = (
    ("duplicate key", "unique"),
    ("unique constraint", "unique"),
    ("check constraint", "check"),
    ("foreign key", "fk"),
    ("not-null", "not_null"),
    ("not null constraint", "not_null"),
)


def db_error_kind(exc):
    """Classify a database exception: 'unique', 'check', 'fk', 'not_null' or None.

    Looks for a PostgreSQL SQLSTATE on the exception (or what it wraps) and
    falls back to matching the error text, so it still works if db.py wraps
    the driver's exception in its own class.
    """
    seen = set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        code = getattr(current, "pgcode", None) or getattr(current, "sqlstate", None)
        if code in _SQLSTATE_KINDS:
            return _SQLSTATE_KINDS[code]
        current = current.__cause__ or current.__context__
    text = str(exc).lower()
    for needle, kind in _TEXT_KINDS:
        if needle in text:
            return kind
    return None
