import functools
import psycopg
from flask import Blueprint, current_app, g, jsonify, request

from auth import login_required as session_login_required
from db import execute_query
from api_utils import as_dict
from .compat import current_user_id, login_required, map_db_error, run_query, transaction
from .responses import error_response

reports_bp = Blueprint("reports", __name__)
moderation_bp = Blueprint("moderation", __name__, url_prefix="/moderation")

REPORT_STATUSES = {"pending", "resolved", "dismissed"}
REVIEW_STATUSES = {"resolved", "dismissed"}
TARGET_COLUMNS = {
    "post": ("post_id", "posts", "post_id"),
    "comment": ("comment_id", "comments", "comment_id"),
    "reply": ("reply_id", "replies", "reply_id"),
}

REPORT_SELECT = """
SELECT r.report_id, r.reporter_id, reporter.username AS reporter_username,
       r.reason, r.status, r.created_at, r.post_id, r.comment_id, r.reply_id,
       r.reviewed_by, reviewer.username AS reviewer_username,
       CASE
           WHEN r.post_id IS NOT NULL THEN 'post'
           WHEN r.comment_id IS NOT NULL THEN 'comment'
           ELSE 'reply'
       END AS target_type,
       COALESCE(r.post_id, r.comment_id, r.reply_id) AS target_id,
       LEFT(COALESCE(p.title, p.content, c.content, reply.content), 500) AS target_content
FROM reports r
JOIN users reporter ON reporter.user_id = r.reporter_id
LEFT JOIN moderators m ON m.user_id = r.reviewed_by
LEFT JOIN users reviewer ON reviewer.user_id = m.user_id
LEFT JOIN posts p ON p.post_id = r.post_id
LEFT JOIN comments c ON c.comment_id = r.comment_id
LEFT JOIN replies reply ON reply.reply_id = r.reply_id
"""


def moderator_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        @functools.wraps(view)
        def verify_moderator(*inner_args, **inner_kwargs):
            row = execute_query(
                "SELECT user_id FROM moderators WHERE user_id = %s;",
                (g.current_user_id,),
                fetch="one",
                action="moderation:authorize",
            )
            if as_dict(row, ["user_id"]) is None:
                return error_response("MODERATOR_REQUIRED", "Moderator access is required.", 403)
            return view(*inner_args, **inner_kwargs)

        return session_login_required(verify_moderator)(*args, **kwargs)

    return wrapped


