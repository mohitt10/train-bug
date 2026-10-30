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
from .serializers import serialize_comment
from .validators import validate_text_content

comments_bp = Blueprint("comments", __name__)


def delete_comment_cascade(comment_id: int, user_id: int):
    """
    DELETE POLICY: default chosen by Phase 3; team may change.
    Enforces atomic cascade respecting foreign key hierarchy:
    1. Select comment FOR UPDATE to prevent concurrency races.
    2. Check if the comment or its replies have reports. Abort if reported.
    3. Delete comment_likes for this comment.
    4. Delete replies under this comment.
    5. Delete comment record.
    Returns: None on success, or a response tuple (error_response, status_code).
    """
    with transaction():
        owner_row = run_query(
            "SELECT comment_id, user_id FROM comments WHERE comment_id = %s FOR UPDATE;",
            (comment_id,),
            action="comment:get_owner_for_delete",
            fetch="one",
        )

        if not owner_row:
            return error_response("NOT_FOUND", "Comment not found.", 404)

        if owner_row["user_id"] != user_id:
            return error_response("FORBIDDEN", "You do not have permission to delete this comment.", 403)

        # Abort if any report references this comment or its replies
        # DELETE POLICY: default chosen by Phase 3; team may change
        report_check = run_query(
            """
            SELECT EXISTS (
                SELECT 1 FROM reports
                WHERE comment_id = %s
                   OR reply_id IN (SELECT reply_id FROM replies WHERE comment_id = %s)
            ) AS has_reports;
            """,
            (comment_id, comment_id),
            action="comment:check_reports",
            fetch="one",
        )

        if report_check and report_check.get("has_reports"):
            return error_response(
                "CONTENT_HAS_REPORTS",
                "This content has a retained report and cannot be deleted.",
                409,
            )

        # 3. Delete likes on this comment
        run_query(
            "DELETE FROM comment_likes WHERE comment_id = %s;",
            (comment_id,),
            action="comment:delete_likes",
            fetch="none",
        )

        # 4. Delete replies under this comment
        run_query(
            "DELETE FROM replies WHERE comment_id = %s;",
            (comment_id,),
            action="comment:delete_replies",
            fetch="none",
        )

        # 5. Delete the comment itself
        run_query(
            "DELETE FROM comments WHERE comment_id = %s;",
            (comment_id,),
            action="comment:delete",
            fetch="none",
        )

        return None


@comments_bp.get("/posts/<int:post_id>/comments")
def get_post_comments(post_id: int):
    """Retrieve comments for a post, ordered chronologically with author info and reply counts."""
    try:
        post_row = run_query(
            "SELECT post_id FROM posts WHERE post_id = %s;",
            (post_id,),
            action="post:exists",
            fetch="one",
        )
        if not post_row:
            return error_response("NOT_FOUND", "Post not found.", 404)

        rows = run_query(
            """
            SELECT c.comment_id, c.user_id, c.post_id, c.content, c.created_at, c.updated_at,
                   u.username, u.display_name,
                   (SELECT COUNT(*) FROM replies r WHERE r.comment_id = c.comment_id) AS reply_count,
                   (SELECT COUNT(*) FROM comment_likes cl WHERE cl.comment_id = c.comment_id) AS like_count,
                   EXISTS (
                       SELECT 1 FROM comment_likes cl
                       WHERE cl.comment_id = c.comment_id AND cl.user_id = %s
                   ) AS liked_by_me
            FROM comments c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.post_id = %s
            ORDER BY c.created_at ASC, c.comment_id ASC;
            """,
            (current_user_id(), post_id),
            action="comment:list",
            fetch="all",
        )

        items = [serialize_comment(r) for r in rows]
        return jsonify({"items": items}), 200

    except psycopg.Error as exc:
        current_app.logger.warning("Database error in get_post_comments (SQLSTATE %s)", getattr(exc, "sqlstate", None))
        status, msg = map_db_error(exc)
        return error_response("DATABASE_ERROR", msg, status)
    except Exception as exc:
        current_app.logger.exception("Unexpected error in get_post_comments: %s", exc)
        return error_response("INTERNAL_ERROR", "Unexpected server error.", 500)


