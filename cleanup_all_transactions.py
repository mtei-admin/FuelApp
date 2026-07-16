"""Cleanup script to remove all transactional data (requests, POs, fuel prices).

Keeps master data (users, vendors, vehicles) intact.
"""
from pathlib import Path

from src.database import delete_all_transactions, init_database

DB_PATH = Path("data") / "fuel_system.db"


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

    init_database(db_path_str)
    delete_all_transactions(db_path_str)
    print("All transactional data deleted successfully.")
    print("To set next serial numbers, run: python reset_serials.py")


if __name__ == "__main__":
    main()

