import os
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4


MAX_HISTORY = max(1, int(os.getenv("QUERY_HISTORY_LIMIT", "500")))

_query_history = deque(maxlen=MAX_HISTORY)
_history_lock = Lock()


def record_query(
    *,
    request_id,
    endpoint,
    action,
    statement,
    operation,
    status,
    duration_ms,
    affected_rows=None,
    error_summary=None,
):
    """Record safe metadata about a SQL execution."""

    entry = {
        "query_id": str(uuid4()),
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "action": action,
        "operation": operation,
        "statement": statement,
        "status": status,
        "duration_ms": round(duration_ms, 3),
        "affected_rows": affected_rows,
        "error_summary": error_summary,
    }

    with _history_lock:
        _query_history.append(entry)


def get_query_history():
    """Return a snapshot of the recorded query history."""

    with _history_lock:
        return [entry.copy() for entry in _query_history]


def clear_query_history():
    """Clear the in-memory query history."""

    with _history_lock:
        _query_history.clear()
