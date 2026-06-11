"""Cleanup script to soft delete all requisitions without serial numbers."""
from pathlib import Path
import sqlite3

DB_PATH = Path("data") / "fuel_system.db"


def get_connection(db_path: str) -> sqlite3.Connection:
    """Get a SQLite connection with WAL and foreign keys enabled."""
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA foreign_keys=ON;")
    return connection


def soft_delete_requisitions_without_serial(db_path: str) -> int:
    """
    Soft delete all requisitions that don't have a serial number.
    
    Args:
        db_path: Path to the SQLite database.
        
    Returns:
        Number of requisitions soft deleted.
    """
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                UPDATE requisitions
                SET is_active = 0
                WHERE (serial_number IS NULL OR serial_number = '') AND is_active = 1
                """
            )
            count = cursor.rowcount
            connection.commit()
            return count
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to soft delete requisitions: {error}") from error


def count_requisitions_without_serial(db_path: str) -> int:
    """Count how many active requisitions don't have serial numbers."""
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                SELECT COUNT(*) 
                FROM requisitions
                WHERE (serial_number IS NULL OR serial_number = '') AND is_active = 1
                """
            )
            return cursor.fetchone()[0]
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to count requisitions: {error}") from error


def main() -> None:
    """Main cleanup function."""
    db_path_str = str(DB_PATH)
    
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return
    
    # Count first
    count = count_requisitions_without_serial(db_path_str)
    print(f"Found {count} active requisition(s) without serial numbers.")
    
    if count == 0:
        print("No requisitions to delete.")
        return
    
    # Confirm
    response = input(f"Are you sure you want to soft delete {count} requisition(s)? (yes/no): ")
    if response.lower() != "yes":
        print("Operation cancelled.")
        return
    
    # Delete
    deleted = soft_delete_requisitions_without_serial(db_path_str)
    print(f"Successfully soft deleted {deleted} requisition(s) without serial numbers.")


if __name__ == "__main__":
    main()

