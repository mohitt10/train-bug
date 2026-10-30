import time
import re
import psycopg
from flask import g, has_request_context

from config import Config
from query_monitor import record_query


def get_sql_operation(sql):
    """Identify the main SQL operation, including WITH statements."""

    tokens = []
    depth = 0
    i = 0

    while i < len(sql):
        char = sql[i]

        # Skip whitespace.
        if char.isspace():
            i += 1
            continue

        # Skip line comments.
        if sql.startswith("--", i):
            newline = sql.find("\n", i)
            i = len(sql) if newline == -1 else newline + 1
            continue

        # Skip block comments.
        if sql.startswith("/*", i):
            end = sql.find("*/", i + 2)
            i = len(sql) if end == -1 else end + 2
            continue

        # Skip quoted strings and identifiers.
        if char in ("'", '"'):
            quote = char
            i += 1

            while i < len(sql):
                if sql[i] == quote:
                    if i + 1 < len(sql) and sql[i + 1] == quote:
                        i += 2
                        continue
                    i += 1
                    break

                if sql[i] == "\\" and quote == "'":
                    i += 2
                else:
                    i += 1

            continue

        if char == "(":
            depth += 1
            i += 1
            continue

        if char == ")":
            depth = max(0, depth - 1)
            i += 1
            continue

        match = re.match(r"[A-Za-z_][A-Za-z_0-9]*", sql[i:])

        if match:
            tokens.append((match.group().upper(), depth))
            i += len(match.group())
        else:
            i += 1

    if not tokens:
        return "UNKNOWN"

    first_operation = tokens[0][0]

    if first_operation != "WITH":
        return first_operation

    operations = {"SELECT", "INSERT", "UPDATE", "DELETE", "MERGE"}

    for token, token_depth in tokens[1:]:
        if token_depth == 0 and token in operations:
            return token

    return "WITH"


def get_connection():
    """Create a new PostgreSQL connection."""

    if not Config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured.")

    return psycopg.connect(
        Config.DATABASE_URL,
        connect_timeout=5,
    )


def execute_query(sql, params=None, *, fetch=None, action=None):
    """
    Execute parameterized SQL and record its execution metadata.

    Args:
        sql: SQL statement using psycopg placeholders (%s).
        params: Query parameters, kept out of the query history.
        fetch: None, "one", or "all".
        action: Optional descriptive action name.

    Returns:
        A dictionary containing rows and affected_rows.

    Raises:
        The original database exception if execution fails.
    """

    if fetch not in (None, "one", "all"):
        raise ValueError("fetch must be None, 'one', or 'all'.")

    operation = get_sql_operation(sql)

    request_id = None
    endpoint = None

    if has_request_context():
        request_id = getattr(g, "request_id", None)
        endpoint = getattr(g, "endpoint", None)

    query_action = action or endpoint or "database_operation"

    start_time = time.perf_counter()
    connection = None
    cursor = None
    affected_rows = None
    execution_attempted = False

    try:
        connection = get_connection()
        cursor = connection.cursor()

        execution_attempted = True
        cursor.execute(sql, params)

        affected_rows = cursor.rowcount

        if fetch == "one":
            rows = cursor.fetchone()
        elif fetch == "all":
            rows = cursor.fetchall()
        else:
            rows = None

        connection.commit()

        duration_ms = (time.perf_counter() - start_time) * 1000

        record_query(
            request_id=request_id,
            endpoint=endpoint,
            action=query_action,
            statement=sql,
            operation=operation,
            status="success",
            duration_ms=duration_ms,
            affected_rows=affected_rows,
        )

        return {
            "rows": rows,
            "affected_rows": affected_rows,
        }

    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except psycopg.Error:
                pass

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Do not store raw exception messages: they may contain
        # sensitive database details or parameter values.
        sqlstate = getattr(exc, "sqlstate", None)
        error_summary = (
            f"Database operation failed (SQLSTATE {sqlstate})."
            if sqlstate
            else f"Database operation failed ({type(exc).__name__})."
        )

        if execution_attempted:
            record_query(
                request_id=request_id,
                endpoint=endpoint,
                action=query_action,
                statement=sql,
                operation=operation,
                status="failure",
                duration_ms=duration_ms,
                affected_rows=affected_rows,
                error_summary=error_summary,
            )

        raise

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()
