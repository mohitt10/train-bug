from flask import Blueprint, jsonify, request

from .compat import (
    current_user_id,
    login_required,
    map_db_error,
    run_query,
    transaction,
)
from .serializers import serialize_comment
from .validators import validate_text_content

comments_bp = Blueprint("comments", __name__)


def delete_comment_cascade(comment_id: int) -> None:
    """
    DELETE POLICY: pending team decision (ON DELETE behavior)
    Application-level cascade to enforce referential integrity:
    1. Delete replies belonging to this comment
    2. Delete the comment record itself
    Note: Comment likes table belongs to Phase 4.
    """
    with transaction():
        run_query(
            "DELETE FROM replies WHERE comment_id = %s;",
            (comment_id,),
            action="comment:delete_replies",
            fetch="none",
        )
        run_query(
            "DELETE FROM comments WHERE comment_id = %s;",
            (comment_id,),
            action="comment:delete",
            fetch="none",
        )


@comments_bp.get("/posts/<int:post_id>/comments")
def get_post_comments(post_id: int):
    """Retrieve comments for a post, ordered chronologically with author info and reply counts."""
    try:
        # Check post existence
        post_row = run_query(
            "SELECT post_id FROM posts WHERE post_id = %s;",
            (post_id,),
            action="post:exists",
            fetch="one",
        )
        if not post_row:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Post not found."}}), 404

        rows = run_query(
            """
            SELECT c.comment_id, c.user_id, c.post_id, c.content, c.created_at, c.updated_at,
                   u.username, u.display_name,
                   (SELECT COUNT(*) FROM replies r WHERE r.comment_id = c.comment_id) AS reply_count
            FROM comments c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.post_id = %s
            ORDER BY c.created_at ASC, c.comment_id ASC;
            """,
            (post_id,),
            action="comment:list",
            fetch="all",
        )

        items = [serialize_comment(r) for r in rows]
        return jsonify({"items": items}), 200

    except Exception as exc:
        status, msg = map_db_error(exc)
        return jsonify({"error": {"code": "DATABASE_ERROR", "message": msg}}), status


@comments_bp.post("/posts/<int:post_id>/comments")
@login_required
def create_comment(post_id: int):
    """Create a new comment on a post (max 2,000 characters)."""
    data = request.get_json(silent=True)
    content, err = validate_text_content(data, field_name="content", max_length=2000)
    if err:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": err}}), 400

    user_id = current_user_id()

    try:
        post_row = run_query(
            "SELECT post_id FROM posts WHERE post_id = %s;",
            (post_id,),
            action="post:exists",
            fetch="one",
        )
        if not post_row:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Post not found."}}), 404

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

    except Exception as exc:
        status, msg = map_db_error(exc)
        return jsonify({"error": {"code": "DATABASE_ERROR", "message": msg}}), status


@comments_bp.patch("/comments/<int:comment_id>")
@login_required
def update_comment(comment_id: int):
    """Update text of an owned comment (max 2,000 characters)."""
    data = request.get_json(silent=True)
    content, err = validate_text_content(data, field_name="content", max_length=2000)
    if err:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": err}}), 400

    user_id = current_user_id()

    try:
        owner_row = run_query(
            "SELECT comment_id, user_id FROM comments WHERE comment_id = %s;",
            (comment_id,),
            action="comment:get_owner",
            fetch="one",
        )

        if not owner_row:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Comment not found."}}), 404

        if owner_row["user_id"] != user_id:
            return jsonify({
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to edit this comment.",
                }
            }), 403

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
                   (SELECT COUNT(*) FROM replies r WHERE r.comment_id = c.comment_id) AS reply_count
            FROM comments c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.comment_id = %s;
            """,
            (comment_id,),
            action="comment:get_updated",
            fetch="one",
        )

        return jsonify(serialize_comment(updated_row)), 200

    except Exception as exc:
        status, msg = map_db_error(exc)
        return jsonify({"error": {"code": "DATABASE_ERROR", "message": msg}}), status


@comments_bp.delete("/comments/<int:comment_id>")
@login_required
def delete_comment(comment_id: int):
    """Delete an owned comment and its nested replies."""
    user_id = current_user_id()

    try:
        owner_row = run_query(
            "SELECT comment_id, user_id FROM comments WHERE comment_id = %s;",
            (comment_id,),
            action="comment:get_owner",
            fetch="one",
        )

        if not owner_row:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Comment not found."}}), 404

        if owner_row["user_id"] != user_id:
            return jsonify({
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to delete this comment.",
                }
            }), 403

        delete_comment_cascade(comment_id)
        return "", 204

    except Exception as exc:
        status, msg = map_db_error(exc)
        return jsonify({"error": {"code": "DATABASE_ERROR", "message": msg}}), status
