# WanderLog — Phase 3 Integration Guide

This document specifies the exact adapter interfaces that connect Phase 3 (Posts, Comments, Replies, Feed) to **Phase 1** (Database connection, schema, SQL Query capture) and **Phase 2** (Authentication, User session).

To ensure complete modularity, **only two adapter files** know about dependencies on other phases:
1. Backend: `server/content/compat.py`
2. Frontend: `client/src/api/authBridge.js`

No other file in `server/content/` or `client/src/features/content/` touches authentication mechanics or direct database drivers.

---

## 1. Backend Adapter: `server/content/compat.py`

When merging Phase 1 and Phase 2, replace the dev stubs inside `server/content/compat.py`.

### Required Exports & Signatures

```python
def run_query(
    sql: str,
    params: tuple = (),
    *,
    action: str,
    fetch: str = "all",
) -> Union[List[Dict[str, Any]], Optional[Dict[str, Any]], int]:
```
* **Purpose**: Executes parameterized SQL (`%s` placeholders) and routes queries to Phase 1's shared query capture system.
* **Arguments**:
  * `sql`: Parameterized SQL statement string.
  * `params`: Query parameter tuple (values are kept out of query logs).
  * `action`: Human-readable action label (e.g., `'feed:list'`, `'post:create'`).
  * `fetch`: One of `'all'` (returns list of dict rows), `'one'` (returns single dict row or None), or `'none'` (returns integer affected row count).
* **Integration with Phase 1**: Call Phase 1's `server.db.execute_query(sql, params, fetch=fetch, action=action)` and map result rows to dictionaries.

---

```python
@contextmanager
def transaction():
```
* **Purpose**: Context manager providing atomic multi-statement database transactions.
* **Behavior**: Commits when leaving the context cleanly; rolls back if an unhandled exception is raised.
* **Integration with Phase 1**: Use Phase 1's connection management or session-level connection pooling.

---

```python
def current_user_id() -> Optional[int]:
```
* **Purpose**: Returns the `user_id` of the currently authenticated user, or `None` if the request is unauthenticated.
* **Dev Stub Behavior**: Reads `X-Dev-User-Id` request header or `?dev_user_id=` query param.
* **Integration with Phase 2**: Replace with Phase 2's session lookup (e.g., `session.get("user_id")` or decoding JWT/token stored in `g.current_user`).

---

```python
def login_required(f):
```
* **Purpose**: Flask route decorator ensuring that only authenticated users can access the endpoint. Returns `401 Unauthorized` with `{"error": {"code": "UNAUTHORIZED", "message": "..."}}` if unauthenticated.
* **Integration with Phase 2**: Replace with Phase 2's `@login_required` or keep the wrapper delegating to `current_user_id()`.

---

```python
def map_db_error(exc: Exception) -> Tuple[int, str]:
```
* **Purpose**: Converts database driver exceptions into safe HTTP status codes and user-facing error messages, concealing internal database structures or credentials.
* **Returns**: `(http_status_code, public_message_string)`.
* **Standard Mappings**:
  * Foreign key violation (`23503`) $\rightarrow$ `(400, "The referenced resource does not exist.")`
  * Unique constraint violation (`23505`) $\rightarrow$ `(409, "A conflicting record already exists.")`
  * Check violation (`23514`) $\rightarrow$ `(400, "The submitted data violated a database constraint.")`
  * Not null violation (`23502`) $\rightarrow$ `(400, "A required field was missing or null.")`
  * Fallback $\rightarrow$ `(500, "A database error occurred while processing the request.")`

---

## 2. Frontend Adapter: `client/src/api/authBridge.js`

When merging Phase 2, update `client/src/api/authBridge.js`.

### Required Exports & Signatures

```javascript
export function useCurrentUser(): {
  user: { user_id: number, username: string, display_name: string } | null,
  isLoggedIn: boolean,
  setDevUserId?: (id: number) => void,
  availableDevUsers?: Array<{ user_id: number, username: string, display_name: string }>
}
```
* **Purpose**: React hook providing the authenticated user object and login status to content components.
* **Dev Stub Behavior**: Manages an in-memory active user selected from the dev toolbar.
* **Integration with Phase 2**: Replace internal state with Phase 2's `AuthContext` or state manager.

---

```javascript
export function getAuthHeaders(): Record<string, string>
```
* **Purpose**: Returns the HTTP headers required to authenticate API requests made via `contentApi.js`.
* **Dev Stub Behavior**: Returns `{ 'X-Dev-User-Id': String(currentUserId) }`.
* **Integration with Phase 2**: Return session cookie credentials, Bearer tokens (`{ 'Authorization': `Bearer ${token}` }`), or whatever headers Phase 2 establishes.

---

## 3. Checklist for Final Main Integration

1. In `server/app.py`: Verify line `from content import content_bp` and `app.register_blueprint(content_bp)` are present.
2. In `server/content/compat.py`: Update `_get_db_connection()` and `current_user_id()` to point to Phase 1 & 2 utilities.
3. In `client/src/api/authBridge.js`: Update `useCurrentUser()` and `getAuthHeaders()` to consume Phase 2's auth provider.
4. Verify all tests pass: `python -m unittest server/tests/test_content.py`.
