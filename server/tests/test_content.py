import unittest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager
import json
import base64
import os
from datetime import datetime, timezone

import sys
from pathlib import Path
server_dir = str(Path(__file__).resolve().parent.parent)
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

from app import app
from content import compat
import query_monitor


class TestContentEndpoints(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        query_monitor.clear_query_history()
        os.environ["ALLOW_DEV_AUTH"] = "1"

        # Mock db.get_connection so transaction() doesn't require a live PostgreSQL server in unit tests
        self.mock_db_patch = patch("db.get_connection")
        self.mock_get_conn = self.mock_db_patch.start()
        self.mock_conn = MagicMock()
        self.mock_get_conn.return_value = self.mock_conn

    def tearDown(self):
        self.mock_db_patch.stop()
        os.environ["ALLOW_DEV_AUTH"] = "1"

    # =========================================================
    # DEV AUTH TESTS
    # =========================================================

    def test_dev_auth_disabled(self):
        """When ALLOW_DEV_AUTH is 0, X-Dev-User-Id is ignored -> 401."""
        os.environ["ALLOW_DEV_AUTH"] = "0"
        res = self.client.post(
            "/api/posts",
            headers={"X-Dev-User-Id": "1"},
            json={"content": "Hello wanderers"},
        )
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "UNAUTHORIZED")

    @patch("content.compat.run_query")
    def test_dev_auth_unknown_user(self, mock_run_query):
        """When dev user does not exist in users table -> 401."""
        mock_run_query.return_value = None  # user not found in DB
        res = self.client.post(
            "/api/posts",
            headers={"X-Dev-User-Id": "999"},
            json={"content": "Hello wanderers"},
        )
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "UNAUTHORIZED")

    @patch("auth.execute_query")
    @patch("content.posts.run_query")
    def test_phase2_session_auth_for_content(self, mock_posts_query, mock_auth_query):
        """A valid Phase 2 session authenticates content without a dev header."""
        self.app.config["SECRET_KEY"] = "test-session-secret"
        mock_auth_query.return_value = {
            "rows": (
                1,
                "alex_traveler",
                "alex@example.com",
                "Alex Mercer",
                None,
                "active",
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
            ),
            "columns": [
                "user_id",
                "username",
                "email",
                "display_name",
                "bio",
                "account_status",
                "created_at",
                "updated_at",
            ],
        }
        mock_posts_query.side_effect = [
            {
                "post_id": 42,
                "user_id": 1,
                "title": None,
                "content": "Session-authenticated post.",
                "location": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": None,
            },
            {"username": "alex_traveler", "display_name": "Alex Mercer"},
        ]

        with self.client.session_transaction() as flask_session:
            flask_session["user_id"] = 1

        res = self.client.post(
            "/api/posts",
            json={"content": "Session-authenticated post."},
        )

        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["user_id"], 1)
        mock_auth_query.assert_called_once()

    # =========================================================
    # URL CONVERTER AND 404 TESTS
    # =========================================================

    def test_post_id_out_of_range(self):
        """IDs above 2147483647 return JSON 404, not 500."""
        res = self.client.get("/api/posts/99999999999")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "NOT_FOUND")

    def test_post_id_non_integer(self):
        """Non-integer IDs return JSON 404, not HTML."""
        res = self.client.get("/api/posts/abc")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "NOT_FOUND")

    # =========================================================
    # VALIDATION TESTS
    # =========================================================

    def test_post_creation_unauthorized(self):
        """Test POST /api/posts requires authentication."""
        res = self.client.post("/api/posts", json={"content": "Hello wanderers"})
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "UNAUTHORIZED")

    @patch("content.compat.run_query")
    def test_post_creation_validation_empty_content(self, mock_run_query):
        """Test POST /api/posts validates required non-empty content."""
        mock_run_query.return_value = {"user_id": 1}
        res = self.client.post(
            "/api/posts",
            headers={"X-Dev-User-Id": "1"},
            json={"content": "   ", "title": "Empty Post"},
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    @patch("content.compat.run_query")
    def test_post_creation_validation_title_length(self, mock_run_query):
        """Test POST /api/posts validates max 200 char title."""
        mock_run_query.return_value = {"user_id": 1}
        res = self.client.post(
            "/api/posts",
            headers={"X-Dev-User-Id": "1"},
            json={"content": "Valid content", "title": "A" * 201},
        )
        self.assertEqual(res.status_code, 400)

    # =========================================================
    # CURSOR PAGINATION VALIDATION
    # =========================================================

    def test_invalid_cursor_timestamp(self):
        """Cursor with unparseable timestamp returns 400."""
        payload = base64.urlsafe_b64encode(json.dumps({"c": "invalid_date", "id": 1}).encode()).decode()
        res = self.client.get(f"/api/feed?cursor={payload}")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "INVALID_PAGINATION")

    def test_out_of_range_cursor_id(self):
        """Cursor with post_id > 2147483647 or bool returns 400."""
        # Oversized int
        payload1 = base64.urlsafe_b64encode(json.dumps({"c": "2026-10-30T10:00:00Z", "id": 99999999999}).encode()).decode()
        res1 = self.client.get(f"/api/feed?cursor={payload1}")
        self.assertEqual(res1.status_code, 400)

        # Boolean (True evaluates as int in python if not checked strictly)
        payload2 = base64.urlsafe_b64encode(json.dumps({"c": "2026-10-30T10:00:00Z", "id": True}).encode()).decode()
        res2 = self.client.get(f"/api/feed?cursor={payload2}")
        self.assertEqual(res2.status_code, 400)

    # =========================================================
    # POST CRUD & OWNERSHIP
    # =========================================================

    @patch("content.compat.run_query")
    @patch("content.posts.run_query")
    def test_post_creation_success(self, mock_posts_query, mock_compat_query):
        """Test POST /api/posts successful creation."""
        mock_compat_query.return_value = {"user_id": 1}
        now = datetime.now(timezone.utc)
        mock_posts_query.side_effect = [
            {
                "post_id": 42,
                "user_id": 1,
                "title": "Mountain trail",
                "content": "Exploring the ridges today.",
                "location": "Alps",
                "created_at": now,
                "updated_at": None,
            },
            {
                "username": "alex_traveler",
                "display_name": "Alex Mercer",
            },
        ]

        res = self.client.post(
            "/api/posts",
            headers={"X-Dev-User-Id": "1"},
            json={"title": "Mountain trail", "content": "Exploring the ridges today.", "location": "Alps"},
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["post_id"], 42)
        self.assertEqual(data["title"], "Mountain trail")
        self.assertEqual(data["username"], "alex_traveler")
        self.assertEqual(data["author"]["display_name"], "Alex Mercer")

    @patch("content.compat.run_query")
    @patch("content.posts.run_query")
    def test_post_forbidden_edit(self, mock_posts_query, mock_compat_query):
        """Test PATCH /api/posts/<id> forbids editing someone else's post."""
        mock_compat_query.return_value = {"user_id": 1}
        # Post owner is user 2, but requester is user 1
        mock_posts_query.return_value = {"post_id": 10, "user_id": 2}

        res = self.client.patch(
            "/api/posts/10",
            headers={"X-Dev-User-Id": "1"},
            json={"content": "Attempting unauthorized update"},
        )
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "FORBIDDEN")

    @patch("content.posts.run_query")
    def test_post_not_found(self, mock_posts_query):
        """Test GET /api/posts/<id> returns 404 for missing post."""
        mock_posts_query.return_value = None
        res = self.client.get("/api/posts/999")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "NOT_FOUND")

    # =========================================================
    # DELETE CASCADE, REPORTS LOCK & FK ORDER TESTS
    # =========================================================

    @patch("content.compat.run_query")
    @patch("content.posts.run_query")
    def test_delete_post_with_reports_blocked(self, mock_posts_query, mock_compat_query):
        """Test delete post is aborted with 409 CONTENT_HAS_REPORTS if reported."""
        mock_compat_query.return_value = {"user_id": 1}
        mock_posts_query.side_effect = [
            {"post_id": 5, "user_id": 1},  # post:get_owner_for_delete
            {"has_reports": True},          # post:check_reports
        ]

        res = self.client.delete("/api/posts/5", headers={"X-Dev-User-Id": "1"})
        self.assertEqual(res.status_code, 409)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "CONTENT_HAS_REPORTS")

    @patch("content.compat.run_query")
    @patch("content.posts.run_query")
    def test_delete_post_fk_safe_order(self, mock_posts_query, mock_compat_query):
        """Test post delete executes statements in strict FK order."""
        mock_compat_query.return_value = {"user_id": 1}
        action_log = []

        def track_query(*args, **kwargs):
            action = kwargs.get("action")
            action_log.append(action)
            if action == "post:get_owner_for_delete":
                return {"post_id": 5, "user_id": 1}
            if action == "post:check_reports":
                return {"has_reports": False}
            return 1

        mock_posts_query.side_effect = track_query

        res = self.client.delete("/api/posts/5", headers={"X-Dev-User-Id": "1"})
        self.assertEqual(res.status_code, 204)

        expected_order = [
            "post:get_owner_for_delete",
            "post:check_reports",
            "comment:delete_likes",
            "post:delete_likes",
            "post:delete_replies",
            "post:delete_comments",
            "post:delete",
        ]
        self.assertEqual(action_log, expected_order)

    # =========================================================
    # COMMENTS & REPLIES TESTS
    # =========================================================

    @patch("content.compat.run_query")
    @patch("content.comments.run_query")
    def test_comment_non_owner_update_and_delete(self, mock_comments_query, mock_compat_query):
        """Comment PATCH/DELETE by non-owner returns 403; missing returns 404."""
        mock_compat_query.return_value = {"user_id": 1}

        # Non-owner PATCH
        mock_comments_query.return_value = {"comment_id": 2, "user_id": 2}
        res = self.client.patch("/api/comments/2", headers={"X-Dev-User-Id": "1"}, json={"content": "Edit"})
        self.assertEqual(res.status_code, 403)

        # Missing DELETE
        mock_comments_query.return_value = None
        res2 = self.client.delete("/api/comments/999", headers={"X-Dev-User-Id": "1"})
        self.assertEqual(res2.status_code, 404)

    @patch("content.compat.run_query")
    @patch("content.replies.run_query")
    def test_reply_non_owner_update_and_delete(self, mock_replies_query, mock_compat_query):
        """Reply PATCH/DELETE by non-owner returns 403; missing returns 404."""
        mock_compat_query.return_value = {"user_id": 1}

        # Non-owner PATCH
        mock_replies_query.return_value = {"reply_id": 3, "user_id": 2}
        res = self.client.patch("/api/replies/3", headers={"X-Dev-User-Id": "1"}, json={"content": "Edit"})
        self.assertEqual(res.status_code, 403)

        # Missing DELETE
        mock_replies_query.return_value = None
        res2 = self.client.delete("/api/replies/999", headers={"X-Dev-User-Id": "1"})
        self.assertEqual(res2.status_code, 404)

    # =========================================================
    # ERROR HANDLING TESTS
    # =========================================================

    @patch("content.posts.run_query")
    def test_unexpected_exception_returns_500_internal_error(self, mock_posts_query):
        """Unexpected non-DB exception returns standard 500 INTERNAL_ERROR."""
        mock_posts_query.side_effect = RuntimeError("Something completely unexpected exploded!")
        res = self.client.get("/api/posts/1")
        self.assertEqual(res.status_code, 500)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "INTERNAL_ERROR")
        self.assertEqual(data["error"]["message"], "Unexpected server error.")

    # =========================================================
    # QUERY MONITOR INTEGRATION
    # =========================================================

    def test_query_monitor_receives_entries_on_content_request(self):
        """Verify that execute_query records query metadata into Phase 1 query_monitor."""
        mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = mock_cursor

        mock_cursor.rowcount = 1
        mock_col_id = MagicMock(); mock_col_id.name = "post_id"
        mock_col_uid = MagicMock(); mock_col_uid.name = "user_id"
        mock_col_title = MagicMock(); mock_col_title.name = "title"
        mock_col_content = MagicMock(); mock_col_content.name = "content"
        mock_col_loc = MagicMock(); mock_col_loc.name = "location"
        mock_col_cat = MagicMock(); mock_col_cat.name = "created_at"
        mock_col_uat = MagicMock(); mock_col_uat.name = "updated_at"
        mock_col_uname = MagicMock(); mock_col_uname.name = "username"
        mock_col_dname = MagicMock(); mock_col_dname.name = "display_name"
        mock_col_ccnt = MagicMock(); mock_col_ccnt.name = "comment_count"

        mock_cursor.description = [
            mock_col_id, mock_col_uid, mock_col_title, mock_col_content,
            mock_col_loc, mock_col_cat, mock_col_uat, mock_col_uname,
            mock_col_dname, mock_col_ccnt,
        ]
        now = datetime.now(timezone.utc)
        mock_cursor.fetchall.return_value = [
            (1, 1, "Title", "Content", "Location", now, None, "alex", "Alex", 0)
        ]

        res = self.client.get("/api/feed")
        self.assertEqual(res.status_code, 200)

        history = query_monitor.get_query_history()
        self.assertGreaterEqual(len(history), 1)
        last_entry = history[-1]
        self.assertEqual(last_entry["action"], "feed:list")
        self.assertEqual(last_entry["operation"], "SELECT")
        self.assertEqual(last_entry["status"], "success")
        self.assertIsNotNone(last_entry["request_id"])


if __name__ == "__main__":
    unittest.main()
