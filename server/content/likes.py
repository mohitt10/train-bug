import psycopg
from flask import Blueprint, current_app, jsonify

from .compat import current_user_id, login_required, map_db_error, run_query
from .responses import error_response
from .serializers import serialize_like_summary

likes_bp = Blueprint("likes", __name__)


def _like_resource(resource_type: str, resource_id: int, user_id: int, action: str):
    table = "post_likes" if resource_type == "post" else "comment_likes"
    key = "post_id" if resource_type == "post" else "comment_id"
    parent_table = "posts" if resource_type == "post" else "comments"
    parent_key = key

    parent = run_query(
        f"SELECT {parent_key} FROM {parent_table} WHERE {parent_key} = %s;",
        (resource_id,),
        action=f"{resource_type}:like_target_exists",
        fetch="one",
    )
    if not parent:
        return None, error_response("NOT_FOUND", f"{resource_type.title()} not found.", 404)

    if action == "like":
        run_query(
            f"""
            INSERT INTO {table} (user_id, {key}, liked_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, {key}) DO NOTHING;
            """,
            (user_id, resource_id),
            action=f"{resource_type}:like",
            fetch="none",
        )
    else:
        run_query(
            f"DELETE FROM {table} WHERE user_id = %s AND {key} = %s;",
            (user_id, resource_id),
            action=f"{resource_type}:unlike",
            fetch="none",
        )

    summary = run_query(
        f"""
        SELECT COUNT(*) AS like_count,
               EXISTS (
                   SELECT 1 FROM {table}
                   WHERE user_id = %s AND {key} = %s
               ) AS liked_by_me
        FROM {table}
        WHERE {key} = %s;
        """,
        (user_id, resource_id, resource_id),
        action=f"{resource_type}:like_summary",
        fetch="one",
    )
    return serialize_like_summary(summary), None


def _register_like_routes(resource_type: str):
    route = f"/{resource_type}s/<int:resource_id>/like"

    def like(resource_id: int):
        return _change_like(resource_type, resource_id, "like")

    def unlike(resource_id: int):
        return _change_like(resource_type, resource_id, "unlike")

    likes_bp.add_url_rule(route, endpoint=f"like_{resource_type}", view_func=login_required(like), methods=["POST"])
    likes_bp.add_url_rule(route, endpoint=f"unlike_{resource_type}", view_func=login_required(unlike), methods=["DELETE"])


def _change_like(resource_type: str, resource_id: int, action: str):
    try:
        summary, err = _like_resource(resource_type, resource_id, current_user_id(), action)
        if err:
            return err
        return jsonify(summary), 200
    except psycopg.Error as exc:
        current_app.logger.warning(
            "Database error changing %s like (SQLSTATE %s)",
            resource_type,
            getattr(exc, "sqlstate", None),
        )
        status, message = map_db_error(exc)
        return error_response("DATABASE_ERROR", message, status)
    except Exception as exc:
        current_app.logger.exception("Unexpected error changing %s like: %s", resource_type, exc)
        return error_response("INTERNAL_ERROR", "Unexpected server error.", 500)


_register_like_routes("post")
_register_like_routes("comment")
