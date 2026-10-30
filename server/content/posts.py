import psycopg
from flask import Blueprint, current_app, jsonify, request

from .compat import (
    current_user_id,
    login_required,
    map_db_error,
    map_db_error_for_delete,
    run_query,
    transaction,
)
from .responses import error_response
from .serializers import serialize_post
from .validators import validate_post_create, validate_post_update

posts_bp = Blueprint("posts", __name__)


def delete_post_cascade(post_id: int, user_id: int):
    """
    DELETE POLICY: default chosen by Phase 3; team may change.
    Enforces atomic cascade respecting foreign key hierarchy:
    1. Select post FOR UPDATE to prevent concurrency races.
    2. Check if the post, its comments, or replies have reports. Abort if reported.
    3. Delete comment_likes for comments on this post.
    4. Delete post_likes for this post.
    5. Delete replies on all comments under this post.
    6. Delete comments under this post.
    7. Delete post record.
    Returns: None on success, or a response tuple (error_response, status_code).
    """
    with transaction():
        owner_row = run_query(
            "SELECT post_id, user_id FROM posts WHERE post_id = %s FOR UPDATE;",
            (post_id,),
            action="post:get_owner_for_delete",
            fetch="one",
        )

        if not owner_row:
            return error_response("NOT_FOUND", "Post not found.", 404)

        if owner_row["user_id"] != user_id:
            return error_response("FORBIDDEN", "You do not have permission to delete this post.", 403)

        # Abort if any report references this post, its comments, or their replies
        # DELETE POLICY: default chosen by Phase 3; team may change
        report_check = run_query(
            """
            SELECT EXISTS (
                SELECT 1 FROM reports
                WHERE post_id = %s
                   OR comment_id IN (SELECT comment_id FROM comments WHERE post_id = %s)
                   OR reply_id IN (
                       SELECT reply_id FROM replies
                       WHERE comment_id IN (SELECT comment_id FROM comments WHERE post_id = %s)
                   )
            ) AS has_reports;
            """,
            (post_id, post_id, post_id),
            action="post:check_reports",
            fetch="one",
        )

        if report_check and report_check.get("has_reports"):
            return error_response(
                "CONTENT_HAS_REPORTS",
                "This content has been reported and cannot be deleted until a moderator reviews it.",
                409,
            )

        # 3. Delete comment_likes for comments under this post
        run_query(
            "DELETE FROM comment_likes WHERE comment_id IN (SELECT comment_id FROM comments WHERE post_id = %s);",
            (post_id,),
            action="comment:delete_likes",
            fetch="none",
        )

        # 4. Delete post_likes for this post
        run_query(
            "DELETE FROM post_likes WHERE post_id = %s;",
            (post_id,),
            action="post:delete_likes",
            fetch="none",
        )

        # 5. Delete replies under comments of this post
        run_query(
            "DELETE FROM replies WHERE comment_id IN (SELECT comment_id FROM comments WHERE post_id = %s);",
            (post_id,),
            action="post:delete_replies",
            fetch="none",
        )

        # 6. Delete comments under this post
        run_query(
            "DELETE FROM comments WHERE post_id = %s;",
            (post_id,),
            action="post:delete_comments",
            fetch="none",
        )

        # 7. Delete the post itself
        run_query(
            "DELETE FROM posts WHERE post_id = %s;",
            (post_id,),
            action="post:delete",
            fetch="none",
        )

        return None


@posts_bp.post("/posts")
@login_required
def create_post():
    """Create a new post authored by the authenticated user."""
    data = request.get_json(silent=True)
    cleaned, err = validate_post_create(data)
    if err:
        return error_response("VALIDATION_ERROR", err, 400)

    author_id = current_user_id()

    try:
        inserted = run_query(
            """
            INSERT INTO posts (user_id, title, content, location, created_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING post_id, user_id, title, content, location, created_at, updated_at;
            """,
            (author_id, cleaned["title"], cleaned["content"], cleaned["location"]),
            action="post:create",
            fetch="one",
        )

        author = run_query(
            "SELECT username, display_name FROM users WHERE user_id = %s;",
            (author_id,),
            action="post:author_info",
            fetch="one",
        )

        row = dict(inserted)
        row["username"] = author["username"] if author else None
        row["display_name"] = author["display_name"] if author else None
        row["comment_count"] = 0

        return jsonify(serialize_post(row)), 201

    except psycopg.Error as exc:
        current_app.logger.warning("Database error in create_post (SQLSTATE %s)", getattr(exc, "sqlstate", None))
        status, msg = map_db_error(exc)
        return error_response("DATABASE_ERROR", msg, status)
    except Exception as exc:
        current_app.logger.exception("Unexpected error in create_post: %s", exc)
        return error_response("INTERNAL_ERROR", "Unexpected server error.", 500)


