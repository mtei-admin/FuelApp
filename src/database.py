"""Database initialization utilities for the Fuel Requisition System."""
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional


def _get_local_timestamp() -> str:
    """
    Get current local timestamp in ISO format.

    Returns:
        ISO format timestamp string (YYYY-MM-DD HH:MM:SS) in local timezone.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_database(db_path: str) -> None:
    """
    Initialize the SQLite database, enabling WAL mode and creating base tables.

    Args:
        db_path: File system path where the SQLite database should be stored.
    """
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with sqlite3.connect(db_file) as connection:
            connection.execute("PRAGMA journal_mode=WAL;")
            connection.execute("PRAGMA foreign_keys=ON;")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    hashed_password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                );
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS vendors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    contact TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                );
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate_number TEXT NOT NULL UNIQUE,
                    model TEXT NOT NULL,
                    vendor_id INTEGER,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (vendor_id) REFERENCES vendors (id)
                );
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS requisitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    requester_id INTEGER NOT NULL,
                    vehicle_id INTEGER NOT NULL,
                    vendor_id INTEGER,
                    quantity REAL NOT NULL,
                    unit TEXT NOT NULL DEFAULT 'liters',
                    status TEXT NOT NULL DEFAULT 'pending',
                    notes TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (requester_id) REFERENCES users (id),
                    FOREIGN KEY (vehicle_id) REFERENCES cars (id),
                    FOREIGN KEY (vendor_id) REFERENCES vendors (id)
                );
                """
            )
            _ensure_requisition_columns(connection)
    except sqlite3.Error as error:
        message = f"Failed to initialize database at {db_file}: {error}"
        raise RuntimeError(message) from error


