import base64
import json
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


def validate_post_create(data: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Validates payload for creating a post.
    Returns: (cleaned_dict, error_message)
    """
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."

    content = data.get("content")
    if content is None or not isinstance(content, str):
        return None, "Post content is required and must be a string."

    stripped_content = content.strip()
    if not stripped_content:
        return None, "Post content cannot be empty."

    # Title is optional, max 200 chars
    title = data.get("title")
    cleaned_title = None
    if title is not None:
        if not isinstance(title, str):
            return None, "Title must be a string."
        cleaned_title = title.strip()
        if len(cleaned_title) > 200:
            return None, "Title must not exceed 200 characters."
        if not cleaned_title:
            cleaned_title = None

    # Location is optional, max 100 chars
    location = data.get("location")
    cleaned_location = None
    if location is not None:
        if not isinstance(location, str):
            return None, "Location must be a string."
        cleaned_location = location.strip()
        if len(cleaned_location) > 100:
            return None, "Location must not exceed 100 characters."
        if not cleaned_location:
            cleaned_location = None

    return {
        "title": cleaned_title,
        "content": stripped_content,
        "location": cleaned_location,
    }, None


def validate_post_update(data: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Validates payload for updating an existing post.
    Returns: (cleaned_dict, error_message)
    """
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."

    fields_to_update = {}

    if "title" in data:
        title = data["title"]
        if title is not None and not isinstance(title, str):
            return None, "Title must be a string or null."
        if title is not None:
            stripped = title.strip()
            if len(stripped) > 200:
                return None, "Title must not exceed 200 characters."
            fields_to_update["title"] = stripped if stripped else None
        else:
            fields_to_update["title"] = None

    if "content" in data:
        content = data["content"]
        if content is None or not isinstance(content, str):
            return None, "Content must be a non-empty string."
        stripped_content = content.strip()
        if not stripped_content:
            return None, "Content cannot be empty."
        fields_to_update["content"] = stripped_content

    if "location" in data:
        loc = data["location"]
        if loc is not None and not isinstance(loc, str):
            return None, "Location must be a string or null."
        if loc is not None:
            stripped_loc = loc.strip()
            if len(stripped_loc) > 100:
                return None, "Location must not exceed 100 characters."
            fields_to_update["location"] = stripped_loc if stripped_loc else None
        else:
            fields_to_update["location"] = None

    if not fields_to_update:
        return None, "At least one editable field ('title', 'content', 'location') must be provided."

    return fields_to_update, None


def validate_text_content(
    data: Any,
    field_name: str = "content",
    max_length: int = 2000,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Validates comment or reply content: non-empty string, max length.
    """
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."

    val = data.get(field_name)
    if val is None or not isinstance(val, str):
        return None, f"'{field_name}' is required and must be a string."

    stripped = val.strip()
    if not stripped:
        return None, f"'{field_name}' cannot be empty."

    if len(stripped) > max_length:
        return None, f"'{field_name}' exceeds maximum limit of {max_length} characters."

    return stripped, None


def validate_pagination_params(
    limit_raw: Any,
    cursor_raw: Optional[str],
    default_limit: int = 20,
    max_limit: int = 50,
) -> Tuple[int, Optional[Tuple[str, int]], Optional[str]]:
    """
    Validates pagination query parameters:
    Returns (limit, cursor_tuple=(created_at_iso, post_id), error_message).
    """
    limit = default_limit
    if limit_raw is not None:
        try:
            limit = int(limit_raw)
            if limit < 1:
                return default_limit, None, "limit must be at least 1."
            if limit > max_limit:
                limit = max_limit
        except (ValueError, TypeError):
            return default_limit, None, "limit must be an integer."

    if not cursor_raw:
        return limit, None, None

    try:
        decoded_bytes = base64.urlsafe_b64decode(cursor_raw.encode("utf-8"))
        payload = json.loads(decoded_bytes.decode("utf-8"))
        if not isinstance(payload, dict):
            return limit, None, "Malformed cursor format."

        created_at_str = payload.get("c")
        post_id = payload.get("id")

        if not created_at_str or not isinstance(post_id, int):
            return limit, None, "Invalid cursor fields."

        # Validate timestamp parseability
        # Note: Accepts standard ISO strings with or without tz
        return limit, (created_at_str, post_id), None

    except Exception:
        return limit, None, "Invalid pagination cursor."
