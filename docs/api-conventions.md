# WanderLog — API Conventions

## 1. General Conventions

- The backend uses Flask.
- API endpoints use the `/api/` prefix.
- JSON is the standard request and response format.
- HTTP methods should reflect the operation being performed.
- Database operations should use the shared `execute_query()` function.

## 2. HTTP Methods

| Method | Intended Use |
|---|---|
| GET | Retrieve resources |
| POST | Create resources |
| PUT | Replace resources |
| PATCH | Partially update resources |
| DELETE | Delete resources |

These conventions apply to future API endpoints.

## 3. Response Format

Successful responses should use JSON.

Example:

```json
{
    "status": "success",
    "data": {
        "id": 1
    }
}
```

Error responses should follow a consistent structure:

```json
{
    "status": "error",
    "error": {
        "code": "RESOURCE_NOT_FOUND",
        "message": "The requested resource was not found."
    }
}
```

Appropriate HTTP status codes should accompany responses.

## 4. HTTP Status Codes

| Code | Meaning |
|---|---|
| 200 | Successful request |
| 201 | Resource created |
| 204 | Successful request with no response body |
| 400 | Invalid request |
| 401 | Authentication required |
| 403 | Access forbidden |
| 404 | Resource not found |
| 409 | Resource conflict |
| 500 | Internal server error |
| 503 | Service unavailable |

## 5. Request Tracking

Each Flask request receives a unique request ID.

The backend returns this ID in the `X-Request-ID` response header.

Database queries executed during a request should be associated with that request ID in the query history.

## 6. Database Query Execution

All application database operations should use `execute_query()` from `server/db.py`.

SQL statements must use parameterized queries.

Example:

```python
execute_query(
    "SELECT * FROM users WHERE username = %s",
    ("example_user",),
    fetch="one",
)
```

User-provided values must never be inserted directly into SQL strings.

## 7. Pagination

Future endpoints returning collections should support pagination.

Recommended conventions:

- Default page size: 20
- Maximum page size: 100
- Page numbers start at 1.
- Results should use a deterministic ordering.

Example query parameters:

```text
?page=1&limit=20
```

## 8. Error Handling

- Responses must not expose database credentials or internal implementation details.
- Raw SQL exceptions should not be returned to clients.
- Database failures should be recorded by the query-monitoring mechanism.
- Appropriate HTTP status codes should be returned.

## 9. Current Implementation Status

The current backend provides:

- `GET /api/health`
- `GET /api/health/db`

The response structures, pagination rules, and other conventions in this document are guidelines for future endpoints. They are not all implemented yet.