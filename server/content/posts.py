from flask import Blueprint, jsonify, request

from .compat import (
    current_user_id,
    login_required,
    map_db_error,
    run_query,
    transaction,
)
from .serializers import serialize_post
from .validators import validate_post_create, validate_post_update

posts_bp = Blueprint("posts", __name__)


def delete_post_cascade(post_id: int) -> None:
    """
    DELETE POLICY: pending team decision (ON DELETE behavior)
    Application-level cascade to enforce referential integrity:
    1. Delete replies on all comments under this post
    2. Delete comments under this post
    3. Delete the post record itself
    Note: Likes and reports tables belong to Phase 4.
    """
    with transaction():
        run_query(
            "DELETE FROM replies WHERE comment_id IN (SELECT comment_id FROM comments WHERE post_id = %s)",
            (post_id,),
            action="post:delete_replies",
            fetch="none",
        )
        run_query(
            "DELETE FROM comments WHERE post_id = %s",
            (post_id,),
            action="post:delete_comments",
            fetch="none",
        )
        run_query(
            "DELETE FROM posts WHERE post_id = %s",
            (post_id,),
            action="post:delete",
            fetch="none",
        )


@posts_bp.post("/posts")
@login_required
def create_post():
    """Create a new post authored by the authenticated user."""
    data = request.get_json(silent=True)
    cleaned, err = validate_post_create(data)
    if err:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": err}}), 400

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

        # Retrieve author details for the newly created post
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

    except Exception as exc:
        status, msg = map_db_error(exc)
        return jsonify({"error": {"code": "DATABASE_ERROR", "message": msg}}), status


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
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Post not found."}}), 404

        return jsonify(serialize_post(row)), 200

    except Exception as exc:
        status, msg = map_db_error(exc)
        return jsonify({"error": {"code": "DATABASE_ERROR", "message": msg}}), status


@posts_bp.patch("/posts/<int:post_id>")
@login_required
def update_post(post_id: int):
    """Update title, content, or location of an owned post."""
    data = request.get_json(silent=True)
    fields, err = validate_post_update(data)
    if err:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": err}}), 400

    user_id = current_user_id()

    try:
        # Check ownership
        owner_row = run_query(
            "SELECT post_id, user_id FROM posts WHERE post_id = %s;",
            (post_id,),
            action="post:get_owner",
            fetch="one",
        )

        if not owner_row:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Post not found."}}), 404

        if owner_row["user_id"] != user_id:
            return jsonify({
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to edit this post.",
                }
            }), 403

        # Build dynamic parameterized UPDATE
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

        # Fetch updated post with joins
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

    except Exception as exc:
        status, msg = map_db_error(exc)
        return jsonify({"error": {"code": "DATABASE_ERROR", "message": msg}}), status


@posts_bp.delete("/posts/<int:post_id>")
@login_required
def delete_post(post_id: int):
    """Delete an owned post and its comments/replies."""
    user_id = current_user_id()

    try:
        owner_row = run_query(
            "SELECT post_id, user_id FROM posts WHERE post_id = %s;",
            (post_id,),
            action="post:get_owner",
            fetch="one",
        )

        if not owner_row:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Post not found."}}), 404

        if owner_row["user_id"] != user_id:
            return jsonify({
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to delete this post.",
                }
            }), 403

        delete_post_cascade(post_id)
        return "", 204

    except Exception as exc:
        status, msg = map_db_error(exc)
        return jsonify({"error": {"code": "DATABASE_ERROR", "message": msg}}), status
