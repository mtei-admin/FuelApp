"""Active session presence service."""
from typing import Any, Dict, List

from src.database import list_active_user_sessions

ACTIVE_IDLE_MINUTES = 15


def get_collapsed_active_users(db_path: str) -> Dict[str, Any]:
    """
    Return online users collapsed to one row per user with device counts.

    Args:
        db_path: SQLite database path.

    Returns:
        Dict with idle_minutes, online_count, and users list.
    """
    sessions = list_active_user_sessions(db_path, idle_minutes=ACTIVE_IDLE_MINUTES)
    grouped: Dict[int, Dict[str, Any]] = {}

    for session in sessions:
        user_id = int(session["user_id"])
        if user_id not in grouped:
            grouped[user_id] = {
                "user_id": user_id,
                "username": session["username"],
                "full_name": session.get("full_name"),
                "role": session["role"],
                "device_count": 0,
                "is_online": False,
                "login_at": session.get("login_at") or "",
                "last_seen_at": session.get("last_seen_at") or "",
                "ip_address": "",
            }

        entry = grouped[user_id]
        entry["device_count"] += 1
        if session.get("is_online"):
            entry["is_online"] = True

        login_at = session.get("login_at") or ""
        if login_at and (not entry["login_at"] or login_at < entry["login_at"]):
            entry["login_at"] = login_at

        last_seen = session.get("last_seen_at") or ""
        if last_seen and last_seen >= entry["last_seen_at"]:
            entry["last_seen_at"] = last_seen
            ip_address = (session.get("ip_address") or "").strip()
            if ip_address:
                entry["ip_address"] = ip_address

    users = list(grouped.values())
    users.sort(key=lambda row: (row["is_online"], row["last_seen_at"] or ""), reverse=True)

    online_count = sum(1 for row in users if row["is_online"])
    return {
        "idle_minutes": ACTIVE_IDLE_MINUTES,
        "online_count": online_count,
        "users": users,
    }