@posts_bp.get("/posts/<int:post_id>")
def get_post(post_id: int):
    """Retrieve an individual post with author details and comment count."""
    try:
        row = run_query(
            """
            SELECT p.post_id, p.user_id, p.title, p.content, p.location, p.created_at, p.updated_at,
                   u.username, u.display_name,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.post_id) AS comment_count
            FROM posts p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.post_id = %s;
            """,
            (post_id,),
            action="post:get",
            fetch="one",
        )

        if not row:
            return error_response("NOT_FOUND", "Post not found.", 404)

        return jsonify(serialize_post(row)), 200

    except psycopg.Error as exc:
        current_app.logger.warning("Database error in get_post (SQLSTATE %s)", getattr(exc, "sqlstate", None))
        status, msg = map_db_error(exc)
        return error_response("DATABASE_ERROR", msg, status)
    except Exception as exc:
        current_app.logger.exception("Unexpected error in get_post: %s", exc)
        return error_response("INTERNAL_ERROR", "Unexpected server error.", 500)


@posts_bp.patch("/posts/<int:post_id>")
@login_required
def update_post(post_id: int):
    """Update title, content, or location of an owned post."""
    data = request.get_json(silent=True)
    fields, err = validate_post_update(data)
    if err:
        return error_response("VALIDATION_ERROR", err, 400)

    user_id = current_user_id()

    try:
        with transaction():
            owner_row = run_query(
                "SELECT post_id, user_id FROM posts WHERE post_id = %s FOR UPDATE;",
                (post_id,),
                action="post:get_owner",
                fetch="one",
            )

            if not owner_row:
                return error_response("NOT_FOUND", "Post not found.", 404)

            if owner_row["user_id"] != user_id:
                return error_response("FORBIDDEN", "You do not have permission to edit this post.", 403)

            set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
            params = []

            if "title" in fields:
                set_clauses.append("title = %s")
                params.append(fields["title"])
            if "content" in fields:
                set_clauses.append("content = %s")
                params.append(fields["content"])
            if "location" in fields:
                set_clauses.append("location = %s")
                params.append(fields["location"])

            params.append(post_id)

            sql = f"UPDATE posts SET {', '.join(set_clauses)} WHERE post_id = %s;"
            run_query(sql, tuple(params), action="post:update", fetch="none")

            updated_row = run_query(
                """
                SELECT p.post_id, p.user_id, p.title, p.content, p.location, p.created_at, p.updated_at,
                       u.username, u.display_name,
                       (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.post_id) AS comment_count
                FROM posts p
                JOIN users u ON p.user_id = u.user_id
                WHERE p.post_id = %s;
                """,
                (post_id,),
                action="post:get_updated",
                fetch="one",
            )

            return jsonify(serialize_post(updated_row)), 200

    except psycopg.Error as exc:
        current_app.logger.warning("Database error in update_post (SQLSTATE %s)", getattr(exc, "sqlstate", None))
        status, msg = map_db_error(exc)
        return error_response("DATABASE_ERROR", msg, status)
    except Exception as exc:
        current_app.logger.exception("Unexpected error in update_post: %s", exc)
        return error_response("INTERNAL_ERROR", "Unexpected server error.", 500)


@posts_bp.delete("/posts/<int:post_id>")
@login_required
def delete_post(post_id: int):
    """Delete an owned post, cascading to likes, comments, and replies."""
    user_id = current_user_id()

    try:
        err = delete_post_cascade(post_id, user_id)
        if err is not None:
            return err

        return "", 204

    except psycopg.Error as exc:
        current_app.logger.warning("Database error in delete_post (SQLSTATE %s)", getattr(exc, "sqlstate", None))
        status, msg = map_db_error_for_delete(exc)
        return error_response("DATABASE_ERROR", msg, status)
    except Exception as exc:
        current_app.logger.exception("Unexpected error in delete_post: %s", exc)
        return error_response("INTERNAL_ERROR", "Unexpected server error.", 500)
