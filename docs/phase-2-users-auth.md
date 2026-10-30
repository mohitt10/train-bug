# Phase 2 — Authentication, Profiles and Follows

Branch: `phase-2-users`. Builds on Phase 1's `execute_query()` in `server/db.py`.

## Decisions

| Topic | Decision |
|---|---|
| Auth mechanism | Flask signed-cookie **session** (`session["user_id"]`). No tokens. |
| Password hashing | `werkzeug.security` (`generate_password_hash` / `check_password_hash`). Only the hash is stored; it is never returned by any endpoint. |
| `account_status` values | `active` (set on registration; `NULL` treated as active) and `suspended` (login and every protected endpoint return 403). |
| Visibility | All `/api/users/...` endpoints require login. |
| Account deletion | **Not implemented** (`DELETE /api/users/me`): waiting for the team's foreign-key deletion policy. |
| `password_hash` | Schema marks it NOT NULL in `schema.sql`; registration always supplies a hash. |
| Dev proxy | Vite proxies `/api` to `http://localhost:5000`, so the browser uses one origin and no CORS setup is needed. |

## Using auth from other phases

```python
from auth import login_required
from flask import g

@bp.post("/api/posts")
@login_required
def create_post():
    author_id = g.current_user_id   # int, never read the author from the request body
    me = g.current_user             # dict: user_id, username, email, display_name, bio, account_status, ...
```

`login_required` runs one `SELECT` per request (so a deleted or suspended user is rejected immediately).
Responses use `api_utils.success()` / `api_utils.error_response()`; `api_utils.as_dict()`,
`get_pagination()` and `db_error_kind()` are shared helpers.

React: `const { user } = useAuth()` (from `context/AuthContext.js`); add API calls on top of `apiRequest()` in `api/client.js`.

## Endpoints

All responses follow `docs/api-conventions.md`. Error bodies may also contain `error.details` (field → message) for validation errors.

| Method | Path | Auth | Success | Errors |
|---|---|---|---|---|
| POST | `/api/auth/register` | no | 201 `{user}` (and logs in) | 400 `VALIDATION_ERROR`, 409 `USERNAME_TAKEN` / `EMAIL_TAKEN` / `ACCOUNT_EXISTS` |
| POST | `/api/auth/login` | no | 200 `{user}` | 400, 401 `INVALID_CREDENTIALS`, 403 `ACCOUNT_SUSPENDED` |
| POST | `/api/auth/logout` | yes | 204 | 401 |
| GET | `/api/users/me` | yes | 200 profile + `email` | 401 |
| PATCH | `/api/users/me` | yes | 200 profile + `email` | 400 `VALIDATION_ERROR` / `NO_FIELDS` |
| GET | `/api/users/<id>` | yes | 200 profile | 404 `USER_NOT_FOUND` |
| GET | `/api/users/by-username/<username>` | yes | 200 profile | 404 |
| POST | `/api/users/<id>/follow` | yes | 201 `{following, follower_count, following_count}` | 400 `CANNOT_FOLLOW_SELF`, 404, 409 `ALREADY_FOLLOWING` |
| DELETE | `/api/users/<id>/follow` | yes | 200 `{following, follower_count, following_count}` | 404 `NOT_FOLLOWING` |
| GET | `/api/users/<id>/followers?page=&limit=` | yes | 200 `{items, page, limit, total}` | 404 |
| GET | `/api/users/<id>/following?page=&limit=` | yes | 200 `{items, page, limit, total}` | 404 |

Register body: `username` (3–50, letters/digits/underscore), `email`, `password` (8–128), optional `display_name`.
Login body: `identifier` (username or email) and `password`.
Profile: `user_id, username, display_name, bio, account_status, created_at, follower_count, following_count, is_following` (+ `email` on `/me` only).

## SQL per operation

| Operation | SQL |
|---|---|
| Register (duplicate check) | `SELECT username, email FROM users WHERE LOWER(username)=LOWER(%s) OR email=%s` |
| Register | `INSERT INTO users (...) VALUES (...) RETURNING ...` |
| Login | `SELECT ..., password_hash FROM users WHERE LOWER(username)=LOWER(%s) OR email=%s LIMIT 1` |
| Auth check (every protected request) | `SELECT ... FROM users WHERE user_id=%s` |
| Profile | `SELECT` from `users` with scalar subqueries counting `follows` and an `EXISTS` for `is_following` |
| Edit profile | `UPDATE users SET display_name=%s, bio=%s, updated_at=CURRENT_TIMESTAMP WHERE user_id=%s RETURNING user_id` |
| Follow | `INSERT INTO follows (follower_id, following_id, followed_at) VALUES (%s,%s,CURRENT_TIMESTAMP) RETURNING follower_id` |
| Unfollow | `DELETE FROM follows WHERE follower_id=%s AND following_id=%s RETURNING follower_id` |
| Followers list | `SELECT ... FROM follows f JOIN users u ON u.user_id = f.follower_id WHERE f.following_id=%s ORDER BY ... LIMIT %s OFFSET %s` |
| Following list | same, joined on `f.following_id`, filtered by `f.follower_id` |

Constraints demonstrated: `UNIQUE(username)`, `UNIQUE(email)`, `chk_no_self_follow`, composite PK on `follows`, foreign keys on `follows`.
Self-follow and duplicate follow are rejected by the database; the API only translates the error.

## Smoke test (curl)

```bash
curl -c jar -X POST localhost:5000/api/auth/register -H 'Content-Type: application/json' \
  -d '{"username":"alice","email":"alice@example.com","password":"password1"}'
curl -b jar localhost:5000/api/users/me
curl -b jar -X POST localhost:5000/api/users/1/follow     # your own id -> 400 CANNOT_FOLLOW_SELF
curl -b jar -X POST localhost:5000/api/auth/logout
curl -b jar localhost:5000/api/users/me                    # -> 401
```
