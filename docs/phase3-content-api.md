# WanderLog — Phase 3 Content API Specification

Phase 3 implements the content and feed engine for WanderLog, covering posts, comments, replies, and cursor-paginated feeds.

---

## 1. General Conventions & Error Format

- Base path for all endpoints: `/api`
- Content-Type: `application/json`
- Character encoding: UTF-8
- Media uploads: **STRICTLY NONE** (text-only social media platform)

### Standard Error Response Format
All errors return a standard JSON structure with the appropriate HTTP status code:

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Post content cannot be empty."
  }
}
```

### Standard HTTP Status Codes
| HTTP Status | Meaning | Usage |
|:---|:---|:---|
| `200 OK` | Success | Successful resource retrieval or update |
| `201 Created` | Created | Successful resource creation (`posts`, `comments`, `replies`) |
| `204 No Content` | No Content | Successful resource deletion |
| `400 Bad Request` | Bad Request | Validation errors (empty text, limit exceeded, malformed JSON, invalid cursor) |
| `401 Unauthorized` | Unauthorized | Unauthenticated request on protected route |
| `403 Forbidden` | Forbidden | Attempt to edit or delete content owned by another user |
| `404 Not Found` | Not Found | Resource or parent resource does not exist |
| `409 Conflict` | Conflict | Database unique constraint violation, concurrency conflict, or reported content deletion lock |
| `500 Server Error` | Server Error | Unhandled server or database exception (safe error message) |

---

## 2. Validation & Size Limits

| Entity | Field | Rules & Limits |
|:---|:---|:---|
| **Post** | `title` | Optional; string; max 200 characters; nullable |
| **Post** | `content` | **Required**; non-empty after trim; **NO length limit** (stored as `TEXT` in DB) |
| **Post** | `location` | Optional; string; max 100 characters; nullable |
| **Post** | `updated_at` | Stays `NULL` on creation. The UI interprets `NULL` as "not edited". |
| **Comment** | `content` | **Required**; non-empty after trim; **max 2,000 characters** (`VARCHAR(2000)`) |
| **Reply** | `content` | **Required**; non-empty after trim; **max 2,000 characters** (`VARCHAR(2000)`) |

---

## 3. Ownership & Deletion Policy

- **Author attribution**: The server derives `user_id` strictly from authenticated context (`current_user_id()`), **never** from the request body.
- **Backend enforcement**: On `PATCH` and `DELETE` requests:
  1. The server queries the database for the record and its `user_id` inside `transaction()` using `SELECT ... FOR UPDATE` to prevent concurrency races.
  2. If the record does not exist: returns `404 Not Found`.
  3. If `record.user_id != current_user_id()`: returns `403 Forbidden` (`FORBIDDEN`).
- **Deletion Policy with Reports (Phase 4 decision)**:
  * Deletion checks whether any record in the `reports` table references the post, comment, or reply (or any nested comments/replies of the post).
  * If a report record exists, the delete operation is **aborted** and returns HTTP 409.
    Reports are retained as moderation history, and the schema has restrictive foreign
    keys to their target. Therefore, reported content remains undeletable even after a
    report is reviewed; review does not erase the audit record:
    ```json
    {
      "status": "error",
      "error": {
        "code": "CONTENT_HAS_REPORTS",
        "message": "This content has a retained report and cannot be deleted."
      }
    }
    ```
  * If no reports exist, cascading deletion proceeds in strict foreign key dependency order:
    1. Delete child `comment_likes`
    2. Delete child `post_likes`
    3. Delete child `replies`
    4. Delete child `comments`
    5. Delete `posts`

Likes are supported for posts and comments only. No reply-like table or endpoint exists.
`GET /api/feed`, user timelines, post detail, and comment lists include `like_count` and
`liked_by_me`; POST/DELETE `/api/posts/<id>/like` and
`/api/comments/<id>/like` update the current user's like.

Authenticated users may submit `POST /api/reports` with `target_type` (`post`,
`comment`, or `reply`), `target_id`, and a reason of 1–500 characters. The server
derives reporter identity and selects exactly one target column. Reports start as
`pending`; moderators may transition a pending report once to `resolved` or `dismissed`.
Both outcomes are terminal. The reviewer's ID always comes from the authenticated
moderator session. Reports are not deleted through the API.

Moderator-only routes: `GET /api/moderation/me`,
`GET /api/moderation/reports?status=pending|resolved|dismissed`,
`GET /api/moderation/reports/<report_id>`, and
`PATCH /api/moderation/reports/<report_id>` with `{"status":"resolved"}` or
`{"status":"dismissed"}`.

The moderator-only SQL inspector is available at `GET /api/query-inspector/queries`
and `GET /api/query-inspector/queries/<query_id>`. It returns bounded in-memory query
metadata and SQL templates, never SQL parameter values, and does not execute submitted
SQL.

---

## 4. Cursor-Based Pagination Format

Feed and timeline endpoints support deterministic cursor-based pagination:
- `limit`: Integer between 1 and 50 (default: `20`).
- `cursor`: Opaque URL-safe base64 string encoding `(created_at, post_id)`.
- Internal structure: `base64(json({"c": "<iso8601_timestamp>", "id": <post_id>}))`.
- The database sorts by `created_at DESC, post_id DESC` and evaluates:
  ```sql
  WHERE (p.created_at < %s) OR (p.created_at = %s AND p.post_id < %s)
  ```
- If additional items remain, the response returns `next_cursor: "<string>"`; otherwise `next_cursor: null`.

---

## 5. Endpoints Specification

### 5.1 Posts & Feed

#### `GET /api/feed`
Retrieves chronological feed of newest posts.
- **Query params**: `limit` (default 20, max 50), `cursor` (opaque base64 string).
- **Response (200 OK)**:
```json
{
  "items": [
    {
      "post_id": 1,
      "user_id": 1,
      "title": "Sunrise over the Sahyadri Ridges",
      "content": "Started the climb at 4:30 AM in pitch black mist...",
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
  ],
  "next_cursor": "eyJjIjogIjIwMjYtMTAtMzBUMDk6Mjc6MDAiLCAiaWQiOiAxfQ=="
}
```

#### `GET /api/users/<user_id>/posts`
Retrieves posts authored by a specific user.
- **Query params**: `limit` (default 20), `cursor` (optional).
- **Response (200 OK)**:
```json
{
  "items": [...],
  "next_cursor": null,
  "user": {
    "user_id": 1,
    "username": "alex_traveler",
    "display_name": "Alex Mercer"
  }
}
```

#### `POST /api/posts`
Creates a new post authored by the authenticated user.
- **Authentication**: Phase 2 session cookie; local testing may use `X-Dev-User-Id` when `ALLOW_DEV_AUTH=1`.
- **Request Body**:
```json
{
  "title": "Narrow Gauge Railway",
  "content": "Rode the mountain train across 102 tunnels today.",
  "location": "Shimla"
}
```
- **Response (201 Created)**: Serialized post object.

#### `GET /api/posts/<post_id>`
Retrieves a single post and its metadata.
- **Response (200 OK)**: Serialized post object.
- **Response (404 Not Found)**:
```json
{
  "status": "error",
  "error": {
    "code": "NOT_FOUND",
    "message": "Post not found."
  }
}
```

#### `PATCH /api/posts/<post_id>`
Updates an owned post's `title`, `content`, or `location`.
- **Authentication**: Phase 2 session cookie; local testing may use `X-Dev-User-Id` when `ALLOW_DEV_AUTH=1`.
- **Request Body**: (at least one field)
```json
{
  "title": "Updated Title",
  "content": "Updated content story.",
  "location": "Updated Location"
}
```
- **Response (200 OK)**: Serialized updated post (`updated_at` updated).
- **Response (403 Forbidden)**: If requester is not the author.

#### `DELETE /api/posts/<post_id>`
Deletes an owned post, its likes, comments, and replies.
- **Authentication**: Phase 2 session cookie; local testing may use `X-Dev-User-Id` when `ALLOW_DEV_AUTH=1`.
- **Response (204 No Content)**: Empty body.
- **Response (403 Forbidden)**: If requester is not the author.
- **Response (409 Conflict)**: If post or its comments/replies have reports.

---

### 5.2 Comments

#### `GET /api/posts/<post_id>/comments`
Retrieves chronological discussion comments for a post.
- **Response (200 OK)**:
```json
{
  "items": [
    {
      "comment_id": 1,
      "post_id": 1,
      "user_id": 2,
      "content": "Did you take the eastern ladder route or the village trail?",
      "created_at": "2026-10-30T09:30:00+00:00",
      "updated_at": null,
      "reply_count": 1,
      "username": "sarah_journeys",
      "display_name": "Sarah Jenkins",
      "author": {
        "user_id": 2,
        "username": "sarah_journeys",
        "display_name": "Sarah Jenkins"
      }
    }
  ]
}
```

#### `POST /api/posts/<post_id>/comments`
Adds a comment to a post (max 2,000 characters).
- **Request Body**:
```json
{
  "content": "Took the village trail going up!"
}
```
- **Response (201 Created)**: Serialized comment object.
- **Response (404 Not Found)**: If target post does not exist (or was deleted).

#### `PATCH /api/comments/<comment_id>`
Edits an owned comment.
- **Request Body**: `{"content": "Updated comment content."}`
- **Response (200 OK)**: Serialized comment object.

#### `DELETE /api/comments/<comment_id>`
Deletes an owned comment and its nested replies and likes.
- **Response (204 No Content)**: Empty body.
- **Response (409 Conflict)**: If comment or its replies have reports.

---

### 5.3 Replies

#### `GET /api/comments/<comment_id>/replies`
Retrieves chronological replies under a comment.
- **Response (200 OK)**:
```json
{
  "items": [
    {
      "reply_id": 1,
      "comment_id": 1,
      "user_id": 1,
      "content": "Took the village trail going up and ladder route down!",
      "created_at": "2026-10-30T09:45:00+00:00",
      "updated_at": null,
      "username": "alex_traveler",
      "display_name": "Alex Mercer",
      "author": {
        "user_id": 1,
        "username": "alex_traveler",
        "display_name": "Alex Mercer"
      }
    }
  ]
}
```

#### `POST /api/comments/<comment_id>/replies`
Adds a reply to a comment (max 2,000 characters).
- **Request Body**: `{"content": "Glad you enjoyed the climb!"}`
- **Response (201 Created)**: Serialized reply object.
- **Response (404 Not Found)**: If target comment does not exist.

#### `PATCH /api/replies/<reply_id>`
Edits an owned reply.
- **Request Body**: `{"content": "Updated reply content."}`
- **Response (200 OK)**: Serialized reply object.

#### `DELETE /api/replies/<reply_id>`
Deletes an owned reply.
- **Response (204 No Content)**: Empty body.
- **Response (409 Conflict)**: If reply has reports.

---

## 6. Complete SQL Actions Reference

Every database query executes through `server.db.execute_query` with a descriptive action label captured in Phase 1 query monitoring:

| Action Label | SQL Operation | Target Tables | Purpose |
|:---|:---|:---|:---|
| `feed:list` | `SELECT` | `posts`, `users`, `comments` | Retrieve paginated global feed with author JOINs & comment counts |
| `feed:user_posts` | `SELECT` | `posts`, `users`, `comments` | Retrieve paginated timeline for a single user |
| `user:exists` | `SELECT` | `users` | Verify user existence for user timeline |
| `auth:dev_user_lookup` | `SELECT` | `users` | Verify dev user existence in simulated auth |
| `post:create` | `INSERT` | `posts` | Insert new post record with `CURRENT_TIMESTAMP` |
| `post:author_info` | `SELECT` | `users` | Fetch author details for new post |
| `post:get` | `SELECT` | `posts`, `users`, `comments` | Read single post with author JOIN & comment count |
| `post:get_owner` | `SELECT` | `posts` | Check post ownership with `FOR UPDATE` before `PATCH` |
| `post:get_owner_for_delete` | `SELECT` | `posts` | Check post ownership with `FOR UPDATE` before `DELETE` |
| `post:check_reports` | `SELECT` | `reports`, `comments`, `replies` | Check if post or its comments/replies have reports before delete |
| `post:delete_likes` | `DELETE` | `post_likes` | Cascade delete post likes |
| `comment:delete_likes` | `DELETE` | `comment_likes` | Cascade delete comment likes |
| `post:delete_replies` | `DELETE` | `replies`, `comments` | Cascade delete replies of comments on post |
| `post:delete_comments` | `DELETE` | `comments` | Cascade delete comments on post |
| `post:delete` | `DELETE` | `posts` | Delete post record |
| `post:exists` | `SELECT` | `posts` | Check post existence prior to comment creation |
| `comment:list` | `SELECT` | `comments`, `users`, `replies` | List comments for a post with author JOINs & reply counts |
| `comment:create` | `INSERT` | `comments` | Insert comment on post |
| `comment:author_info`| `SELECT` | `users` | Fetch author details for new comment |
| `comment:get_owner` | `SELECT` | `comments` | Check comment ownership with `FOR UPDATE` before `PATCH` |
| `comment:get_owner_for_delete` | `SELECT` | `comments` | Check comment ownership with `FOR UPDATE` before `DELETE` |
| `comment:check_reports` | `SELECT` | `reports`, `replies` | Check if comment or replies have reports before delete |
| `comment:update` | `UPDATE` | `comments` | Update comment text & `updated_at` |
| `comment:get_updated` | `SELECT` | `comments`, `users`, `replies` | Fetch comment after update |
| `comment:delete_replies`| `DELETE` | `replies` | Cascade delete replies under comment |
| `comment:delete` | `DELETE` | `comments` | Delete comment record |
| `comment:exists` | `SELECT` | `comments` | Check comment existence prior to reply creation |
| `reply:list` | `SELECT` | `replies`, `users` | List replies for a comment with author JOINs |
| `reply:create` | `INSERT` | `replies` | Insert reply under comment |
| `reply:author_info` | `SELECT` | `users` | Fetch author details for new reply |
| `reply:get_owner` | `SELECT` | `replies` | Check reply ownership with `FOR UPDATE` before `PATCH` |
| `reply:get_owner_for_delete` | `SELECT` | `replies` | Check reply ownership with `FOR UPDATE` before `DELETE` |
| `reply:check_reports` | `SELECT` | `reports` | Check if reply has reports before delete |
| `reply:update` | `UPDATE` | `replies` | Update reply text & `updated_at` |
| `reply:delete` | `DELETE` | `replies` | Delete reply record |
