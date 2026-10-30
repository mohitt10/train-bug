"""
DEV STUB: replace with Phase 1/2 integration. See docs/phase3-integration.md

This module isolates Phase 3 from Phase 1 (database connection, query capture)
and Phase 2 (authentication, user session). In production, an integrator will
replace the internals of these functions with calls to Phase 1's execute_query
and Phase 2's session/token auth.
"""

import os
import functools
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple, Union
from flask import g, has_request_context, jsonify, request

# Support both psycopg (v3) and psycopg2
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import errors as pg_errors
    _DRIVER = "psycopg2"
except ImportError:
    try:
        import psycopg
        from psycopg.rows import dict_row
        from psycopg import errors as pg_errors
        _DRIVER = "psycopg"
    except ImportError:
        _DRIVER = None
        pg_errors = None


def _get_db_connection():
    """Establish a database connection using environment variables."""
    if _DRIVER is None:
        raise RuntimeError("Neither psycopg nor psycopg2 is installed.")

    database_url = os.getenv("DATABASE_URL")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "wanderlog")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")

    if _DRIVER == "psycopg2":
        if database_url:
            return psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        return psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            cursor_factory=RealDictCursor,
        )
    else:
        conn_str = database_url or f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        return psycopg.connect(conn_str, row_factory=dict_row)


@contextmanager
def transaction():
    """
    Context manager for multi-statement atomic operations.
    Commits on clean exit, rolls back on exception.
    """
    if not has_request_context():
        # Standalone context
        conn = _get_db_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return

    # Check if a transaction is already active in this request
    existing_conn = getattr(g, "_phase3_tx_conn", None)
    if existing_conn is not None:
        # Re-use existing transaction
        yield existing_conn
        return

    conn = _get_db_connection()
    g._phase3_tx_conn = conn
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        g._phase3_tx_conn = None
        conn.close()


def run_query(
    sql: str,
    params: tuple = (),
    *,
    action: str,
    fetch: str = "all",
) -> Union[List[Dict[str, Any]], Optional[Dict[str, Any]], int]:
    """
    Executes parameterized SQL (%s placeholders).
    
    Args:
        sql: SQL query template with %s placeholders.
        params: Tuple of query parameter values.
        action: Human-readable action label (e.g. 'feed:list', 'post:create').
        fetch: One of 'all', 'one', or 'none'.
               - 'all': returns list of dict rows
               - 'one': returns single dict or None
               - 'none': returns affected row count (int)
    """
    if fetch not in ("all", "one", "none"):
        raise ValueError("fetch must be 'all', 'one', or 'none'.")

    # If within a transaction, use the shared transaction connection
    tx_conn = getattr(g, "_phase3_tx_conn", None) if has_request_context() else None
    conn = tx_conn if tx_conn is not None else _get_db_connection()
    cursor = None

    try:
        if _DRIVER == "psycopg2":
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor(row_factory=dict_row)

        cursor.execute(sql, params)

        if fetch == "one":
            row = cursor.fetchone()
            result = dict(row) if row is not None else None
        elif fetch == "all":
            rows = cursor.fetchall()
            result = [dict(r) for r in rows]
        else:
            result = cursor.rowcount

        if tx_conn is None:
            conn.commit()

        return result

    except Exception:
        if tx_conn is None:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if tx_conn is None:
            conn.close()


def current_user_id() -> Optional[int]:
    """
    DEV STUB: Extracts authenticated user ID from request headers.
    In Phase 2 integration, this will inspect Flask session or auth tokens.
    """
    if not has_request_context():
        return None

    header_val = request.headers.get("X-Dev-User-Id")
    if header_val:
        try:
            uid = int(header_val)
            if uid > 0:
                return uid
        except (ValueError, TypeError):
            pass

    # Allow query parameter in dev for browser testing convenience
    arg_val = request.args.get("dev_user_id")
    if arg_val:
        try:
            uid = int(arg_val)
            if uid > 0:
                return uid
        except (ValueError, TypeError):
            pass

    return None


def login_required(f):
    """Decorator ensuring the request has an authenticated user."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        uid = current_user_id()
        if not uid:
            return jsonify({
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Authentication required. Please provide credentials.",
                }
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def map_db_error(exc: Exception) -> Tuple[int, str]:
    """
    Translates database driver exceptions into safe HTTP status and public message.
    Never leaks SQL, schemas, or parameter values.
    """
    # Check SQLSTATE or pgcode
    pgcode = getattr(exc, "pgcode", getattr(exc, "sqlstate", None))

    if pgcode == "23503":
        return 400, "The referenced resource does not exist."
    if pgcode == "23505":
        return 409, "A conflicting record already exists."
    if pgcode == "23514":
        return 400, "The submitted data violated a database constraint."
    if pgcode == "23502":
        return 400, "A required field was missing or null."

    return 500, "A database error occurred while processing the request."
