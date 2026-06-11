"""Cleanup script to remove all transactional data (requests, POs, fuel prices).

Keeps master data (users, vendors, vehicles) intact.
"""
from pathlib import Path
import sqlite3


DB_PATH = Path("data") / "fuel_system.db"


def get_connection(db_path: str) -> sqlite3.Connection:
    """Get a SQLite connection with WAL and foreign keys enabled."""
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA foreign_keys=ON;")
    return connection


def delete_all_transactions(db_path: str) -> None:
    """
    Delete all transactional data while leaving master data untouched.

    Tables affected:
    - requisitions
    - vendor_fuel_prices
    - password_reset_tokens
    - user_sessions
    """
    try:
        with get_connection(db_path) as connection:
            # Wrap in a single transaction
            connection.execute("BEGIN;")

            # Delete all requisitions (requests, POs, billing history)
            connection.execute("DELETE FROM requisitions;")

            # Delete all vendor fuel prices
            connection.execute("DELETE FROM vendor_fuel_prices;")

            # Optional but recommended: clear password reset tokens
            try:
                connection.execute("DELETE FROM password_reset_tokens;")
            except sqlite3.OperationalError:
                # Table may not exist in very old DBs
                pass

            # Optional: clear all user sessions (forces fresh login)
            try:
                connection.execute("DELETE FROM user_sessions;")
            except sqlite3.OperationalError:
                pass

            connection.commit()
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to delete transactional data: {error}") from error


def main() -> None:
    """Entry point for cleanup script."""
    db_path_str = str(DB_PATH)

    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    print("This will permanently delete ALL requests, POs, fuel prices,")
    print("password reset tokens, and user sessions from the database.")
    print("Master data (users, vendors, vehicles) will be kept.")
    confirm = input("Type 'yes' to continue: ")
    if confirm.strip().lower() != "yes":
        print("Operation cancelled.")
        return

    delete_all_transactions(db_path_str)
    print("All transactional data deleted successfully.")
    print("Next new requisition will start serial_number from 00001 again (based on app logic).")


if __name__ == "__main__":
    main()

