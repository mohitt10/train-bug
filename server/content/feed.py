from flask import Blueprint, jsonify, request

from .compat import map_db_error, run_query
from .serializers import encode_cursor, serialize_author, serialize_post
from .validators import validate_pagination_params

feed_bp = Blueprint("feed", __name__)


@feed_bp.get("/feed")
def get_feed():
    """
    Retrieve newest posts in descending chronological order using cursor-based pagination.
    Cursor encodes (created_at, post_id).
    Default limit: 20, Max limit: 50.
    """
    limit_raw = request.args.get("limit")
    cursor_raw = request.args.get("cursor")

    limit, cursor_tuple, err = validate_pagination_params(limit_raw, cursor_raw)
    if err:
        return jsonify({"error": {"code": "INVALID_PAGINATION", "message": err}}), 400

    params = []
    where_clause = ""

    if cursor_tuple:
        created_at_cursor, post_id_cursor = cursor_tuple
        where_clause = "WHERE (p.created_at < %s) OR (p.created_at = %s AND p.post_id < %s)"
        params.extend([created_at_cursor, created_at_cursor, post_id_cursor])

    # Fetch limit + 1 to check if another page exists
    fetch_limit = limit + 1
    params.append(fetch_limit)

    sql = f"""
        SELECT p.post_id, p.user_id, p.title, p.content, p.location, p.created_at, p.updated_at,
               u.username, u.display_name,
               (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.post_id) AS comment_count
        FROM posts p
        JOIN users u ON p.user_id = u.user_id
        {where_clause}
        ORDER BY p.created_at DESC, p.post_id DESC
        LIMIT %s;
    """

    try:
        rows = run_query(sql, tuple(params), action="feed:list", fetch="all")

        has_next = len(rows) > limit
        items_rows = rows[:limit] if has_next else rows

        next_cursor = None
        if has_next and items_rows:
            last_item = items_rows[-1]
            next_cursor = encode_cursor(last_item["created_at"], last_item["post_id"])

        return jsonify({
            "items": [serialize_post(r) for r in items_rows],
            "next_cursor": next_cursor,
        }), 200

    except Exception as exc:
        status, msg = map_db_error(exc)
        return jsonify({"error": {"code": "DATABASE_ERROR", "message": msg}}), status


@feed_bp.get("/users/<int:user_id>/posts")
def get_user_posts(user_id: int):
    """
    Retrieve posts authored by a specific user, ordered chronologically with cursor pagination.
    """
    limit_raw = request.args.get("limit")
    cursor_raw = request.args.get("cursor")

    limit, cursor_tuple, err = validate_pagination_params(limit_raw, cursor_raw)
    if err:
        return jsonify({"error": {"code": "INVALID_PAGINATION", "message": err}}), 400

    try:
        # Check user existence
        user_row = run_query(
            "SELECT user_id, username, display_name FROM users WHERE user_id = %s;",
            (user_id,),
            action="user:exists",
            fetch="one",
        )
        if not user_row:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "User not found."}}), 404

        params = [user_id]
        cursor_clause = ""

        if cursor_tuple:
            created_at_cursor, post_id_cursor = cursor_tuple
            cursor_clause = "AND ((p.created_at < %s) OR (p.created_at = %s AND p.post_id < %s))"
            params.extend([created_at_cursor, created_at_cursor, post_id_cursor])

        fetch_limit = limit + 1
        params.append(fetch_limit)

        sql = f"""
            SELECT p.post_id, p.user_id, p.title, p.content, p.location, p.created_at, p.updated_at,
                   u.username, u.display_name,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.post_id) AS comment_count
            FROM posts p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.user_id = %s
            {cursor_clause}
            ORDER BY p.created_at DESC, p.post_id DESC
            LIMIT %s;
        """

        rows = run_query(sql, tuple(params), action="feed:user_posts", fetch="all")

        has_next = len(rows) > limit
        items_rows = rows[:limit] if has_next else rows

        next_cursor = None
        if has_next and items_rows:
            last_item = items_rows[-1]
            next_cursor = encode_cursor(last_item["created_at"], last_item["post_id"])

        return jsonify({
            "items": [serialize_post(r) for r in items_rows],
            "next_cursor": next_cursor,
            "user": serialize_author(user_row),
        }), 200

    except Exception as exc:
        status, msg = map_db_error(exc)
        return jsonify({"error": {"code": "DATABASE_ERROR", "message": msg}}), status
