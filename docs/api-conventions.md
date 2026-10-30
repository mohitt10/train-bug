# WanderLog — API Conventions

## 1. General Conventions

- The backend uses Flask.
- API endpoints use the `/api/` prefix.
- JSON is the standard request and response format.
- HTTP methods reflect the operation being performed.
- All database operations use explicit parameterized SQL via `execute_query()` from `server/db.py`.

## 2. HTTP Methods

| Method | Intended Use |
|---|---|
| GET | Retrieve resources |
| POST | Create resources |
| PUT | Replace resources |
| PATCH | Partially update resources |
| DELETE | Delete resources |

## 3. Response Format

### Successful Responses
Successful responses return clean JSON. Resource endpoints return the resource object directly (or a collection object with an `items` array):

Single resource example (`POST /api/posts`, `GET /api/posts/<id>`):
```json
{
    "post_id": 1,
    "user_id": 1,
    "title": "Sunrise over the Sahyadri Ridges",
    "content": "Started the climb at 4:30 AM...",
    "location": "Kalsubai Peak, MH",
    "created_at": "2026-10-30T09:27:00+00:00",
    "updated_at": null,
    "comment_count": 2,
    "username": "alex_traveler",
    "display_name": "Alex Mercer",
    "author": {
        "user_id": 1,
        "username": "alex_traveler",
        "display_name": "Alex Mercer"
    }
}
```

Collection response example (`GET /api/feed`):
```json
{
    "items": [ ... ],
    "next_cursor": "eyJjIjogIjIwMjYtMTAtMzBUMDk6Mjc6MDAiLCAiaWQiOiAxfQ=="
}
```

### Error Responses
Error responses strictly follow the standard structure across all endpoints:

```json
{
    "status": "error",
    "error": {
        "code": "RESOURCE_NOT_FOUND",
        "message": "The requested resource was not found."
    }
}
```

## 4. HTTP Status Codes

| Code | Meaning |
|---|---|
| 200 | Successful request |
| 201 | Resource created |
| 204 | Successful request with no response body |
| 400 | Invalid request / validation error |
| 401 | Authentication required |
| 403 | Access forbidden / ownership check failure |
| 404 | Resource not found |
| 409 | Resource conflict / constraint violation / reported content deletion lock |
| 500 | Internal server error |
| 503 | Service unavailable |

## 5. Request Tracking

Each Flask request receives a unique request ID.

The backend returns this ID in the `X-Request-ID` response header.

Database queries executed during a request are associated with that request ID in the query history.

## 6. Database Query Execution

All application database operations must use parameterized queries through `server/db.py`.

Example:

```python
execute_query(
    "SELECT * FROM users WHERE username = %s",
    ("example_user",),
    fetch="one",
)
```

User-provided values must never be concatenated into SQL strings.

## 7. Pagination (Cursor-Based)

Feed and timeline collections implement deterministic, cursor-based pagination:
- `limit`: Default 20, maximum 50.
- `cursor`: Opaque URL-safe base64 string encoding `(created_at, post_id)`.
- Internal structure: `base64(json({"c": "<iso_timestamp>", "id": <post_id>}))`.
- The database sorts by `created_at DESC, post_id DESC` and evaluates:
  ```sql
  WHERE (p.created_at < %s) OR (p.created_at = %s AND p.post_id < %s)
  ```
- If a next page exists, `next_cursor` contains the encoded token for the last item; otherwise `next_cursor` is `null`.

## 8. Error Handling

- Responses must not expose database credentials or internal implementation details.
- Raw SQL exceptions are never returned to clients; they are mapped to safe messages and logged with SQLSTATE only.
- Database failures are recorded by `query_monitor.py` with status `failure`.
- Appropriate HTTP status codes accompany every response.
