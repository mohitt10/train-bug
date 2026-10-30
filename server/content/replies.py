from flask import Blueprint, jsonify, request

from .compat import (
    current_user_id,
    login_required,
    map_db_error,
    run_query,
    transaction,
)
from .serializers import serialize_reply
from .validators import validate_text_content

replies_bp = Blueprint("replies", __name__)


def delete_reply_cascade(reply_id: int) -> None:
    """
    DELETE POLICY: pending team decision (ON DELETE behavior)
    Delete the reply record.
    """
    with transaction():
        run_query(
            "DELETE FROM replies WHERE reply_id = %s;",
            (reply_id,),
            action="reply:delete",
            fetch="none",
        )


@replies_bp.get("/comments/<int:comment_id>/replies")
def get_comment_replies(comment_id: int):
    """Retrieve replies for a comment, ordered chronologically with author details."""
    try:
        # Check comment existence
        comment_row = run_query(
            "SELECT comment_id FROM comments WHERE comment_id = %s;",
            (comment_id,),
            action="comment:exists",
            fetch="one",
        )
        if not comment_row:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Comment not found."}}), 404

        rows = run_query(
            """
            SELECT r.reply_id, r.user_id, r.comment_id, r.content, r.created_at, r.updated_at,
                   u.username, u.display_name
            FROM replies r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.comment_id = %s
            ORDER BY r.created_at ASC, r.reply_id ASC;
            """,
            (comment_id,),
            action="reply:list",
            fetch="all",
        )

        items = [serialize_reply(r) for r in rows]
        return jsonify({"items": items}), 200

    except Exception as exc:
        status, msg = map_db_error(exc)
        return jsonify({"error": {"code": "DATABASE_ERROR", "message": msg}}), status


@replies_bp.post("/comments/<int:comment_id>/replies")
@login_required
def create_reply(comment_id: int):
    """Create a new reply to a comment (max 2,000 characters)."""
    data = request.get_json(silent=True)
    content, err = validate_text_content(data, field_name="content", max_length=2000)
    if err:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": err}}), 400

    user_id = current_user_id()

    try:
        comment_row = run_query(
            "SELECT comment_id FROM comments WHERE comment_id = %s;",
            (comment_id,),
            action="comment:exists",
            fetch="one",
        )
        if not comment_row:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Comment not found."}}), 404

        inserted = run_query(
            """
            INSERT INTO replies (user_id, comment_id, content, created_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING reply_id, user_id, comment_id, content, created_at, updated_at;
            """,
            (user_id, comment_id, content),
            action="reply:create",
            fetch="one",
        )

        author = run_query(
            "SELECT username, display_name FROM users WHERE user_id = %s;",
            (user_id,),
            action="reply:author_info",
            fetch="one",
        )

        row = dict(inserted)
        row["username"] = author["username"] if author else None
        row["display_name"] = author["display_name"] if author else None

        return jsonify(serialize_reply(row)), 201

    except Exception as exc:
        status, msg = map_db_error(exc)
        return jsonify({"error": {"code": "DATABASE_ERROR", "message": msg}}), status


@replies_bp.patch("/replies/<int:reply_id>")
@login_required
def update_reply(reply_id: int):
    """Update text of an owned reply (max 2,000 characters)."""
    data = request.get_json(silent=True)
    content, err = validate_text_content(data, field_name="content", max_length=2000)
    if err:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": err}}), 400

    user_id = current_user_id()

    try:
        owner_row = run_query(
            "SELECT reply_id, user_id FROM replies WHERE reply_id = %s;",
            (reply_id,),
            action="reply:get_owner",
            fetch="one",
        )

        if not owner_row:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Reply not found."}}), 404

        if owner_row["user_id"] != user_id:
            return jsonify({
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to edit this reply.",
                }
            }), 403

        run_query(
            """
            UPDATE replies
            SET content = %s, updated_at = CURRENT_TIMESTAMP
            WHERE reply_id = %s;
            """,
            (content, reply_id),
            action="reply:update",
            fetch="none",
        )

        updated_row = run_query(
            """
            SELECT r.reply_id, r.user_id, r.comment_id, r.content, r.created_at, r.updated_at,
                   u.username, u.display_name
            FROM replies r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.reply_id = %s;
            """,
            (reply_id,),
            action="reply:get_updated",
            fetch="one",
        )

        return jsonify(serialize_reply(updated_row)), 200

    except Exception as exc:
        status, msg = map_db_error(exc)
        return jsonify({"error": {"code": "DATABASE_ERROR", "message": msg}}), status


@replies_bp.delete("/replies/<int:reply_id>")
@login_required
def delete_reply(reply_id: int):
    """Delete an owned reply."""
    user_id = current_user_id()

    try:
        owner_row = run_query(
            "SELECT reply_id, user_id FROM replies WHERE reply_id = %s;",
            (reply_id,),
            action="reply:get_owner",
            fetch="one",
        )

        if not owner_row:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Reply not found."}}), 404

        if owner_row["user_id"] != user_id:
            return jsonify({
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to delete this reply.",
                }
            }), 403

        delete_reply_cascade(reply_id)
        return "", 204

    except Exception as exc:
        status, msg = map_db_error(exc)
        return jsonify({"error": {"code": "DATABASE_ERROR", "message": msg}}), status
