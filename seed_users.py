"""Seed or update all production users from data/seed_users.json."""
import argparse
import json
import os
from getpass import getpass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.auth import hash_password
from src.database import (
    create_user,
    fetch_user_by_username,
    init_database,
    reactivate_user,
    update_user,
)

DB_PATH = Path("data") / "fuel_system.db"
SEED_FILE = Path("data") / "seed_users.json"


def load_seed_users() -> List[Dict[str, Any]]:
    """Load user definitions from the JSON seed file."""
    if not SEED_FILE.is_file():
        raise FileNotFoundError(f"Seed file not found: {SEED_FILE}")
    with SEED_FILE.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("seed_users.json must contain a JSON array of users.")
    return data


def resolve_password(cli_password: Optional[str], reset_passwords: bool) -> Optional[str]:
    """
    Resolve seed password from CLI, environment, or prompt.

    Returns None when existing users should keep their current password.
    """
    if not reset_passwords:
        return None

    password = cli_password or os.environ.get("SEED_USER_PASSWORD", "").strip()
    if password:
        return password

    password = getpass("Enter default password for all seeded users: ")
    confirm = getpass("Confirm password: ")
    if password != confirm:
        raise ValueError("Passwords do not match.")
    if not password:
        raise ValueError("Password cannot be empty when --reset-passwords is used.")
    return password


def upsert_seed_user(
    db_path: str,
    entry: Dict[str, Any],
    password: Optional[str],
) -> str:
    """
    Create or update one user from a seed entry.

    Returns:
        'created', 'updated', or 'unchanged'.
    """
    username = str(entry["username"]).strip()
    role = str(entry["role"]).strip().lower()
    if role == "user":
        role = "encoder"
    full_name = str(entry.get("full_name") or username).strip()
    email_raw = entry.get("email")
    email = str(email_raw).strip() if email_raw else None
    company_raw = entry.get("company")
    company = str(company_raw).strip() if company_raw else None

    existing = fetch_user_by_username(db_path, username)
    if existing:
        user_id = int(existing["id"])
        changed = False

        if not existing.get("is_active"):
            reactivate_user(db_path, user_id)
            changed = True

        if (existing.get("role") or "").lower() != role:
            update_user(db_path, user_id, role=role)
            changed = True

        if (existing.get("full_name") or "") != full_name:
            update_user(db_path, user_id, full_name=full_name)
            changed = True

        existing_email = existing.get("email") or None
        if existing_email != email:
            update_user(db_path, user_id, email=email)
            changed = True

        existing_company = (existing.get("company") or "").strip() or None
        if existing_company != company:
            update_user(db_path, user_id, company=company)
            changed = True

        if password:
            update_user(db_path, user_id, hashed_password=hash_password(password))
            changed = True

        return "updated" if changed else "unchanged"

    if not password:
        raise RuntimeError(
            f"User '{username}' does not exist. Run with --reset-passwords "
            "or set SEED_USER_PASSWORD to create new accounts."
        )

    create_user(
        db_path,
        username,
        hash_password(password),
        role,
        full_name,
        email,
        company=company,
    )
    return "created"


def seed_all_users(
    db_path: str,
    password: Optional[str],
) -> Dict[str, int]:
    """Upsert every user from the seed file."""
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    for entry in load_seed_users():
        result = upsert_seed_user(db_path, entry, password)
        counts[result] += 1
        print(f"  {entry['username']}: {result}")
    return counts


def main() -> None:
    """Run user seeding from data/seed_users.json."""
    parser = argparse.ArgumentParser(
        description="Seed all users from data/seed_users.json (create missing, sync roles/names)."
    )
    parser.add_argument(
        "--reset-passwords",
        action="store_true",
        help="Set the same password on every seeded user (prompt or SEED_USER_PASSWORD).",
    )
    parser.add_argument(
        "--password",
        help="Default password (use with --reset-passwords; prefer SEED_USER_PASSWORD in .env).",
    )
    args = parser.parse_args()

    db_path = str(DB_PATH)
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    init_database(db_path)
    password = resolve_password(args.password, args.reset_passwords)

    print(f"Seeding users from {SEED_FILE} ...")
    counts = seed_all_users(db_path, password)
    print(
        f"Done. created={counts['created']} updated={counts['updated']} "
        f"unchanged={counts['unchanged']}"
    )


if __name__ == "__main__":
    main()
