# WanderLog — Phase 3 Integration Guide

This document describes how Phase 3 (posts, comments, replies, and feed) integrates
with Phase 1 (database connection, schema, and SQL query capture) and Phase 2
(authentication, profiles, and follows).

## Integration Status

Phase 3 content queries use Phase 1's `server.db.execute_query` through
`server/content/compat.py`. Results are mapped to dictionaries, queries are recorded
by `server.query_monitor` with action labels, durations, request IDs, and endpoints,
and multi-statement content deletes use the shared transaction manager.

The Phase 2 `auth_bp` and `users_bp` blueprints are registered by `server/app.py`.
Content routes use Phase 2's signed-session authentication and server-derived
`g.current_user_id`. `ALLOW_DEV_AUTH=1` enables the verified `X-Dev-User-Id` fallback
for local testing only. The content frontend reads Phase 2's `AuthContext` and sends
same-origin cookies. Login, registration, profile, and follow screens remain
available alongside the Phase 3 feed.

## Shared Database Interfaces

```python
def run_query(
    sql: str,
    params: tuple = (),
    *,
    action: str,
    fetch: str = "all",
) -> Union[List[Dict[str, Any]], Optional[Dict[str, Any]], int]:
```

Fetch modes:

- `all`: list of dictionary rows.
- `one`: one dictionary row or `None`.
- `none`: affected row count as an integer.

```python
@contextmanager
def transaction():
```

The transaction context manager reuses outer transactions when nested, commits on
clean exit, and rolls back on exceptions.

```python
def map_db_error(exc: Exception, is_delete: bool = False) -> Tuple[int, str]:
def map_db_error_for_delete(exc: Exception) -> Tuple[int, str]:
```

These helpers translate PostgreSQL SQLSTATE errors into safe HTTP statuses and
user-facing messages. Foreign-key violations during deletion map to HTTP 409.