def _serialize_report(row):
    return {
        "report_id": row["report_id"],
        "reporter": {
            "user_id": row["reporter_id"],
            "username": row["reporter_username"],
        },
        "reason": row["reason"],
        "status": row["status"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "target": {
            "type": row["target_type"],
            "id": row["target_id"],
            "content": row["target_content"],
        },
        "reviewed_by": row["reviewed_by"],
        "reviewer_username": row["reviewer_username"],
    }


@reports_bp.post("/reports")
@login_required
def create_report():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error_response("VALIDATION_ERROR", "Request body must be a JSON object.", 400)

    target_type = data.get("target_type")
    target_id = data.get("target_id")
    reason = data.get("reason")
    if not isinstance(target_type, str) or target_type not in TARGET_COLUMNS:
        return error_response("VALIDATION_ERROR", "target_type must be post, comment, or reply.", 400)
    if isinstance(target_id, bool) or not isinstance(target_id, int) or not 1 <= target_id <= 2147483647:
        return error_response("VALIDATION_ERROR", "target_id must be a positive integer.", 400)
    if not isinstance(reason, str) or not reason.strip() or len(reason.strip()) > 500:
        return error_response("VALIDATION_ERROR", "reason must contain 1 to 500 characters.", 400)

    target_column, target_table, target_key = TARGET_COLUMNS[target_type]
    try:
        exists = run_query(
            f"SELECT {target_key} FROM {target_table} WHERE {target_key} = %s;",
            (target_id,),
            action=f"report:{target_type}_exists",
            fetch="one",
        )
        if not exists:
            return error_response("NOT_FOUND", f"{target_type.title()} not found.", 404)

        row = run_query(
            f"""
            INSERT INTO reports (reporter_id, reason, status, created_at, {target_column})
            VALUES (%s, %s, 'pending', CURRENT_TIMESTAMP, %s)
            RETURNING report_id, reporter_id, reason, status, created_at,
                      post_id, comment_id, reply_id, reviewed_by;
            """,
            (current_user_id(), reason.strip(), target_id),
            action="report:create",
            fetch="one",
        )
        return jsonify({
            "report_id": row["report_id"],
            "status": row["status"],
            "target_type": target_type,
            "target_id": target_id,
        }), 201
    except psycopg.Error as exc:
        current_app.logger.warning("Database error creating report (SQLSTATE %s)", getattr(exc, "sqlstate", None))
        status, message = map_db_error(exc)
        if getattr(exc, "sqlstate", None) == "23503":
            return error_response("NOT_FOUND", "The reported content no longer exists.", 404)
        return error_response("DATABASE_ERROR", message, status)
    except Exception as exc:
        current_app.logger.exception("Unexpected error creating report: %s", exc)
        return error_response("INTERNAL_ERROR", "Unexpected server error.", 500)


@moderation_bp.get("/me")
@moderator_required
def get_moderator():
    row = run_query(
        """
        SELECT u.user_id, u.username, u.display_name, m.moderator_since
        FROM moderators m
        JOIN users u ON u.user_id = m.user_id
        WHERE m.user_id = %s;
        """,
        (g.current_user_id,),
        action="moderation:me",
        fetch="one",
    )
    if not row:
        return error_response("MODERATOR_REQUIRED", "Moderator access is required.", 403)
    if row["moderator_since"]:
        row["moderator_since"] = row["moderator_since"].isoformat()
    return jsonify(row), 200


@moderation_bp.get("/reports")
@moderator_required
def list_reports():
    status_filter = request.args.get("status", "pending")
    if status_filter not in REPORT_STATUSES:
        return error_response(
            "VALIDATION_ERROR",
            "status must be pending, resolved, or dismissed.",
            400,
        )

    try:
        limit = int(request.args.get("limit", 25))
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        return error_response("VALIDATION_ERROR", "limit and offset must be integers.", 400)
    if not 1 <= limit <= 100 or offset < 0:
        return error_response("VALIDATION_ERROR", "limit must be 1-100 and offset cannot be negative.", 400)

    rows = run_query(
        REPORT_SELECT + """
        WHERE r.status = %s
        ORDER BY r.created_at DESC, r.report_id DESC
        LIMIT %s OFFSET %s;
        """,
        (status_filter, limit, offset),
        action="moderation:reports_list",
        fetch="all",
    )
    return jsonify({
        "items": [_serialize_report(row) for row in rows],
        "status": status_filter,
        "limit": limit,
        "offset": offset,
    }), 200


@moderation_bp.get("/reports/<int:report_id>")
@moderator_required
def get_report(report_id: int):
    row = run_query(
        REPORT_SELECT + " WHERE r.report_id = %s;",
        (report_id,),
        action="moderation:report_get",
        fetch="one",
    )
    if not row:
        return error_response("NOT_FOUND", "Report not found.", 404)
    return jsonify(_serialize_report(row)), 200


@moderation_bp.patch("/reports/<int:report_id>")
@moderator_required
def review_report(report_id: int):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"status"}:
        return error_response("VALIDATION_ERROR", "Provide only a report status.", 400)
    new_status = data.get("status")
    if not isinstance(new_status, str) or new_status not in REVIEW_STATUSES:
        return error_response("VALIDATION_ERROR", "status must be resolved or dismissed.", 400)

    try:
        with transaction():
            row = run_query(
                "SELECT report_id, status FROM reports WHERE report_id = %s FOR UPDATE;",
                (report_id,),
                action="moderation:report_lock",
                fetch="one",
            )
            if not row:
                return error_response("NOT_FOUND", "Report not found.", 404)
            if row["status"] != "pending":
                return error_response(
                    "REPORT_ALREADY_REVIEWED",
                    "Only pending reports can be reviewed.",
                    409,
                )
            run_query(
                """
                UPDATE reports
                SET status = %s, reviewed_by = %s
                WHERE report_id = %s;
                """,
                (new_status, g.current_user_id, report_id),
                action="moderation:report_review",
                fetch="none",
            )

        updated = run_query(
            REPORT_SELECT + " WHERE r.report_id = %s;",
            (report_id,),
            action="moderation:report_get",
            fetch="one",
        )
        return jsonify(_serialize_report(updated)), 200
    except psycopg.Error as exc:
        current_app.logger.warning("Database error reviewing report (SQLSTATE %s)", getattr(exc, "sqlstate", None))
        status, message = map_db_error(exc)
        return error_response("DATABASE_ERROR", message, status)
    except Exception as exc:
        current_app.logger.exception("Unexpected error reviewing report: %s", exc)
        return error_response("INTERNAL_ERROR", "Unexpected server error.", 500)
