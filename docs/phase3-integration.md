# WanderLog — Phase 3 Integration Guide

This document specifies the integration boundaries connecting Phase 3 (Posts, Comments, Replies, Feed) to **Phase 1** (Database connection, schema, SQL Query capture) and **Phase 2** (Authentication, User session).

---

## Current Status: Phase 1 Fully Integrated

`server/content/compat.py` is **now fully wired into Phase 1**:
- `compat.run_query` directly executes through `server.db.execute_query` and formats rows as dictionary records using `columns`.
- `compat.transaction` directly delegates to Phase 1's `server.db.transaction` context manager.
- Every content query is captured by `server.query_monitor.record_query` with action labels, execution durations, request IDs, and endpoints.
- `psycopg2-binary` has been removed; all queries use Phase 1's `psycopg` driver.

---

## Phase 2 Integration Checklist

Only the authentication boundary in `server/content/compat.py` and `client/src/api/authBridge.js` awaits Phase 2:

### 1. Backend: `server/content/compat.py`

Replace the dev stub in `current_user_id()` with Phase 2's session/token lookup:

```python
def current_user_id() -> Optional[int]:
    """
    In Phase 2: Inspect Flask session or verify Bearer token from headers.
    Return authenticated user_id as int, or None if unauthenticated.
    """
```

`login_required(f)` will then automatically enforce real authentication across all protected content endpoints.

### 2. Frontend: `client/src/api/authBridge.js`

Update `useCurrentUser()` and `getAuthHeaders()` to consume Phase 2's authentication state:

```javascript
export function useCurrentUser(): {
  user: { user_id: number, username: string, display_name: string } | null,
  isLoggedIn: boolean
}

export function getAuthHeaders(): Record<string, string>
```

---

## Shared Database Interfaces Reference

```python
def run_query(
    sql: str,
    params: tuple = (),
    *,
    action: str,
    fetch: str = "all",
) -> Union[List[Dict[str, Any]], Optional[Dict[str, Any]], int]:
```
* **Fetch Modes**:
  * `'all'` $\to$ returns list of dict rows (`[ {col: val, ...}, ... ]`)
  * `'one'` $\to$ returns single dict row or `None`
  * `'none'` $\to$ returns affected row count as `int`

```python
@contextmanager
def transaction():
```
* Multi-statement atomic transaction context manager that reuses outer transactions if nested.
* Commits on clean exit; rolls back on exception.

```python
def map_db_error(exc: Exception, is_delete: bool = False) -> Tuple[int, str]:
def map_db_error_for_delete(exc: Exception) -> Tuple[int, str]:
```
* Translates PostgreSQL SQLSTATE errors into safe HTTP status codes and public user-facing messages.
* ForeignKey violation (`23503`) during delete maps to `(409, "This item cannot be deleted because other records still depend on it.")`.
