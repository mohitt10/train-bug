"""Phase 2: profiles and follow relationships.

Policy: every endpoint here requires login (profiles and follower lists are
visible to logged-in users only). Account deletion is NOT implemented - it
depends on the team's foreign-key deletion policy (see docs).
"""
from flask import Blueprint, g

from api_utils import (
    as_dict,
    as_dicts,
    db_error_kind,
    error_response,
    get_pagination,
    json_body,
    success,
)
from auth import login_required
from db import execute_query

users_bp = Blueprint("users", __name__, url_prefix="/api/users")

PROFILE_COLUMNS = [
    "user_id", "username", "display_name", "bio", "account_status",
    "created_at", "follower_count", "following_count", "is_following",
]
_PROFILE_SELECT = """
SELECT u.user_id, u.username, u.display_name, u.bio, u.account_status,
       u.created_at,
       (SELECT COUNT(*) FROM follows WHERE following_id = u.user_id) AS follower_count,
       (SELECT COUNT(*) FROM follows WHERE follower_id  = u.user_id) AS following_count,
       EXISTS (SELECT 1 FROM follows
               WHERE follower_id = %s AND following_id = u.user_id) AS is_following
FROM users u
"""
PROFILE_BY_ID_SQL = _PROFILE_SELECT + " WHERE u.user_id = %s"
PROFILE_BY_USERNAME_SQL = _PROFILE_SELECT + " WHERE LOWER(u.username) = LOWER(%s)"

FOLLOWERS_SQL = """
SELECT u.user_id, u.username, u.display_name, f.followed_at
FROM follows f
JOIN users u ON u.user_id = f.follower_id
WHERE f.following_id = %s
ORDER BY f.followed_at DESC NULLS LAST, u.user_id DESC
LIMIT %s OFFSET %s
"""
FOLLOWERS_COUNT_SQL = "SELECT COUNT(*) AS total FROM follows WHERE following_id = %s"

FOLLOWING_SQL = """
SELECT u.user_id, u.username, u.display_name, f.followed_at
FROM follows f
JOIN users u ON u.user_id = f.following_id
WHERE f.follower_id = %s
ORDER BY f.followed_at DESC NULLS LAST, u.user_id DESC
LIMIT %s OFFSET %s
"""
FOLLOWING_COUNT_SQL = "SELECT COUNT(*) AS total FROM follows WHERE follower_id = %s"

LIST_COLUMNS = ["user_id", "username", "display_name", "followed_at"]


def _profile(sql, target):
    row = execute_query(sql, (g.current_user_id, target), fetch="one")
    profile = as_dict(row, PROFILE_COLUMNS)
    if profile is not None:
        profile["is_following"] = bool(profile["is_following"])
        profile["follower_count"] = int(profile["follower_count"])
        profile["following_count"] = int(profile["following_count"])
    return profile


def _user_exists(user_id):
    row = execute_query(
        "SELECT user_id FROM users WHERE user_id = %s", (user_id,), fetch="one"
    )
    return as_dict(row, ["user_id"]) is not None


def _follow_counts(user_id):
    row = execute_query(
        "SELECT (SELECT COUNT(*) FROM follows WHERE following_id = %s) AS follower_count, "
        "       (SELECT COUNT(*) FROM follows WHERE follower_id  = %s) AS following_count",
        (user_id, user_id),
        fetch="one",
    )
    counts = as_dict(row, ["follower_count", "following_count"])
    return {key: int(value) for key, value in counts.items()}


def _not_found():
    return error_response("USER_NOT_FOUND", "User not found.", 404)


# ---------------------------------------------------------------- profiles

@users_bp.get("/me")
@login_required
def get_me():
    profile = _profile(PROFILE_BY_ID_SQL, g.current_user_id)
    profile["email"] = g.current_user["email"]  # email is only ever shown to its owner
    return success(profile)


