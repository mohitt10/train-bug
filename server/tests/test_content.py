import unittest
from unittest.mock import MagicMock, patch
import json
import base64
from datetime import datetime, timezone

import sys
from pathlib import Path
server_dir = str(Path(__file__).resolve().parent.parent)
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

from app import app
from content import compat


class TestContentEndpoints(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_post_creation_unauthorized(self):
        """Test POST /api/posts requires authentication."""
        res = self.client.post("/api/posts", json={"content": "Hello wanderers"})
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "UNAUTHORIZED")

    def test_post_creation_validation_empty_content(self):
        """Test POST /api/posts validates required non-empty content."""
        res = self.client.post(
            "/api/posts",
            headers={"X-Dev-User-Id": "1"},
            json={"content": "   ", "title": "Empty Post"},
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    def test_post_creation_validation_title_length(self):
        """Test POST /api/posts validates max 200 char title."""
        res = self.client.post(
            "/api/posts",
            headers={"X-Dev-User-Id": "1"},
            json={"content": "Valid content", "title": "A" * 201},
        )
        self.assertEqual(res.status_code, 400)

    @patch("content.posts.run_query")
    def test_post_creation_success(self, mock_run_query):
        """Test POST /api/posts successful creation."""
        now = datetime.now(timezone.utc)
        mock_run_query.side_effect = [
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

    @patch("content.posts.run_query")
    def test_post_forbidden_edit(self, mock_run_query):
        """Test PATCH /api/posts/<id> forbids editing someone else's post."""
        # Post owner is user 2, but requester is user 1
        mock_run_query.return_value = {"post_id": 10, "user_id": 2}

        res = self.client.patch(
            "/api/posts/10",
            headers={"X-Dev-User-Id": "1"},
            json={"content": "Attempting unauthorized update"},
        )
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "FORBIDDEN")

    @patch("content.posts.run_query")
    def test_post_not_found(self, mock_run_query):
        """Test GET /api/posts/<id> returns 404 for missing post."""
        mock_run_query.return_value = None
        res = self.client.get("/api/posts/999")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "NOT_FOUND")

    @patch("content.posts.run_query")
    @patch("content.posts.delete_post_cascade")
    def test_post_delete_owner(self, mock_delete_cascade, mock_run_query):
        """Test DELETE /api/posts/<id> by owner returns 204."""
        mock_run_query.return_value = {"post_id": 5, "user_id": 1}

        res = self.client.delete(
            "/api/posts/5",
            headers={"X-Dev-User-Id": "1"},
        )
        self.assertEqual(res.status_code, 204)
        mock_delete_cascade.assert_called_once_with(5)

    @patch("content.comments.run_query")
    def test_comment_length_limit(self, mock_run_query):
        """Test POST /api/posts/<id>/comments enforces 2,000 character limit."""
        res = self.client.post(
            "/api/posts/1/comments",
            headers={"X-Dev-User-Id": "1"},
            json={"content": "X" * 2001},
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("exceeds maximum limit", data["error"]["message"])

    @patch("content.replies.run_query")
    def test_reply_length_limit(self, mock_run_query):
        """Test POST /api/comments/<id>/replies enforces 2,000 character limit."""
        res = self.client.post(
            "/api/comments/1/replies",
            headers={"X-Dev-User-Id": "1"},
            json={"content": "Y" * 2001},
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("exceeds maximum limit", data["error"]["message"])

    @patch("content.feed.run_query")
    def test_feed_pagination_cursor(self, mock_run_query):
        """Test GET /api/feed returns items and next_cursor."""
        now = datetime.now(timezone.utc)
        items = [
            {
                "post_id": i,
                "user_id": 1,
                "title": f"Post {i}",
                "content": f"Content {i}",
                "location": None,
                "created_at": now,
                "updated_at": None,
                "username": "alex",
                "display_name": "Alex",
                "comment_count": 0,
            }
            for i in range(25, 4, -1) # 21 items (for limit=20)
        ]
        mock_run_query.return_value = items

        res = self.client.get("/api/feed?limit=20")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data["items"]), 20)
        self.assertIsNotNone(data["next_cursor"])

        # Decode cursor to verify format
        decoded = json.loads(base64.urlsafe_b64decode(data["next_cursor"].encode()).decode())
        self.assertEqual(decoded["id"], 6)  # The 20th item has post_id 6


if __name__ == "__main__":
    unittest.main()