def _ensure_requisition_columns(connection: sqlite3.Connection) -> None:
    """
    Ensure optional requisition columns exist for purchasing/billing flows.

    Columns added if missing:
    - po_reference: TEXT
    - invoice_number: TEXT
    - unit_price: REAL
    - total_price: REAL
    """
    required = {
        "po_reference": "TEXT",
        "invoice_number": "TEXT",
        "unit_price": "REAL",
        "total_price": "REAL",
    }
    cursor = connection.execute("PRAGMA table_info(requisitions);")
    existing = {row[1] for row in cursor.fetchall()}
    for column_name, column_type in required.items():
        if column_name not in existing:
            connection.execute(
                f"ALTER TABLE requisitions ADD COLUMN {column_name} {column_type};"
            )


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Provide a SQLite connection with WAL and foreign keys enabled.

    Args:
        db_path: File system path to the SQLite database.

    Returns:
        An open sqlite3.Connection with required pragmas set.
    """
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA foreign_keys=ON;")
    return connection


def fetch_user_by_username(db_path: str, username: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user record by username.

    Args:
        db_path: File system path to the SQLite database.
        username: Username to look up.

    Returns:
        A dictionary of user fields if found; otherwise None.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT id, username, hashed_password, role, is_active
                FROM users
                WHERE username = ?
                """,
                (username,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as error:
        message = f"Failed to fetch user '{username}': {error}"
        raise RuntimeError(message) from error


def create_requisition(
    db_path: str,
    requester_id: int,
    vehicle_id: int,
    vendor_id: Optional[int],
    quantity: float,
    unit: str,
    unit_price: Optional[float] = None,
    notes: str = "",
) -> int:
    """
    Create a fuel requisition with pending status.

    Args:
        db_path: File system path to the SQLite database.
        requester_id: ID of the requesting user.
        vehicle_id: ID of the vehicle.
        vendor_id: Optional vendor ID.
        quantity: Requested fuel quantity.
        unit: Unit of measure (e.g., liters).
        unit_price: Optional price per unit.
        notes: Optional notes.

    Returns:
        The new requisition ID.
    """
    total_price = (quantity * unit_price) if unit_price is not None else None
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO requisitions (
                    requester_id, vehicle_id, vendor_id, quantity, unit, unit_price, total_price,
                    status, notes, is_active, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, 1, ?, ?)
                """,
                (requester_id, vehicle_id, vendor_id, quantity, unit, unit_price, total_price, notes, timestamp, timestamp),
            )
            return int(cursor.lastrowid)
    except sqlite3.Error as error:
        message = f"Failed to create requisition: {error}"
        raise RuntimeError(message) from error


def list_requisitions_for_user(db_path: str, requester_id: int) -> List[Dict[str, Any]]:
    """
    List active requisitions for a specific requester.

    Args:
        db_path: File system path to the SQLite database.
        requester_id: User ID whose requisitions are fetched.

    Returns:
        A list of requisition records as dictionaries.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT
                    r.id,
                    r.quantity,
                    r.unit,
                    r.unit_price,
                    r.total_price,
                    r.status,
                    r.notes,
                    r.created_at,
                    r.updated_at,
                    c.plate_number,
                    c.model,
                    v.name AS vendor_name
                FROM requisitions r
                INNER JOIN cars c ON c.id = r.vehicle_id
                LEFT JOIN vendors v ON v.id = r.vendor_id
                WHERE r.is_active = 1 AND r.requester_id = ?
                ORDER BY r.created_at DESC
                """,
                (requester_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to list requisitions for user {requester_id}: {error}"
        raise RuntimeError(message) from error


def list_pending_requisitions(db_path: str) -> List[Dict[str, Any]]:
    """
    List active pending requisitions for supervisor review.

    Args:
        db_path: File system path to the SQLite database.

    Returns:
        A list of pending requisitions as dictionaries.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT
                    r.id,
                    r.quantity,
                    r.unit,
                    r.unit_price,
                    r.total_price,
                    r.status,
                    r.notes,
                    r.created_at,
                    r.updated_at,
                    r.requester_id,
                    u.username AS requester_name,
                    c.plate_number,
                    c.model,
                    v.name AS vendor_name
                FROM requisitions r
                INNER JOIN users u ON u.id = r.requester_id
                INNER JOIN cars c ON c.id = r.vehicle_id
                LEFT JOIN vendors v ON v.id = r.vendor_id
                WHERE r.is_active = 1 AND r.status = 'pending'
                ORDER BY r.created_at DESC
                """
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to list pending requisitions: {error}"
        raise RuntimeError(message) from error


def update_requisition_status(
    db_path: str, requisition_id: int, status: str, approver_id: Optional[int]
) -> None:
    """
    Update the status of a requisition.

    Args:
        db_path: File system path to the SQLite database.
        requisition_id: ID of the requisition to update.
        status: New status value.
        approver_id: Optional user ID of the approver.
    """
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                UPDATE requisitions
                SET status = ?, updated_at = ?
                WHERE id = ? AND is_active = 1
                """,
                (status, timestamp, requisition_id),
            )
    except sqlite3.Error as error:
        message = f"Failed to update requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def update_requisition_po(
    db_path: str, requisition_id: int, po_reference: str
) -> None:
    """
    Mark a requisition as having a generated purchase order.

    Args:
        db_path: File system path to the SQLite database.
        requisition_id: ID of the requisition to update.
        po_reference: Optional PO reference text.
    """
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                UPDATE requisitions
                SET status = 'po_generated',
                    po_reference = ?,
                    updated_at = ?
                WHERE id = ? AND is_active = 1
                """,
                (po_reference, timestamp, requisition_id),
            )
    except sqlite3.Error as error:
        message = f"Failed to mark PO for requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def update_requisition_received(
    db_path: str, requisition_id: int
) -> None:
    """
    Mark a requisition as received.

    Args:
        db_path: File system path to the SQLite database.
        requisition_id: ID of the requisition to update.
    """
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                UPDATE requisitions
                SET status = 'received',
                    updated_at = ?
                WHERE id = ? AND is_active = 1
                """,
                (timestamp, requisition_id),
            )
    except sqlite3.Error as error:
        message = f"Failed to mark received requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def update_requisition_billed(
    db_path: str, requisition_id: int, invoice_number: str
) -> None:
    """
    Mark a requisition as billed with an invoice number.

    Args:
        db_path: File system path to the SQLite database.
        requisition_id: ID of the requisition to update.
        invoice_number: Invoice number to record.
    """
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                UPDATE requisitions
                SET status = 'billed',
                    invoice_number = ?,
                    updated_at = ?
                WHERE id = ? AND is_active = 1
                """,
                (invoice_number, timestamp, requisition_id),
            )
    except sqlite3.Error as error:
        message = f"Failed to mark billed requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def list_requisitions_by_status(
    db_path: str, statuses: List[str]
) -> List[Dict[str, Any]]:
    """
    List active requisitions filtered by status values.

    Args:
        db_path: File system path to the SQLite database.
        statuses: List of status strings to include.

    Returns:
        A list of requisition records.
    """
    if not statuses:
        return []
    placeholders = ",".join("?" for _ in statuses)
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                f"""
                SELECT
                    r.id,
                    r.quantity,
                    r.unit,
                    r.unit_price,
                    r.total_price,
                    r.status,
                    r.notes,
                    r.po_reference,
                    r.invoice_number,
                    r.created_at,
                    r.updated_at,
                    r.requester_id,
                    u.username AS requester_name,
                    c.plate_number,
                    c.model,
                    v.name AS vendor_name
                FROM requisitions r
                INNER JOIN users u ON u.id = r.requester_id
                INNER JOIN cars c ON c.id = r.vehicle_id
                LEFT JOIN vendors v ON v.id = r.vendor_id
                WHERE r.is_active = 1 AND r.status IN ({placeholders})
                ORDER BY r.created_at DESC
                """,
                statuses,
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to list requisitions: {error}"
        raise RuntimeError(message) from error


def list_vendors(db_path: str) -> List[Dict[str, Any]]:
    """
    List active vendors.

    Args:
        db_path: File system path to the SQLite database.

    Returns:
        A list of vendor records as dictionaries.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT id, name, contact, is_active, created_at
                FROM vendors
                WHERE is_active = 1
                ORDER BY name
                """
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to list vendors: {error}"
        raise RuntimeError(message) from error


def upsert_vendor(db_path: str, name: str, contact: str = "") -> int:
    """
    Insert a new vendor or reactivate an existing inactive vendor by name.

    Args:
        db_path: File system path to the SQLite database.
        name: Vendor name (unique).
        contact: Optional contact info.

    Returns:
        The vendor id.
    """
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                "SELECT id, is_active FROM vendors WHERE name = ?", (name,)
            )
            existing = cursor.fetchone()
            if existing:
                vendor_id, is_active = existing
                if not is_active:
                    connection.execute(
                        """
                        UPDATE vendors
                        SET is_active = 1, contact = ?
                        WHERE id = ?
                        """,
                        (contact, vendor_id),
                    )
                else:
                    connection.execute(
                        """
                        UPDATE vendors
                        SET contact = ?
                        WHERE id = ?
                        """,
                        (contact, vendor_id),
                    )
                return vendor_id

            cursor = connection.execute(
                """
                INSERT INTO vendors (name, contact, is_active)
                VALUES (?, ?, 1)
                """,
                (name, contact),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as error:
        message = f"Vendor name '{name}' already exists."
        raise RuntimeError(message) from error
    except sqlite3.Error as error:
        message = f"Failed to upsert vendor '{name}': {error}"
        raise RuntimeError(message) from error


def soft_delete_vendor(db_path: str, vendor_id: int) -> None:
    """
    Soft delete a vendor by setting is_active to 0.

    Args:
        db_path: File system path to the SQLite database.
        vendor_id: Vendor id to deactivate.
    """
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                "UPDATE vendors SET is_active = 0 WHERE id = ?", (vendor_id,)
            )
    except sqlite3.Error as error:
        message = f"Failed to deactivate vendor id {vendor_id}: {error}"
        raise RuntimeError(message) from error


def list_cars(db_path: str) -> List[Dict[str, Any]]:
    """
    List active cars with optional vendor link.

    Args:
        db_path: File system path to the SQLite database.

    Returns:
        A list of car records as dictionaries.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT
                    c.id,
                    c.plate_number,
                    c.model,
                    c.vendor_id,
                    v.name AS vendor_name,
                    c.is_active,
                    c.created_at
                FROM cars c
                LEFT JOIN vendors v ON v.id = c.vendor_id
                WHERE c.is_active = 1
                ORDER BY c.plate_number
                """
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to list cars: {error}"
        raise RuntimeError(message) from error


def upsert_car(
    db_path: str, plate_number: str, model: str, vendor_id: Optional[int] = None
) -> int:
    """
    Insert a new car or reactivate/update an existing one by plate number.

    Args:
        db_path: File system path to the SQLite database.
        plate_number: Unique vehicle plate number.
        model: Vehicle model description.
        vendor_id: Optional linked vendor id.

    Returns:
        The car id.
    """
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                "SELECT id, is_active FROM cars WHERE plate_number = ?",
                (plate_number,),
            )
            existing = cursor.fetchone()
            if existing:
                car_id, is_active = existing
                connection.execute(
                    """
                    UPDATE cars
                    SET model = ?, vendor_id = ?, is_active = 1
                    WHERE id = ?
                    """,
                    (model, vendor_id, car_id),
                )
                return car_id

            cursor = connection.execute(
                """
                INSERT INTO cars (plate_number, model, vendor_id, is_active)
                VALUES (?, ?, ?, 1)
                """,
                (plate_number, model, vendor_id),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as error:
        message = f"Car plate '{plate_number}' already exists."
        raise RuntimeError(message) from error
    except sqlite3.Error as error:
        message = f"Failed to upsert car '{plate_number}': {error}"
        raise RuntimeError(message) from error


def soft_delete_car(db_path: str, car_id: int) -> None:
    """
    Soft delete a car by setting is_active to 0.

    Args:
        db_path: File system path to the SQLite database.
        car_id: Car id to deactivate.
    """
    try:
        with get_connection(db_path) as connection:
            connection.execute("UPDATE cars SET is_active = 0 WHERE id = ?", (car_id,))
    except sqlite3.Error as error:
        message = f"Failed to deactivate car id {car_id}: {error}"
        raise RuntimeError(message) from error


def list_users(db_path: str) -> List[Dict[str, Any]]:
    """
    List all users (active and inactive).

    Args:
        db_path: File system path to the SQLite database.

    Returns:
        A list of user records as dictionaries.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT id, username, role, is_active, created_at
                FROM users
                ORDER BY username
                """
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to list users: {error}"
        raise RuntimeError(message) from error


def create_user(
    db_path: str, username: str, hashed_password: str, role: str = "user"
) -> int:
    """
    Create a new user.

    Args:
        db_path: File system path to the SQLite database.
        username: Unique username.
        hashed_password: Bcrypt-hashed password.
        role: User role (user, supervisor, purchaser, finance).

    Returns:
        The new user ID.
    """
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (username, hashed_password, role, is_active)
                VALUES (?, ?, ?, 1)
                """,
                (username, hashed_password, role),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as error:
        message = f"Username '{username}' already exists."
        raise RuntimeError(message) from error
    except sqlite3.Error as error:
        message = f"Failed to create user '{username}': {error}"
        raise RuntimeError(message) from error


