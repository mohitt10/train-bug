# WanderLog Phase 3 Real Database Smoke Test Guide

This document provides a step-by-step verification script to validate Phase 3 functionality against a live PostgreSQL instance.

---

## 1. Environment Preparation

1. **Initialize the database and dev seed data**:
   ```bash
   createdb wanderlog_db
   psql -d wanderlog_db -f server/schema.sql
   psql -d wanderlog_db -f server/dev/seed_dev_data.sql
   ```

2. **Configure `server/.env`**:
   ```env
   DATABASE_URL=postgresql://wanderlog_user:replace-with-password@localhost:5432/wanderlog_db
   FLASK_SECRET_KEY=dev_secret_key
   ALLOW_DEV_AUTH=1
   ```

3. **Start the Flask server**:
   ```bash
   cd server
   python app.py
   ```
   (Server runs on `http://127.0.0.1:5000`)

---

## 2. End-to-End Smoke Test Flow

### Step A: Verify System Health
```bash
curl -i http://127.0.0.1:5000/api/health/db
```
* **Expected Result**: HTTP `200 OK`, `{"database": "connected", "status": "ok"}`

---

### Step B: Create a Post as User 1 (Alex Mercer)
```bash
curl -i -X POST http://127.0.0.1:5000/api/posts \
  -H "Content-Type: application/json" \
  -H "X-Dev-User-Id: 1" \
  -d '{"title": "Kokan Coastal Trail", "content": "Red laterite cliffs meeting the Arabian Sea at sunset.", "location": "Guhagar"}'
```
* **Expected Result**: HTTP `201 Created`
* **Response**: Contains `post_id` (e.g. `10`), `username: "alex_traveler"`, `comment_count: 0`.

---

### Step C: Update the Post as User 1 (Author)
```bash
curl -i -X PATCH http://127.0.0.1:5000/api/posts/10 \
  -H "Content-Type: application/json" \
  -H "X-Dev-User-Id: 1" \
  -d '{"title": "Kokan Coastal Trail (Updated)", "content": "Red laterite cliffs meeting the Arabian Sea at golden hour."}'
```
* **Expected Result**: HTTP `200 OK`, `updated_at` is now non-null.

---

### Step D: Attempt Unauthorized Edit as User 2 (Sarah Jenkins)
```bash
curl -i -X PATCH http://127.0.0.1:5000/api/posts/10 \
  -H "Content-Type: application/json" \
  -H "X-Dev-User-Id: 2" \
  -d '{"content": "Tampering with Alex post"}'
```
* **Expected Result**: HTTP `403 Forbidden`
* **Response**:
```json
{
  "status": "error",
  "error": {
    "code": "FORBIDDEN",
    "message": "You do not have permission to edit this post."
  }
}
```

---

### Step E: Enforce 2,000-Character Comment Limit
Attempt to comment with 2,001 characters:
```bash
python -c "
import urllib.request, json
body = json.dumps({'content': 'X' * 2001}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:5000/api/posts/10/comments', data=body, headers={'Content-Type': 'application/json', 'X-Dev-User-Id': '2'}, method='POST')
try:
    urllib.request.urlopen(req)
except urllib.error.HTTPError as e:
    print('Status:', e.code)
    print(e.read().decode('utf-8'))
"
```
* **Expected Result**: HTTP `400 Bad Request`
* **Response**: `{"status": "error", "error": {"code": "VALIDATION_ERROR", "message": "'content' exceeds maximum limit of 2000 characters."}}`

---

### Step F: Create Valid Comment & Reply
1. **Comment on Post 10 by User 2**:
   ```bash
   curl -i -X POST http://127.0.0.1:5000/api/posts/10/comments \
     -H "Content-Type: application/json" \
     -H "X-Dev-User-Id: 2" \
     -d '{"content": "Is the trail marked well near the lighthouse?"}'
   ```
   * **Expected Result**: HTTP `201 Created`, returns `comment_id` (e.g. `10`).

2. **Reply to Comment 10 by User 1**:
   ```bash
   curl -i -X POST http://127.0.0.1:5000/api/comments/10/replies \
     -H "Content-Type: application/json" \
     -H "X-Dev-User-Id: 1" \
     -d '{"content": "Yes, blue arrows painted on the rocks point toward the headland."}'
   ```
   * **Expected Result**: HTTP `201 Created`, returns `reply_id` (e.g. `10`).

---

### Step G: Cursor Pagination Flow
1. **Fetch Page 1 (limit=2)**:
   ```bash
   curl -s "http://127.0.0.1:5000/api/feed?limit=2"
   ```
   Returns 2 items and a `next_cursor` token.

2. **Fetch Page 2 using `next_cursor`**:
   ```bash
   curl -s "http://127.0.0.1:5000/api/feed?limit=2&cursor=<NEXT_CURSOR_VALUE>"
   ```
   Continue until `next_cursor` returns `null`.

---

### Step H: Cascading Deletion of Content with Comments & Replies
Delete Post 10 as User 1:
```bash
curl -i -X DELETE http://127.0.0.1:5000/api/posts/10 \
  -H "X-Dev-User-Id: 1"
```
* **Expected Result**: HTTP `204 No Content`
* **Verify Deletion via GET**:
  ```bash
  curl -i http://127.0.0.1:5000/api/posts/10
  ```
  * Returns HTTP `404 Not Found`.
  * Also verify in PostgreSQL:
    ```sql
    SELECT * FROM posts WHERE post_id = 10;
    SELECT * FROM comments WHERE post_id = 10;
    SELECT * FROM replies WHERE comment_id = 10;
    ```
    All 3 queries return 0 rows.

---

### Step I: Verify Query Capture in Query History
Run from the `server` directory:
```bash
python -c "
import sys; sys.path.insert(0, '.'); import query_monitor
history = query_monitor.get_query_history()
print(f'Total captured queries: {len(history)}')
for q in history[-10:]:
    print(f'[{q[\"status\"]}] {q[\"action\"]:25s} {q[\"operation\"]:6s} ({q[\"duration_ms\"]:.1f}ms)')
"
```
* **Expected Result**: All action labels (`feed:list`, `post:create`, `comment:create`, `reply:create`, `post:delete_replies`, `post:delete_comments`, `post:delete`) appear with status `success`, duration in milliseconds, and active request IDs.
