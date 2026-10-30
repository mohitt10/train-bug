import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from werkzeug.security import generate_password_hash

server_dir = str(Path(__file__).resolve().parent.parent)
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

from app import app
from api_utils import as_dict, as_dicts


class TestPhase4Endpoints(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["SECRET_KEY"] = "phase4-test-secret"
        self.client = self.app.test_client()
        os.environ["ALLOW_DEV_AUTH"] = "0"
        self.connection_patch = patch("db.get_connection")
        self.mock_connection_factory = self.connection_patch.start()
        self.mock_connection_factory.return_value = MagicMock()

    def tearDown(self):
        self.connection_patch.stop()

    def sign_in_as(self, user_id=1):
        with self.client.session_transaction() as flask_session:
            flask_session["user_id"] = user_id

    @staticmethod
    def user_row(user_id=1, status="active"):
        return (
            user_id,
            "alex_traveler",
            "alex@example.com",
            "Alex Mercer",
            None,
            status,
            datetime.now(timezone.utc),
            datetime.now(timezone.utc),
        )

    @patch("auth.execute_query")
    @patch("content.likes.run_query")
    def test_post_like_is_conflict_safe_and_returns_summary(self, mock_query, mock_auth):
        self.sign_in_as()
        mock_auth.return_value = self.user_row()
        mock_query.side_effect = [
            {"post_id": 7},
            0,
            {"like_count": 3, "liked_by_me": True},
        ]

        response = self.client.post("/api/posts/7/like")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"like_count": 3, "liked_by_me": True})
        insert_sql = mock_query.call_args_list[1].args[0]
        self.assertIn("ON CONFLICT (user_id, post_id) DO NOTHING", insert_sql)

    @patch("auth.execute_query")
    @patch("content.reports.run_query")
    def test_report_target_is_selected_by_server_and_status_starts_pending(self, mock_query, mock_auth):
        self.sign_in_as(3)
        mock_auth.return_value = self.user_row(3)
        mock_query.side_effect = [
            {"comment_id": 18},
            {
                "report_id": 31,
                "reporter_id": 3,
                "reason": "Spam",
                "status": "pending",
            },
        ]

        response = self.client.post(
            "/api/reports",
            json={
                "target_type": "comment",
                "target_id": 18,
                "reason": "Spam",
                "reporter_id": 999,
                "reviewed_by": 999,
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["status"], "pending")
        insert_sql, insert_params = mock_query.call_args_list[1].args[:2]
        self.assertIn("(reporter_id, reason, status, created_at, comment_id)", insert_sql)
        insert_columns = insert_sql.split("VALUES", maxsplit=1)[0]
        self.assertNotIn("reviewed_by", insert_columns)
        self.assertEqual(insert_params, (3, "Spam", 18))

    @patch("auth.execute_query")
    @patch("content.reports.execute_query")
    def test_regular_user_cannot_access_moderation(self, mock_moderator_query, mock_auth):
        self.sign_in_as()
        mock_auth.return_value = self.user_row()
        mock_moderator_query.return_value = None

        response = self.client.get("/api/moderation/reports")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"]["code"], "MODERATOR_REQUIRED")

    @patch("auth.execute_query")
    @patch("content.reports.execute_query")
    @patch("content.reports.run_query")
    def test_review_attribution_comes_from_authenticated_moderator(self, mock_query, mock_moderator, mock_auth):
        self.sign_in_as(9)
        mock_auth.return_value = self.user_row(9)
        mock_moderator.return_value = (9,)
        now = datetime.now(timezone.utc)
        mock_query.side_effect = [
            {"report_id": 31, "status": "pending"},
            1,
            {
                "report_id": 31,
                "reporter_id": 3,
                "reporter_username": "reporter",
                "reason": "Spam",
                "status": "resolved",
                "created_at": now,
                "post_id": 18,
                "comment_id": None,
                "reply_id": None,
                "reviewed_by": 9,
                "reviewer_username": "mod",
                "target_type": "post",
                "target_id": 18,
                "target_content": "A post",
            },
        ]

        response = self.client.patch("/api/moderation/reports/31", json={"status": "resolved"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["reviewed_by"], 9)
        update_params = mock_query.call_args_list[1].args[1]
        self.assertEqual(update_params, ("resolved", 9, 31))

    @patch("auth.execute_query")
    @patch("content.reports.run_query")
    def test_report_ignores_client_controlled_target_columns(self, mock_query, mock_auth):
        self.sign_in_as(3)
        mock_auth.return_value = self.user_row(3)
        mock_query.side_effect = [
            {"comment_id": 18},
            {"report_id": 31, "reporter_id": 3, "reason": "Bad", "status": "pending"},
        ]
        response = self.client.post(
            "/api/reports",
            json={
                "target_type": "comment",
                "target_id": 18,
                "reason": "Bad",
                "post_id": 1,
                "reply_id": 2,
                "reviewed_by": 99,
                "reporter_id": 99,
            },
        )
        self.assertEqual(response.status_code, 201)
        insert_sql = mock_query.call_args_list[1].args[0]
        self.assertIn("created_at, comment_id)", insert_sql)
        self.assertNotIn("post_id)", insert_sql)
        self.assertNotIn("reply_id)", insert_sql)

    def test_phase1_execute_query_result_envelope_maps_to_phase2_rows(self):
        row = {
            "rows": (7, "wanderer"),
            "columns": ["user_id", "username"],
            "affected_rows": 1,
        }
        rows = {
            "rows": [(7, "wanderer"), (8, "traveler")],
            "columns": ["user_id", "username"],
            "affected_rows": 2,
        }

        self.assertEqual(as_dict(row, []), {"user_id": 7, "username": "wanderer"})
        self.assertEqual(
            as_dicts(rows, []),
            [
                {"user_id": 7, "username": "wanderer"},
                {"user_id": 8, "username": "traveler"},
            ],
        )
        self.assertIsNone(as_dict({"rows": None, "columns": ["user_id"]}, []))

    @patch("auth.execute_query")
    @patch("users.execute_query")
    def test_phase2_profile_route_reads_shared_db_result_envelope(self, mock_users_query, mock_auth):
        self.sign_in_as(1)
        now = datetime.now(timezone.utc)
        mock_auth.return_value = {
            "rows": self.user_row(),
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
        mock_users_query.return_value = {
            "rows": (2, "sarah_journeys", "Sarah Jenkins", "Traveler", "active", now, 4, 2, True),
            "columns": [
                "user_id",
                "username",
                "display_name",
                "bio",
                "account_status",
                "created_at",
                "follower_count",
                "following_count",
                "is_following",
            ],
        }

        response = self.client.get("/api/users/2")

        self.assertEqual(response.status_code, 200)
        profile = response.get_json()["data"]
        self.assertEqual(profile["user_id"], 2)
        self.assertEqual(profile["follower_count"], 4)
        self.assertTrue(profile["is_following"])

    @patch("auth.execute_query")
    def test_phase2_register_and_login_accept_shared_db_result_envelopes(self, mock_auth):
        now = datetime.now(timezone.utc)
        columns = [
            "user_id",
            "username",
            "email",
            "display_name",
            "bio",
            "account_status",
            "created_at",
            "updated_at",
        ]
        mock_auth.side_effect = [
            {"rows": [], "columns": ["username", "email"], "affected_rows": 0},
            {
                "rows": (11, "new_traveler", "new@example.com", "New Traveler", None, "active", now, now),
                "columns": columns,
                "affected_rows": 1,
            },
            {
                "rows": (
                    11,
                    "new_traveler",
                    "new@example.com",
                    "New Traveler",
                    None,
                    "active",
                    now,
                    now,
                    generate_password_hash("password123"),
                ),
                "columns": columns + ["password_hash"],
                "affected_rows": 1,
            },
        ]

        registration = self.client.post(
            "/api/auth/register",
            json={
                "username": "new_traveler",
                "email": "new@example.com",
                "password": "password123",
                "display_name": "New Traveler",
            },
        )
        login = self.client.post(
            "/api/auth/login",
            json={"identifier": "new_traveler", "password": "password123"},
        )

        self.assertEqual(registration.status_code, 201)
        self.assertEqual(registration.get_json()["data"]["user"]["user_id"], 11)
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.get_json()["data"]["user"]["username"], "new_traveler")
        self.assertEqual(mock_auth.call_args_list[1].kwargs["fetch"], "one")


if __name__ == "__main__":
    unittest.main()
