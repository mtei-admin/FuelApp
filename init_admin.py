"""Seed script to create the first Finance admin user."""
from getpass import getpass
from pathlib import Path
import sqlite3

from src.auth import hash_password
from src.database import init_database


DB_PATH = Path("data") / "fuel_system.db"


def prompt_credentials() -> tuple[str, str]:
    """
    Prompt for admin username and password with confirmation.

    Returns:
        A tuple containing the username and password.
    """
    username = input("Enter admin username (default: admin): ").strip() or "admin"
    password = getpass("Enter admin password: ")
    confirm = getpass("Confirm admin password: ")
    if password != confirm:
        raise ValueError("Passwords do not match. Please rerun the script.")
    return username, password


def upsert_finance_user(username: str, password: str) -> None:
    """
    Insert or update the Finance admin user with a securely hashed password.

    Args:
        username: Desired username for the admin account.
        password: Plain-text password to be hashed and stored.
    """
    init_database(str(DB_PATH))
    hashed = hash_password(password)

    try:
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute("PRAGMA journal_mode=WAL;")
            connection.execute("PRAGMA foreign_keys=ON;")
            cursor = connection.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            )
            existing = cursor.fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE users
                    SET hashed_password = ?, role = ?, is_active = 1
                    WHERE id = ?
                    """,
                    (hashed, "Finance", existing[0]),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO users (username, hashed_password, role, is_active)
                    VALUES (?, ?, ?, 1)
                    """,
                    (username, hashed, "Finance"),
                )
    except sqlite3.Error as error:
        message = f"Failed to create or update admin user: {error}"
        raise RuntimeError(message) from error


def main() -> None:
    """Run the admin seeding workflow."""
    username, password = prompt_credentials()
    upsert_finance_user(username, password)
    print(f"Admin user '{username}' ensured with Finance role.")


if __name__ == "__main__":
    main()