@users_bp.patch("/me")
@login_required
def update_me():
    body = json_body()
    if body is None:
        return error_response("INVALID_JSON", "Request body must be a JSON object.", 400)

    assignments, params, errors = [], [], {}

    if "display_name" in body:
        value = body["display_name"]
        value = value.strip() if isinstance(value, str) else ""
        if not 1 <= len(value) <= 100:
            errors["display_name"] = "Display name must be 1-100 characters."
        else:
            assignments.append("display_name = %s")
            params.append(value)

    if "bio" in body:
        value = body["bio"]
        if value is None:
            value = ""
        if not isinstance(value, str) or len(value.strip()) > 500:
            errors["bio"] = "Bio must be at most 500 characters."
        else:
            assignments.append("bio = %s")
            params.append(value.strip() or None)

    if errors:
        return error_response(
            "VALIDATION_ERROR", next(iter(errors.values())), 400, details=errors
        )
    if not assignments:
        return error_response(
            "NO_FIELDS", "Send display_name and/or bio to update.", 400
        )

    # Column names come from the fixed whitelist above; values are bound parameters.
    execute_query(
        "UPDATE users SET " + ", ".join(assignments) + ", updated_at = CURRENT_TIMESTAMP "
        "WHERE user_id = %s RETURNING user_id",
        tuple(params) + (g.current_user_id,),
        fetch="one",
    )

    profile = _profile(PROFILE_BY_ID_SQL, g.current_user_id)
    profile["email"] = g.current_user["email"]
    return success(profile)


@users_bp.get("/<int:user_id>")
@login_required
def get_user(user_id):
    profile = _profile(PROFILE_BY_ID_SQL, user_id)
    return success(profile) if profile else _not_found()


@users_bp.get("/by-username/<username>")
@login_required
def get_user_by_username(username):
    profile = _profile(PROFILE_BY_USERNAME_SQL, username)
    return success(profile) if profile else _not_found()


# ----------------------------------------------------------------- follows

@users_bp.post("/<int:user_id>/follow")
@login_required
def follow(user_id):
    if not _user_exists(user_id):
        return _not_found()

    # Self-follow and duplicate follows are rejected by the DATABASE
    # (chk_no_self_follow and the composite primary key); we only translate
    # the resulting errors into clean API responses.
    try:
        execute_query(
            "INSERT INTO follows (follower_id, following_id, followed_at) "
            "VALUES (%s, %s, CURRENT_TIMESTAMP) RETURNING follower_id",
            (g.current_user_id, user_id),
            fetch="one",
        )
    except Exception as exc:  # noqa: BLE001
        kind = db_error_kind(exc)
        if kind == "check":
            return error_response(
                "CANNOT_FOLLOW_SELF", "You cannot follow yourself.", 400
            )
        if kind == "unique":
            return error_response(
                "ALREADY_FOLLOWING", "You already follow this user.", 409
            )
        if kind == "fk":
            return _not_found()
        raise

    return success({"following": True, **_follow_counts(user_id)}, 201)


@users_bp.delete("/<int:user_id>/follow")
@login_required
def unfollow(user_id):
    row = execute_query(
        "DELETE FROM follows WHERE follower_id = %s AND following_id = %s "
        "RETURNING follower_id",
        (g.current_user_id, user_id),
        fetch="one",
    )
    if as_dict(row, ["follower_id"]) is None:
        return error_response("NOT_FOLLOWING", "You do not follow this user.", 404)
    return success({"following": False, **_follow_counts(user_id)})


def _paged_follow_list(user_id, list_sql, count_sql):
    if not _user_exists(user_id):
        return _not_found()
    page, limit, offset = get_pagination()
    rows = execute_query(list_sql, (user_id, limit, offset), fetch="all")
    total_row = execute_query(count_sql, (user_id,), fetch="one")
    total = int(as_dict(total_row, ["total"])["total"])
    return success(
        {
            "items": as_dicts(rows, LIST_COLUMNS),
            "page": page,
            "limit": limit,
            "total": total,
        }
    )


@users_bp.get("/<int:user_id>/followers")
@login_required
def list_followers(user_id):
    return _paged_follow_list(user_id, FOLLOWERS_SQL, FOLLOWERS_COUNT_SQL)


@users_bp.get("/<int:user_id>/following")
@login_required
def list_following(user_id):
    return _paged_follow_list(user_id, FOLLOWING_SQL, FOLLOWING_COUNT_SQL)
