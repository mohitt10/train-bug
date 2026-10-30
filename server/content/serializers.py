import base64
import json
from datetime import datetime
from typing import Any, Dict, Optional


def _format_datetime(val: Any) -> Optional[str]:
    """Formats datetime objects to standard ISO-8601 strings."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def encode_cursor(created_at: Any, post_id: int) -> str:
    """Encodes created_at and post_id into an opaque URL-safe base64 string."""
    created_at_str = _format_datetime(created_at)
    payload = json.dumps({"c": created_at_str, "id": post_id})
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")


def serialize_author(row: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts author identity fields."""
    return {
        "user_id": row.get("user_id"),
        "username": row.get("username"),
        "display_name": row.get("display_name"),
    }


def serialize_post(row: Dict[str, Any]) -> Dict[str, Any]:
    """Formats a database post row into standard JSON."""
    return {
        "post_id": row.get("post_id"),
        "user_id": row.get("user_id"),
        "title": row.get("title"),
        "content": row.get("content"),
        "location": row.get("location"),
        "created_at": _format_datetime(row.get("created_at")),
        "updated_at": _format_datetime(row.get("updated_at")),
        "comment_count": int(row.get("comment_count", 0) or 0),
        "username": row.get("username"),
        "display_name": row.get("display_name"),
        "author": serialize_author(row),
    }


def serialize_comment(row: Dict[str, Any]) -> Dict[str, Any]:
    """Formats a database comment row into standard JSON."""
    return {
        "comment_id": row.get("comment_id"),
        "post_id": row.get("post_id"),
        "user_id": row.get("user_id"),
        "content": row.get("content"),
        "created_at": _format_datetime(row.get("created_at")),
        "updated_at": _format_datetime(row.get("updated_at")),
        "reply_count": int(row.get("reply_count", 0) or 0),
        "username": row.get("username"),
        "display_name": row.get("display_name"),
        "author": serialize_author(row),
    }


def serialize_reply(row: Dict[str, Any]) -> Dict[str, Any]:
    """Formats a database reply row into standard JSON."""
    return {
        "reply_id": row.get("reply_id"),
        "comment_id": row.get("comment_id"),
        "user_id": row.get("user_id"),
        "content": row.get("content"),
        "created_at": _format_datetime(row.get("created_at")),
        "updated_at": _format_datetime(row.get("updated_at")),
        "username": row.get("username"),
        "display_name": row.get("display_name"),
        "author": serialize_author(row),
    }