@comments_bp.post("/posts/<int:post_id>/comments")
@login_required
def create_comment(post_id: int):
    """Create a new comment on a post (max 2,000 characters)."""
    data = request.get_json(silent=True)
    content, err = validate_text_content(data, field_name="content", max_length=2000)
    if err:
        return error_response("VALIDATION_ERROR", err, 400)

    user_id = current_user_id()

    try:
        post_row = run_query(
            "SELECT post_id FROM posts WHERE post_id = %s;",
            (post_id,),
            action="post:exists",
            fetch="one",
        )
        if not post_row:
            return error_response("NOT_FOUND", "Post not found.", 404)

        inserted = run_query(
            """
            INSERT INTO comments (user_id, post_id, content, created_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING comment_id, user_id, post_id, content, created_at, updated_at;
            """,
            (user_id, post_id, content),
            action="comment:create",
            fetch="one",
        )

        author = run_query(
            "SELECT username, display_name FROM users WHERE user_id = %s;",
            (user_id,),
            action="comment:author_info",
            fetch="one",
        )

        row = dict(inserted)
        row["username"] = author["username"] if author else None
        row["display_name"] = author["display_name"] if author else None
        row["reply_count"] = 0

        return jsonify(serialize_comment(row)), 201

    except psycopg.Error as exc:
        # FK violation on INSERT indicates post was deleted between check and insert
        if getattr(exc, "sqlstate", None) == "23503":
            return error_response("NOT_FOUND", "Post not found.", 404)
        current_app.logger.warning("Database error in create_comment (SQLSTATE %s)", getattr(exc, "sqlstate", None))
        status, msg = map_db_error(exc)
        return error_response("DATABASE_ERROR", msg, status)
    except Exception as exc:
        current_app.logger.exception("Unexpected error in create_comment: %s", exc)
        return error_response("INTERNAL_ERROR", "Unexpected server error.", 500)


@comments_bp.patch("/comments/<int:comment_id>")
@login_required
def update_comment(comment_id: int):
    """Update text of an owned comment (max 2,000 characters)."""
    data = request.get_json(silent=True)
    content, err = validate_text_content(data, field_name="content", max_length=2000)
    if err:
        return error_response("VALIDATION_ERROR", err, 400)

    user_id = current_user_id()

    try:
        with transaction():
            owner_row = run_query(
                "SELECT comment_id, user_id FROM comments WHERE comment_id = %s FOR UPDATE;",
                (comment_id,),
                action="comment:get_owner",
                fetch="one",
            )

            if not owner_row:
                return error_response("NOT_FOUND", "Comment not found.", 404)

            if owner_row["user_id"] != user_id:
                return error_response("FORBIDDEN", "You do not have permission to edit this comment.", 403)

            run_query(
                """
                UPDATE comments
                SET content = %s, updated_at = CURRENT_TIMESTAMP
                WHERE comment_id = %s;
                """,
                (content, comment_id),
                action="comment:update",
                fetch="none",
            )

            updated_row = run_query(
                """
                SELECT c.comment_id, c.user_id, c.post_id, c.content, c.created_at, c.updated_at,
                       u.username, u.display_name,
                       (SELECT COUNT(*) FROM replies r WHERE r.comment_id = c.comment_id) AS reply_count,
                       (SELECT COUNT(*) FROM comment_likes cl WHERE cl.comment_id = c.comment_id) AS like_count,
                       EXISTS (
                           SELECT 1 FROM comment_likes cl
                           WHERE cl.comment_id = c.comment_id AND cl.user_id = %s
                       ) AS liked_by_me
                FROM comments c
                JOIN users u ON c.user_id = u.user_id
                WHERE c.comment_id = %s;
                """,
                (user_id, comment_id),
                action="comment:get_updated",
                fetch="one",
            )

            return jsonify(serialize_comment(updated_row)), 200

    except psycopg.Error as exc:
        current_app.logger.warning("Database error in update_comment (SQLSTATE %s)", getattr(exc, "sqlstate", None))
        status, msg = map_db_error(exc)
        return error_response("DATABASE_ERROR", msg, status)
    except Exception as exc:
        current_app.logger.exception("Unexpected error in update_comment: %s", exc)
        return error_response("INTERNAL_ERROR", "Unexpected server error.", 500)


@comments_bp.delete("/comments/<int:comment_id>")
@login_required
def delete_comment(comment_id: int):
    """Delete an owned comment, cascading to likes and replies."""
    user_id = current_user_id()

    try:
        err = delete_comment_cascade(comment_id, user_id)
        if err is not None:
            return err

        return "", 204

    except psycopg.Error as exc:
        current_app.logger.warning("Database error in delete_comment (SQLSTATE %s)", getattr(exc, "sqlstate", None))
        status, msg = map_db_error_for_delete(exc)
        return error_response("DATABASE_ERROR", msg, status)
    except Exception as exc:
        current_app.logger.exception("Unexpected error in delete_comment: %s", exc)
        return error_response("INTERNAL_ERROR", "Unexpected server error.", 500)