def update_user(
    db_path: str,
    user_id: int,
    username: Optional[str] = None,
    role: Optional[str] = None,
    hashed_password: Optional[str] = None,
) -> None:
    """
    Update user fields (username, role, or password).

    Args:
        db_path: File system path to the SQLite database.
        user_id: User ID to update.
        username: Optional new username.
        role: Optional new role.
        hashed_password: Optional new hashed password.
    """
    try:
        with get_connection(db_path) as connection:
            updates = []
            params = []
            if username is not None:
                updates.append("username = ?")
                params.append(username)
            if role is not None:
                updates.append("role = ?")
                params.append(role)
            if hashed_password is not None:
                updates.append("hashed_password = ?")
                params.append(hashed_password)
            if not updates:
                return
            params.append(user_id)
            connection.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params
            )
    except sqlite3.IntegrityError as error:
        message = f"Username already exists."
        raise RuntimeError(message) from error
    except sqlite3.Error as error:
        message = f"Failed to update user id {user_id}: {error}"
        raise RuntimeError(message) from error


def soft_delete_user(db_path: str, user_id: int) -> None:
    """
    Soft delete a user by setting is_active to 0.

    Args:
        db_path: File system path to the SQLite database.
        user_id: User id to deactivate.
    """
    try:
        with get_connection(db_path) as connection:
            connection.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
    except sqlite3.Error as error:
        message = f"Failed to deactivate user id {user_id}: {error}"
        raise RuntimeError(message) from error


def reactivate_user(db_path: str, user_id: int) -> None:
    """
    Reactivate a user by setting is_active to 1.

    Args:
        db_path: File system path to the SQLite database.
        user_id: User id to reactivate.
    """
    try:
        with get_connection(db_path) as connection:
            connection.execute("UPDATE users SET is_active = 1 WHERE id = ?", (user_id,))
    except sqlite3.Error as error:
        message = f"Failed to reactivate user id {user_id}: {error}"
        raise RuntimeError(message) from error

