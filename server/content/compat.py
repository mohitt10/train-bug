"""Adapters connecting Phase 3 content endpoints to shared DB and Phase 2 auth."""

import os
import functools
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple, Union
from flask import g, has_request_context, request, session

from auth import login_required as session_login_required
import db
from .responses import error_response


@contextmanager
def transaction():
    """Context manager for transactions, delegated to Phase 1's db.transaction."""
    with db.transaction() as conn:
        yield conn


def run_query(
    sql: str,
    params: tuple = (),
    *,
    action: str,
    fetch: str = "all",
) -> Union[List[Dict[str, Any]], Optional[Dict[str, Any]], int]:
    """
    Executes parameterized SQL via Phase 1 db.execute_query and maps results to dicts.

    Args:
        sql: Parameterized SQL statement string.
        params: Tuple of query parameter values.
        action: Descriptive action label for query monitoring.
        fetch: One of 'all', 'one', or 'none'.
    """
    if fetch not in ("all", "one", "none"):
        raise ValueError("fetch must be 'all', 'one', or 'none'.")

    db_fetch = None if fetch == "none" else fetch
    result = db.execute_query(sql, params, fetch=db_fetch, action=action)

    if fetch == "none":
        return result.get("affected_rows") or 0

    cols = result.get("columns") or []
    rows = result.get("rows")

    if fetch == "one":
        if rows is None:
            return None
        return dict(zip(cols, rows))

    if rows is None:
        return []

    return [dict(zip(cols, r)) for r in rows]


def current_user_id() -> Optional[int]:
    """
    Returns the authenticated Phase 2 user ID, or a verified dev user when enabled.
    """
    if not has_request_context():
        return None

    session_user_id = getattr(g, "current_user_id", None)
    if session_user_id is not None:
        return session_user_id

    if hasattr(g, "_cached_user_id"):
        return g._cached_user_id

    allow_dev_auth = os.getenv("ALLOW_DEV_AUTH", "0") == "1"
    if not allow_dev_auth:
        g._cached_user_id = None
        return None

    header_val = request.headers.get("X-Dev-User-Id")
    if not header_val:
        g._cached_user_id = None
        return None

    try:
        uid = int(header_val)
        if uid <= 0:
            g._cached_user_id = None
            return None
    except (ValueError, TypeError):
        g._cached_user_id = None
        return None

    # Verify user exists in the database
    user_row = run_query(
        "SELECT user_id FROM users WHERE user_id = %s;",
        (uid,),
        action="auth:dev_user_lookup",
        fetch="one",
    )
    if user_row:
        g._cached_user_id = uid
        return uid

    g._cached_user_id = None
    return None


def login_required(f):
    """Enforce Phase 2 session auth, with optional local dev-header auth."""
    session_protected = session_login_required(f)

    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if has_request_context() and session.get("user_id") is not None:
            return session_protected(*args, **kwargs)

        uid = current_user_id()
        if not uid:
            return error_response(
                "UNAUTHORIZED",
                "Authentication required. Please provide credentials.",
                401,
            )
        return f(*args, **kwargs)
    return decorated_function


def map_db_error(exc: Exception, is_delete: bool = False) -> Tuple[int, str]:
    """
    Translates database driver exceptions into safe HTTP status and public message.
    Conceals SQL and database internals.
    """
    sqlstate = getattr(exc, "sqlstate", getattr(exc, "pgcode", None))

    if sqlstate == "23503":
        if is_delete:
            return 409, "This item cannot be deleted because other records still depend on it."
        return 400, "The referenced resource does not exist."
    if sqlstate == "23505":
        return 409, "A conflicting record already exists."
    if sqlstate == "23514":
        return 400, "The submitted data violated a database constraint."
    if sqlstate == "23502":
        return 400, "A required field was missing or null."
    if sqlstate in ("22007", "22008", "22P02", "22003"):
        return 400, "Invalid value supplied."
    if sqlstate in ("40001", "40P01"):
        return 409, "Please retry the request."

    return 500, "A database error occurred while processing the request."


def map_db_error_for_delete(exc: Exception) -> Tuple[int, str]:
    """Helper specifically for DELETE operations."""
    return map_db_error(exc, is_delete=True)
