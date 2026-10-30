"""Provision moderators using trusted server/database access, never a public API."""

import argparse

from db import execute_query
from api_utils import as_dict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username", help="Existing account to grant moderator access")
    args = parser.parse_args()

    result = execute_query(
        """
        INSERT INTO moderators (user_id, moderator_since)
        SELECT user_id, CURRENT_TIMESTAMP
        FROM users
        WHERE LOWER(username) = LOWER(%s)
        ON CONFLICT (user_id) DO NOTHING
        RETURNING user_id;
        """,
        (args.username,),
        fetch="one",
        action="moderation:provision",
    )
    granted = as_dict(result, ["user_id"])
    if granted:
        print(f"Moderator access granted to user_id={granted['user_id']}.")
        return

    existing = execute_query(
        "SELECT user_id FROM users WHERE LOWER(username) = LOWER(%s);",
        (args.username,),
        fetch="one",
        action="moderation:provision_check",
    )
    if as_dict(existing, ["user_id"]) is None:
        parser.error("No user exists with that username.")
    print(f"User {args.username!r} already has moderator access.")


if __name__ == "__main__":
    main()
