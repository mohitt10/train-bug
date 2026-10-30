"""Phase 2: authentication.

Session-based auth using Flask's signed session cookie (no extra dependencies).
Passwords are hashed with werkzeug.security (bundled with Flask).

Other phases use:
    from auth import login_required
    from flask import g
    @login_required
    def my_view():
        author_id = g.current_user_id      # int
        me = g.current_user                # dict: user_id, username, email, ...

Account status policy (users.account_status has no fixed vocabulary in the schema):
    'active'    - can log in (new accounts get this value; NULL is treated as active)
    'suspended' - login and all protected endpoints are rejected with 403
"""
import re
from functools import wraps

from flask import Blueprint, g, session
from werkzeug.security import check_password_hash, generate_password_hash

from api_utils import as_dict, db_error_kind, error_response, json_body, success
from db import execute_query

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

ACCOUNT_ACTIVE = "active"
ACCOUNT_SUSPENDED = "suspended"

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,50}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# password_hash is deliberately never part of this list.
PRIVATE_COLUMNS = [
    "user_id", "username", "email", "display_name", "bio",
    "account_status", "created_at", "updated_at",
]
_PRIVATE_SELECT = (
    "SELECT user_id, username, email, display_name, bio, "
    "account_status, created_at, updated_at FROM users"
)


def login_required(view):
    """Require a logged-in, non-suspended user; sets g.current_user / g.current_user_id."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if user_id is None:
            return error_response("AUTH_REQUIRED", "Authentication required.", 401)

        row = execute_query(
            _PRIVATE_SELECT + " WHERE user_id = %s", (user_id,), fetch="one"
        )
        user = as_dict(row, PRIVATE_COLUMNS)
        if user is None:
            session.clear()
            return error_response("AUTH_REQUIRED", "Authentication required.", 401)
        if user["account_status"] == ACCOUNT_SUSPENDED:
            session.clear()
            return error_response(
                "ACCOUNT_SUSPENDED", "This account is suspended.", 403
            )

        g.current_user = user
        g.current_user_id = user["user_id"]
        return view(*args, **kwargs)

    return wrapper


def _validate_registration(body):
    errors = {}

    username = body.get("username")
    username = username.strip() if isinstance(username, str) else ""
    if not USERNAME_RE.match(username):
        errors["username"] = (
            "Username must be 3-50 characters: letters, numbers and underscores only."
        )

    email = body.get("email")
    email = email.strip().lower() if isinstance(email, str) else ""
    if len(email) > 255 or not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address (max 255 characters)."

    password = body.get("password")
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        errors["password"] = "Password must be 8-128 characters."

    display_name = body.get("display_name")
    display_name = display_name.strip() if isinstance(display_name, str) else ""
    display_name = display_name or username
    if len(display_name) > 100:
        errors["display_name"] = "Display name must be at most 100 characters."

    clean = {
        "username": username,
        "email": email,
        "password": password,
        "display_name": display_name,
    }
    return clean, errors


@auth_bp.post("/register")
def register():
    body = json_body()
    if body is None:
        return error_response("INVALID_JSON", "Request body must be a JSON object.", 400)

    data, errors = _validate_registration(body)
    if errors:
        return error_response(
            "VALIDATION_ERROR", next(iter(errors.values())), 400, details=errors
        )

    # Friendly duplicate check. The UNIQUE constraints remain the real guarantee
    # (see the IntegrityError handling below for the race-condition case).
    existing = execute_query(
        "SELECT username, email FROM users "
        "WHERE LOWER(username) = LOWER(%s) OR email = %s",
        (data["username"], data["email"]),
        fetch="all",
    )
    for row in existing or []:
        row = as_dict(row, ["username", "email"])
        if row["username"].lower() == data["username"].lower():
            return error_response(
                "USERNAME_TAKEN", "That username is already taken.", 409
            )
        if row["email"] == data["email"]:
            return error_response(
                "EMAIL_TAKEN", "That email is already registered.", 409
            )

    password_hash = generate_password_hash(data["password"])
    try:
        row = execute_query(
            "INSERT INTO users "
            "(username, email, password_hash, display_name, account_status, "
            " created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
            "RETURNING user_id, username, email, display_name, bio, "
            "account_status, created_at, updated_at",
            (
                data["username"],
                data["email"],
                password_hash,
                data["display_name"],
                ACCOUNT_ACTIVE,
            ),
            fetch="one",
        )
    except Exception as exc:  # noqa: BLE001 - classify, re-raise anything else
        if db_error_kind(exc) == "unique":
            return error_response(
                "ACCOUNT_EXISTS", "Username or email is already registered.", 409
            )
        raise

    user = as_dict(row, PRIVATE_COLUMNS)
    session.clear()
    session["user_id"] = user["user_id"]
    return success({"user": user}, 201)


@auth_bp.post("/login")
def login():
    body = json_body()
    if body is None:
        return error_response("INVALID_JSON", "Request body must be a JSON object.", 400)

    identifier = body.get("identifier") or body.get("username") or ""
    password = body.get("password")
    if (
        not isinstance(identifier, str)
        or not identifier.strip()
        or not isinstance(password, str)
        or not password
    ):
        return error_response(
            "VALIDATION_ERROR", "Enter your username or email and your password.", 400
        )
    identifier = identifier.strip()

    row = execute_query(
        "SELECT user_id, username, email, display_name, bio, account_status, "
        "created_at, updated_at, password_hash "
        "FROM users WHERE LOWER(username) = LOWER(%s) OR email = %s LIMIT 1",
        (identifier, identifier.lower()),
        fetch="one",
    )
    user = as_dict(row, PRIVATE_COLUMNS + ["password_hash"])

    # Same message for unknown user and wrong password (no account enumeration).
    if user is None or not check_password_hash(user["password_hash"], password):
        return error_response(
            "INVALID_CREDENTIALS", "Incorrect username/email or password.", 401
        )
    if user["account_status"] == ACCOUNT_SUSPENDED:
        return error_response("ACCOUNT_SUSPENDED", "This account is suspended.", 403)

    user.pop("password_hash")
    session.clear()
    session["user_id"] = user["user_id"]
    return success({"user": user})


@auth_bp.post("/logout")
@login_required
def logout():
    session.clear()
    return "", 204
