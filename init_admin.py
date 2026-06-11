"""Seed script to create the first Accounting user."""
from getpass import getpass
from pathlib import Path
import sqlite3

from src.auth import hash_password
from src.database import init_database


DB_PATH = Path("data") / "fuel_system.db"


def prompt_credentials() -> tuple[str, str]:
    """
    Prompt for accounting username and password with confirmation.

    Returns:
        A tuple containing the username and password.
    """
    username = input("Enter accounting username (default: accounting): ").strip() or "accounting"
    password = getpass("Enter accounting password: ")
    confirm = getpass("Confirm accounting password: ")
    if password != confirm:
        raise ValueError("Passwords do not match. Please rerun the script.")
    return username, password


def upsert_accounting_user(username: str, password: str) -> None:
    """
    Insert or update the Accounting user with a securely hashed password.

    Args:
        username: Desired username for the accounting account.
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
                    (hashed, "accounting", existing[0]),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO users (username, hashed_password, role, is_active)
                    VALUES (?, ?, ?, 1)
                    """,
                    (username, hashed, "accounting"),
                )
    except sqlite3.Error as error:
        message = f"Failed to create or update accounting user: {error}"
        raise RuntimeError(message) from error


def main() -> None:
    """Run the accounting user seeding workflow."""
    username, password = prompt_credentials()
    upsert_accounting_user(username, password)
    print(f"Accounting user '{username}' ensured with Accounting role.")


if __name__ == "__main__":
    main()

