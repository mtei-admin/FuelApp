"""Database initialization utilities for the Fuel Requisition System."""
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple


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
                    address TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                );
                """
            )
            _ensure_user_full_name_column(connection)
            _ensure_vendor_address_column(connection)
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
            _ensure_car_fuel_type_column(connection)
            _ensure_car_company_column(connection)
            _ensure_car_driver_name_column(connection)
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
            _migrate_prepared_approved_to_full_names(connection)
            _migrate_legacy_roles_to_accounting(connection)
            _migrate_supervisor_to_approver(connection)
            _ensure_user_email_column(connection)
            _ensure_password_reset_tokens_table(connection)
            _ensure_vendor_fuel_prices_table(connection)
            _ensure_user_sessions_table(connection)
    except sqlite3.Error as error:
        message = f"Failed to initialize database at {db_file}: {error}"
        raise RuntimeError(message) from error


def _ensure_user_full_name_column(connection: sqlite3.Connection) -> None:
    """
    Ensure full_name column exists in users table.
    Adds the column if it doesn't exist.
    """
    cursor = connection.execute("PRAGMA table_info(users);")
    columns = {row[1]: row[1] for row in cursor.fetchall()}
    
    if "full_name" not in columns:
        try:
            connection.execute("ALTER TABLE users ADD COLUMN full_name TEXT;")
        except sqlite3.OperationalError:
            # Column might already exist, ignore
            pass


def _migrate_prepared_approved_to_full_names(connection: sqlite3.Connection) -> None:
    """
    Migrate existing prepared_by and approved_by values from usernames to full_names.
    Looks up each username in the users table and replaces it with the corresponding full_name.
    If full_name is empty, keeps the username as fallback.
    """
    try:
        # Get all requisitions with prepared_by or approved_by values
        cursor = connection.execute(
            """
            SELECT id, prepared_by, approved_by
            FROM requisitions
            WHERE (prepared_by IS NOT NULL AND prepared_by != '')
               OR (approved_by IS NOT NULL AND approved_by != '')
            """
        )
        requisitions = cursor.fetchall()
        
        for req_id, prepared_by, approved_by in requisitions:
            updates = []
            params = []
            
            # Migrate prepared_by
            if prepared_by:
                full_name = _get_full_name_by_username(connection, prepared_by)
                if full_name:
                    updates.append("prepared_by = ?")
                    params.append(full_name)
                # If full_name is empty, keep username (fallback)
            
            # Migrate approved_by
            if approved_by:
                full_name = _get_full_name_by_username(connection, approved_by)
                if full_name:
                    updates.append("approved_by = ?")
                    params.append(full_name)
                # If full_name is empty, keep username (fallback)
            
            # Update if we have changes
            if updates:
                params.append(req_id)
                connection.execute(
                    f"UPDATE requisitions SET {', '.join(updates)} WHERE id = ?",
                    params
                )
    except sqlite3.Error:
        # Silently fail - migration is optional
        pass


def _migrate_legacy_roles_to_accounting(connection: sqlite3.Connection) -> None:
    """
    Migrate legacy roles 'admin' and 'finance' to 'accounting'.
    """
    try:
        connection.execute(
            "UPDATE users SET role = 'accounting' WHERE LOWER(TRIM(role)) IN ('admin', 'finance')"
        )
    except sqlite3.Error:
        pass


def _migrate_supervisor_to_approver(connection: sqlite3.Connection) -> None:
    """
    Migrate role 'supervisor' to 'approver' for consistency with UI naming.
    """
    try:
        connection.execute(
            "UPDATE users SET role = 'approver' WHERE LOWER(TRIM(role)) = 'supervisor'"
        )
    except sqlite3.Error:
        pass


def _ensure_user_email_column(connection: sqlite3.Connection) -> None:
    """Ensure email column exists on users table (for password reset)."""
    cursor = connection.execute("PRAGMA table_info(users);")
    columns = {row[1]: row[1] for row in cursor.fetchall()}
    if "email" not in columns:
        try:
            connection.execute("ALTER TABLE users ADD COLUMN email TEXT;")
        except sqlite3.OperationalError:
            pass


def _ensure_password_reset_tokens_table(connection: sqlite3.Connection) -> None:
    """Create password_reset_tokens table if it does not exist."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        """
    )


def _ensure_vendor_fuel_prices_table(connection: sqlite3.Connection) -> None:
    """Create vendor_fuel_prices table if it does not exist (one row per vendor)."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS vendor_fuel_prices (
            vendor_id INTEGER PRIMARY KEY,
            diesel_price REAL,
            unleaded_price REAL,
            premium_price REAL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_by INTEGER,
            FOREIGN KEY (vendor_id) REFERENCES vendors (id),
            FOREIGN KEY (updated_by) REFERENCES users (id)
        );
        """
    )


def _ensure_user_sessions_table(connection: sqlite3.Connection) -> None:
    """Create user_sessions table for cookie-based session persistence."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        """
    )


def _get_full_name_by_username(connection: sqlite3.Connection, username: str) -> Optional[str]:
    """
    Helper to get full_name by username from a connection.
    Returns username if full_name is empty.
    """
    cursor = connection.execute(
        "SELECT full_name, username FROM users WHERE username = ?",
        (username,)
    )
    row = cursor.fetchone()
    if row:
        full_name = row[0] if row[0] else row[1]  # Use username if full_name is empty
        return full_name
    return None


def _ensure_vendor_address_column(connection: sqlite3.Connection) -> None:
    """
    Migrate vendor table: rename 'contact' column to 'address' if it exists.
    
    SQLite doesn't support ALTER TABLE RENAME COLUMN in older versions,
    so we check if 'contact' exists and 'address' doesn't, then migrate.
    """
    cursor = connection.execute("PRAGMA table_info(vendors);")
    columns = {row[1]: row[1] for row in cursor.fetchall()}
    
    if "contact" in columns and "address" not in columns:
        # SQLite 3.25.0+ supports RENAME COLUMN
        try:
            connection.execute("ALTER TABLE vendors RENAME COLUMN contact TO address;")
        except sqlite3.OperationalError:
            # Fallback for older SQLite: create new column, copy data, drop old
            connection.execute("ALTER TABLE vendors ADD COLUMN address TEXT;")
            connection.execute("UPDATE vendors SET address = contact WHERE contact IS NOT NULL;")
            # Note: We can't easily drop the old column in SQLite, so we'll leave it
            # The new 'address' column will be used going forward


def _ensure_car_fuel_type_column(connection: sqlite3.Connection) -> None:
    """
    Ensure fuel_type column exists in cars table.
    Adds the column if it doesn't exist.
    """
    cursor = connection.execute("PRAGMA table_info(cars);")
    columns = {row[1]: row[1] for row in cursor.fetchall()}
    
    if "fuel_type" not in columns:
        try:
            connection.execute("ALTER TABLE cars ADD COLUMN fuel_type TEXT;")
        except sqlite3.OperationalError:
            # Column might already exist, ignore
            pass


def _ensure_car_company_column(connection: sqlite3.Connection) -> None:
    """
    Ensure company column exists in cars table.
    Adds the column if it doesn't exist.
    """
    cursor = connection.execute("PRAGMA table_info(cars);")
    columns = {row[1]: row[1] for row in cursor.fetchall()}
    
    if "company" not in columns:
        try:
            connection.execute("ALTER TABLE cars ADD COLUMN company TEXT;")
        except sqlite3.OperationalError:
            # Column might already exist, ignore
            pass


def _ensure_car_driver_name_column(connection: sqlite3.Connection) -> None:
    """
    Ensure driver_name column exists in cars table.
    Adds the column if it doesn't exist.
    """
    cursor = connection.execute("PRAGMA table_info(cars);")
    columns = {row[1]: row[1] for row in cursor.fetchall()}
    
    if "driver_name" not in columns:
        try:
            connection.execute("ALTER TABLE cars ADD COLUMN driver_name TEXT;")
        except sqlite3.OperationalError:
            # Column might already exist, ignore
            pass


def _ensure_requisition_columns(connection: sqlite3.Connection) -> None:
    """
    Ensure optional requisition columns exist for purchasing/billing flows.

    Columns added if missing:
    - serial_number: TEXT (system-generated, starting at 00001)
    - po_reference: TEXT
    - invoice_number: TEXT
    - unit_price: REAL
    - total_price: REAL
    - is_edited: INTEGER (0 or 1, tracks if requisition has been edited)
    - edited_by: INTEGER (user_id of who edited, NULL if never edited)
    - prepared_by: TEXT (username of who prepared the PO)
    - approved_by: TEXT (username of who approved the requisition)
    """
    required = {
        "serial_number": "TEXT",
        "po_reference": "TEXT",
        "invoice_number": "TEXT",
        "unit_price": "REAL",
        "total_price": "REAL",
        "is_edited": "INTEGER",
        "edited_by": "INTEGER",
        "fuel_type": "TEXT",
        "prepared_by": "TEXT",
        "approved_by": "TEXT",
        "actual_quantity": "REAL",
        "requestor_name": "TEXT",
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
                SELECT id, username, hashed_password, role, is_active, full_name, email
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


def fetch_user_by_id(db_path: str, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user record by ID (for session restore).

    Args:
        db_path: File system path to the SQLite database.
        user_id: User ID to look up.

    Returns:
        A dictionary of user fields if found; otherwise None.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT id, username, hashed_password, role, is_active, full_name, email
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as error:
        message = f"Failed to fetch user by id {user_id}: {error}"
        raise RuntimeError(message) from error


def create_user_session(db_path: str, user_id: int, expires_in_days: int = 7) -> str:
    """
    Create a session for the user; returns the raw token to store in a cookie.

    Args:
        db_path: Database path.
        user_id: User ID.
        expires_in_days: Session validity in days.

    Returns:
        Raw token string (store in cookie; pass to get_user_id_from_session / delete_user_session).
    """
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = (datetime.now() + timedelta(days=expires_in_days)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                INSERT INTO user_sessions (token_hash, user_id, expires_at)
                VALUES (?, ?, ?)
                """,
                (token_hash, user_id, expires_at),
            )
        return token
    except sqlite3.Error as error:
        message = f"Failed to create session: {error}"
        raise RuntimeError(message) from error


def get_user_id_from_session(db_path: str, token: str) -> Optional[int]:
    """
    Validate session token and return user_id if valid and not expired.

    Args:
        db_path: Database path.
        token: Raw token from cookie.

    Returns:
        user_id or None if invalid/expired.
    """
    if not token or not token.strip():
        return None
    token_hash = hashlib.sha256(token.strip().encode()).hexdigest()
    now = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                SELECT user_id FROM user_sessions
                WHERE token_hash = ? AND expires_at > ?
                """,
                (token_hash, now),
            )
            row = cursor.fetchone()
            return int(row[0]) if row else None
    except (sqlite3.Error, TypeError, ValueError):
        return None


def delete_user_session(db_path: str, token: str) -> None:
    """Invalidate a session by token (e.g. on logout)."""
    if not token or not token.strip():
        return
    token_hash = hashlib.sha256(token.strip().encode()).hexdigest()
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                "DELETE FROM user_sessions WHERE token_hash = ?",
                (token_hash,),
            )
    except sqlite3.Error:
        pass


def fetch_username_by_id(db_path: str, user_id: int) -> Optional[str]:
    """
    Retrieve a username by user ID.

    Args:
        db_path: File system path to the SQLite database.
        user_id: User ID to look up.

    Returns:
        Username string if found; otherwise None.
    """
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                "SELECT username FROM users WHERE id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else None
    except sqlite3.Error as error:
        message = f"Failed to fetch username for user ID {user_id}: {error}"
        raise RuntimeError(message) from error


def fetch_full_name_by_id(db_path: str, user_id: int) -> Optional[str]:
    """
    Retrieve full_name by user ID. Falls back to username if full_name is empty.

    Args:
        db_path: File system path to the SQLite database.
        user_id: User ID to look up.

    Returns:
        Full name string if found (or username if full_name is empty); otherwise None.
    """
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                "SELECT full_name, username FROM users WHERE id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row:
                # Return full_name if available, otherwise username
                return row[0] if row[0] else row[1]
            return None
    except sqlite3.Error as error:
        message = f"Failed to fetch full_name for user ID {user_id}: {error}"
        raise RuntimeError(message) from error


def fetch_user_by_email(db_path: str, email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user record by email (case-insensitive, trimmed).

    Args:
        db_path: File system path to the SQLite database.
        email: Email to look up.

    Returns:
        A dictionary of user fields if found; otherwise None.
    """
    if not email or not email.strip():
        return None
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT id, username, hashed_password, role, is_active, full_name, email
                FROM users
                WHERE LOWER(TRIM(email)) = LOWER(TRIM(?)) AND is_active = 1
                """,
                (email.strip(),),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as error:
        message = f"Failed to fetch user by email: {error}"
        raise RuntimeError(message) from error


def create_password_reset_token(db_path: str, user_id: int) -> Tuple[str, str]:
    """
    Create a one-time password reset token for the user.
    Token expires in 1 hour. Store only the hash of the token.

    Returns:
        Tuple of (raw_token, expires_at_iso).
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now = datetime.now()
    expires_at = now + timedelta(hours=1)
    expires_at_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
                VALUES (?, ?, ?)
                """,
                (user_id, token_hash, expires_at_str),
            )
        return raw_token, expires_at_str
    except sqlite3.Error as error:
        message = f"Failed to create reset token: {error}"
        raise RuntimeError(message) from error


def find_valid_reset_token(db_path: str, raw_token: str) -> Optional[int]:
    """
    Find a valid, unused reset token. Returns user_id if valid and not expired.

    Args:
        db_path: File system path to the SQLite database.
        raw_token: The token string from the reset link.

    Returns:
        user_id if token is valid and not expired; otherwise None.
    """
    if not raw_token or not raw_token.strip():
        return None
    token_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                SELECT user_id FROM password_reset_tokens
                WHERE token_hash = ? AND expires_at > ?
                LIMIT 1
                """,
                (token_hash, now_str),
            )
            row = cursor.fetchone()
            return int(row[0]) if row else None
    except sqlite3.Error as error:
        message = f"Failed to validate reset token: {error}"
        raise RuntimeError(message) from error


def invalidate_reset_token(db_path: str, raw_token: str) -> None:
    """Remove the reset token after use (one-time use)."""
    if not raw_token or not raw_token.strip():
        return
    token_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                "DELETE FROM password_reset_tokens WHERE token_hash = ?",
                (token_hash,),
            )
    except sqlite3.Error as error:
        message = f"Failed to invalidate reset token: {error}"
        raise RuntimeError(message) from error


def _get_next_serial_number(connection: sqlite3.Connection) -> str:
    """
    Generate the next serial number for a requisition.

    Serial numbers start at 00001 and increment sequentially.
    Format: 00001, 00002, 00003, etc.

    Args:
        connection: Active SQLite connection.

    Returns:
        Formatted serial number string (e.g., "00001").
    """
    cursor = connection.execute(
        """
        SELECT MAX(CAST(serial_number AS INTEGER)) as max_serial
        FROM requisitions
        WHERE serial_number IS NOT NULL AND serial_number != ''
        """
    )
    result = cursor.fetchone()
    max_serial = result[0] if result and result[0] is not None else 0
    next_serial = max_serial + 1
    return f"{next_serial:05d}"


def create_requisition(
    db_path: str,
    requester_id: int,
    vehicle_id: int,
    vendor_id: Optional[int],
    quantity: float,
    unit: str,
    unit_price: Optional[float] = None,
    notes: str = "",
    fuel_type: Optional[str] = None,
    requestor_name: Optional[str] = None,
) -> int:
    """
    Create a fuel requisition with pending status and auto-generated serial number.

    Args:
        db_path: File system path to the SQLite database.
        requester_id: ID of the requesting user.
        vehicle_id: ID of the vehicle.
        vendor_id: Optional vendor ID.
        quantity: Requested fuel quantity.
        unit: Unit of measure (e.g., liters).
        unit_price: Optional price per unit.
        notes: Optional notes.
        requestor_name: Optional display name of the requestor (complete name, editable on form).

    Returns:
        The new requisition ID.
    """
    total_price = (quantity * unit_price) if unit_price is not None else None
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            serial_number = _get_next_serial_number(connection)
            cursor = connection.execute(
                """
                INSERT INTO requisitions (
                    serial_number, requester_id, vehicle_id, vendor_id, quantity, unit,
                    unit_price, total_price, status, notes, fuel_type, requestor_name, is_active, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, 1, ?, ?)
                """,
                (serial_number, requester_id, vehicle_id, vendor_id, quantity, unit, unit_price, total_price, notes, fuel_type, (requestor_name or "").strip() or None, timestamp, timestamp),
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
                    r.serial_number,
                    r.quantity,
                    r.unit,
                    r.unit_price,
                    r.total_price,
                    r.status,
                    r.notes,
                    r.created_at,
                    r.updated_at,
                    r.is_edited,
                    r.edited_by,
                    r.requester_id,
                    r.requestor_name,
                    c.plate_number,
                    c.model,
                    v.name AS vendor_name,
                    v.id AS vendor_id
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


def fetch_requisition_by_id(db_path: str, requisition_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch a single requisition by ID with full details.

    Args:
        db_path: File system path to the SQLite database.
        requisition_id: ID of the requisition to fetch.

    Returns:
        A dictionary of requisition fields if found; otherwise None.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT
                    r.id,
                    r.serial_number,
                    r.requester_id,
                    r.vehicle_id,
                    r.vendor_id,
                    r.quantity,
                    r.unit,
                    r.unit_price,
                    r.total_price,
                    r.status,
                    r.notes,
                    r.fuel_type,
                    r.requestor_name,
                    r.created_at,
                    r.updated_at,
                    r.is_edited,
                    r.edited_by,
                    c.plate_number,
                    c.model,
                    v.name AS vendor_name
                FROM requisitions r
                INNER JOIN cars c ON c.id = r.vehicle_id
                LEFT JOIN vendors v ON v.id = r.vendor_id
                WHERE r.id = ? AND r.is_active = 1
                """,
                (requisition_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as error:
        message = f"Failed to fetch requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def get_role_hierarchy_level(role: str) -> int:
    """
    Get the hierarchy level of a role (higher number = higher privilege).

    Role hierarchy: user (1) < approver (2) < purchaser (3) < accounting (4) < superuser (5)

    Args:
        role: User role string (case-insensitive).

    Returns:
        Integer hierarchy level (1-5).
    """
    role_lower = role.lower()
    hierarchy = {
        "user": 1,
        "approver": 2,
        "purchaser": 3,
        "accounting": 4,
        "superuser": 5,
    }
    return hierarchy.get(role_lower, 1)


def can_user_edit_requisition(
    db_path: str, requisition_id: int, user_id: int, user_role: str
) -> tuple:
    """
    Check if a user can edit a requisition.

    Rules:
    - Only creator or higher level users can edit
    - Can only be edited once (if is_edited = 1, cannot edit again)
    - Cannot edit if status is not 'pending' (already in workflow)

    Args:
        db_path: File system path to the SQLite database.
        requisition_id: ID of the requisition to check.
        user_id: ID of the user attempting to edit.
        user_role: Role of the user attempting to edit.

    Returns:
        Tuple of (can_edit: bool, error_message: Optional[str]).
    """
    req = fetch_requisition_by_id(db_path, requisition_id)
    if not req:
        return False, "Requisition not found."

    # Check if already edited
    if req.get("is_edited", 0) == 1:
        return False, "This requisition has already been edited and cannot be edited again."

    # Check if status allows editing (only pending can be edited)
    if req.get("status", "").lower() != "pending":
        return False, "Only pending requisitions can be edited."

    # Check if user is creator
    if req.get("requester_id") == user_id:
        return True, None

    # Check if user has higher role than creator
    creator = fetch_user_by_username(db_path, "")  # We need to get creator's role
    # Instead, let's fetch creator directly
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                "SELECT role FROM users WHERE id = ?", (req.get("requester_id"),)
            )
            creator_row = cursor.fetchone()
            if not creator_row:
                return False, "Creator not found."

            creator_role = creator_row["role"]
            user_level = get_role_hierarchy_level(user_role)
            creator_level = get_role_hierarchy_level(creator_role)

            if user_level > creator_level:
                return True, None
            else:
                return False, "Only the creator or higher level users can edit this requisition."
    except sqlite3.Error as error:
        return False, f"Database error: {error}"


def update_requisition(
    db_path: str,
    requisition_id: int,
    user_id: int,
    user_role: str,
    vehicle_id: int,
    vendor_id: Optional[int],
    quantity: float,
    unit: str,
    unit_price: Optional[float] = None,
    notes: str = "",
    fuel_type: Optional[str] = None,
    requestor_name: Optional[str] = None,
) -> None:
    """
    Update a requisition with edit restrictions.

    Rules:
    - Only creator or higher level users can edit
    - Can only be edited once
    - Only pending requisitions can be edited

    Args:
        db_path: File system path to the SQLite database.
        requisition_id: ID of the requisition to update.
        user_id: ID of the user performing the edit.
        user_role: Role of the user performing the edit.
        vehicle_id: Updated vehicle ID.
        vendor_id: Updated vendor ID (optional).
        quantity: Updated quantity.
        unit: Updated unit.
        unit_price: Updated unit price (optional).
        notes: Updated notes.

    Raises:
        RuntimeError: If edit is not allowed or database operation fails.
    """
    can_edit, error_msg = can_user_edit_requisition(db_path, requisition_id, user_id, user_role)
    if not can_edit:
        raise RuntimeError(error_msg or "Edit not allowed.")

    total_price = (quantity * unit_price) if unit_price is not None else None
    timestamp = _get_local_timestamp()

    try:
        with get_connection(db_path) as connection:
            updates = [
                "vehicle_id = ?",
                "vendor_id = ?",
                "quantity = ?",
                "unit = ?",
                "unit_price = ?",
                "total_price = ?",
                "notes = ?",
                "fuel_type = ?",
                "is_edited = 1",
                "edited_by = ?",
                "updated_at = ?",
            ]
            params = [
                vehicle_id,
                vendor_id,
                quantity,
                unit,
                unit_price,
                total_price,
                notes.strip(),
                fuel_type,
                user_id,
                timestamp,
                requisition_id,
            ]
            if requestor_name is not None:
                updates.append("requestor_name = ?")
                params.insert(-1, (requestor_name or "").strip() or None)
            connection.execute(
                f"UPDATE requisitions SET {', '.join(updates)} WHERE id = ? AND is_active = 1",
                params,
            )
    except sqlite3.Error as error:
        message = f"Failed to update requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def list_pending_requisitions(db_path: str) -> List[Dict[str, Any]]:
    """
    List active pending requisitions for approver review.

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
                    r.serial_number,
                    r.quantity,
                    r.unit,
                    r.unit_price,
                    r.total_price,
                    r.status,
                    r.notes,
                    r.created_at,
                    r.updated_at,
                    r.requester_id,
                    r.vendor_id,
                    r.fuel_type,
                    COALESCE(NULLIF(TRIM(u.full_name), ''), u.username) AS requester_name,
                    c.plate_number,
                    c.model,
                    v.name AS vendor_name,
                    v.address AS vendor_address
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
    approved_by_full_name = None
    if approver_id and status == "approved":
        approved_by_full_name = fetch_full_name_by_id(db_path, approver_id)
    
    try:
        with get_connection(db_path) as connection:
            if approved_by_full_name:
                connection.execute(
                    """
                    UPDATE requisitions
                    SET status = ?, approved_by = ?, updated_at = ?
                    WHERE id = ? AND is_active = 1
                    """,
                    (status, approved_by_full_name, timestamp, requisition_id),
                )
            else:
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


def check_prior_approved_requests(db_path: str, vehicle_id: int, days: int = 2) -> List[Dict[str, Any]]:
    """
    Check for prior approved requisitions for a vehicle within the specified number of days.

    Args:
        db_path: File system path to the SQLite database.
        vehicle_id: ID of the vehicle to check.
        days: Number of days to look back (default: 2).

    Returns:
        A list of approved requisition records as dictionaries, ordered by updated_at DESC.
        Returns empty list if no approved requests found within the time period.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            # Use date arithmetic that works with SQLite
            # SQLite date arithmetic: datetime('now', '-2 days', 'localtime')
            days_str = f"-{days} days"
            cursor = connection.execute(
                """
                SELECT
                    r.id,
                    r.serial_number,
                    r.quantity,
                    r.unit,
                    r.status,
                    r.created_at,
                    r.updated_at,
                    c.plate_number,
                    c.model,
                    v.name AS vendor_name,
                    u.username AS requester_name
                FROM requisitions r
                INNER JOIN cars c ON c.id = r.vehicle_id
                LEFT JOIN vendors v ON v.id = r.vendor_id
                LEFT JOIN users u ON u.id = r.requester_id
                WHERE r.vehicle_id = ?
                    AND r.status = 'approved'
                    AND r.is_active = 1
                    AND datetime(r.updated_at) >= datetime('now', ?, 'localtime')
                ORDER BY r.updated_at DESC
                """,
                (vehicle_id, days_str),
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to check prior approved requests for vehicle {vehicle_id}: {error}"
        raise RuntimeError(message) from error


def update_requisition_po(
    db_path: str, requisition_id: int, po_reference: str, unit_price: Optional[float] = None, prepared_by_user_id: Optional[int] = None
) -> None:
    """
    Mark a requisition as having a generated purchase order and set unit price.

    Args:
        db_path: File system path to the SQLite database.
        requisition_id: ID of the requisition to update.
        po_reference: Optional PO reference text.
        unit_price: Optional price per unit (set by purchaser).
        prepared_by_user_id: Optional user ID of who prepared the PO.
    """
    timestamp = _get_local_timestamp()
    prepared_by_full_name = None
    if prepared_by_user_id:
        prepared_by_full_name = fetch_full_name_by_id(db_path, prepared_by_user_id)
    
    try:
        with get_connection(db_path) as connection:
            # Get quantity to calculate total_price
            cursor = connection.execute(
                "SELECT quantity FROM requisitions WHERE id = ? AND is_active = 1",
                (requisition_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise RuntimeError(f"Requisition {requisition_id} not found or inactive")
            
            quantity = row[0]
            total_price = (quantity * unit_price) if unit_price is not None else None
            
            if prepared_by_full_name:
                connection.execute(
                    """
                    UPDATE requisitions
                    SET status = 'po_generated',
                        po_reference = ?,
                        unit_price = ?,
                        total_price = ?,
                        prepared_by = ?,
                        updated_at = ?
                    WHERE id = ? AND is_active = 1
                    """,
                    (po_reference, unit_price, total_price, prepared_by_full_name, timestamp, requisition_id),
                )
            else:
                connection.execute(
                    """
                    UPDATE requisitions
                    SET status = 'po_generated',
                        po_reference = ?,
                        unit_price = ?,
                        total_price = ?,
                        updated_at = ?
                    WHERE id = ? AND is_active = 1
                    """,
                    (po_reference, unit_price, total_price, timestamp, requisition_id),
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


def update_requisition_actual_quantity(
    db_path: str, requisition_id: int, actual_quantity: float
) -> None:
    """
    Update the actual quantity for a requisition and recalculate total_price.
    
    Used for FULLTANK requests where actual quantity is captured during billing.

    Args:
        db_path: File system path to the SQLite database.
        requisition_id: ID of the requisition to update.
        actual_quantity: Actual quantity delivered (in liters).
    """
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            # Get unit_price to calculate total_price
            cursor = connection.execute(
                "SELECT unit_price FROM requisitions WHERE id = ?",
                (requisition_id,)
            )
            row = cursor.fetchone()
            unit_price = row[0] if row else None
            
            # Calculate total_price if unit_price exists
            total_price = None
            if unit_price and unit_price > 0:
                total_price = actual_quantity * unit_price
            
            if total_price is not None:
                connection.execute(
                    """
                    UPDATE requisitions
                    SET actual_quantity = ?,
                        total_price = ?,
                        updated_at = ?
                    WHERE id = ? AND is_active = 1
                    """,
                    (actual_quantity, total_price, timestamp, requisition_id),
                )
            else:
                connection.execute(
                    """
                    UPDATE requisitions
                    SET actual_quantity = ?,
                        updated_at = ?
                    WHERE id = ? AND is_active = 1
                    """,
                    (actual_quantity, timestamp, requisition_id),
                )
    except sqlite3.Error as error:
        message = f"Failed to update actual quantity for requisition {requisition_id}: {error}"
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
                    r.serial_number,
                    r.quantity,
                    r.unit,
                    r.unit_price,
                    r.total_price,
                    r.actual_quantity,
                    r.status,
                    r.notes,
                    r.po_reference,
                    r.invoice_number,
                    r.fuel_type,
                    r.created_at,
                    r.updated_at,
                    r.requester_id,
                    r.requestor_name,
                    r.prepared_by,
                    r.approved_by,
                    COALESCE(NULLIF(TRIM(r.requestor_name), ''), u.username) AS requester_name,
                    c.plate_number,
                    c.model,
                    c.company,
                    r.vendor_id,
                    v.name AS vendor_name,
                    v.address AS vendor_address
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
                SELECT id, name, address, is_active, created_at
                FROM vendors
                WHERE is_active = 1
                ORDER BY name
                """
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to list vendors: {error}"
        raise RuntimeError(message) from error


def get_vendor_fuel_prices(db_path: str) -> List[Dict[str, Any]]:
    """
    List all vendors with their current fuel prices (for price-update UI).

    Returns one row per vendor with vendor_id, name, diesel_price, unleaded_price,
    premium_price, updated_at. Vendors without a row in vendor_fuel_prices appear
    with NULL prices.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT
                    v.id AS vendor_id,
                    v.name AS vendor_name,
                    p.diesel_price,
                    p.unleaded_price,
                    p.premium_price,
                    p.updated_at
                FROM vendors v
                LEFT JOIN vendor_fuel_prices p ON p.vendor_id = v.id
                WHERE v.is_active = 1
                ORDER BY v.name
                """
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to get vendor fuel prices: {error}"
        raise RuntimeError(message) from error


def get_vendor_fuel_price_for_fuel_type(
    db_path: str, vendor_id: Optional[int], fuel_type: Optional[str]
) -> Optional[float]:
    """
    Return current unit price for a vendor and fuel type (Diesel / Unleaded / Premium).

    Args:
        db_path: Database path.
        vendor_id: Vendor ID (may be None).
        fuel_type: One of 'Diesel', 'Unleaded Gasoline', 'Premium Gasoline' (case-insensitive).

    Returns:
        Price per liter or None if not set.
    """
    if vendor_id is None:
        return None
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                SELECT diesel_price, unleaded_price, premium_price
                FROM vendor_fuel_prices
                WHERE vendor_id = ?
                """,
                (vendor_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            diesel, unleaded, premium = row
            ft = (fuel_type or "").strip().lower()
            if "diesel" in ft:
                return float(diesel) if diesel is not None else None
            if "unleaded" in ft:
                return float(unleaded) if unleaded is not None else None
            if "premium" in ft:
                return float(premium) if premium is not None else None
            return None
    except (sqlite3.Error, TypeError, ValueError):
        return None


def upsert_vendor_fuel_prices(
    db_path: str,
    vendor_id: int,
    diesel_price: Optional[float],
    unleaded_price: Optional[float],
    premium_price: Optional[float],
    updated_by_user_id: Optional[int] = None,
) -> None:
    """
    Insert or update fuel prices for one vendor.

    Args:
        db_path: Database path.
        vendor_id: Vendor ID.
        diesel_price: Price per liter for Diesel (optional).
        unleaded_price: Price per liter for Unleaded Gasoline (optional).
        premium_price: Price per liter for Premium Gasoline (optional).
        updated_by_user_id: User ID of the purchaser who updated (optional).
    """
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                INSERT INTO vendor_fuel_prices (
                    vendor_id, diesel_price, unleaded_price, premium_price,
                    updated_at, updated_by
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (vendor_id) DO UPDATE SET
                    diesel_price = excluded.diesel_price,
                    unleaded_price = excluded.unleaded_price,
                    premium_price = excluded.premium_price,
                    updated_at = excluded.updated_at,
                    updated_by = excluded.updated_by
                """,
                (
                    vendor_id,
                    diesel_price,
                    unleaded_price,
                    premium_price,
                    timestamp,
                    updated_by_user_id,
                ),
            )
    except sqlite3.Error as error:
        message = f"Failed to upsert vendor fuel prices: {error}"
        raise RuntimeError(message) from error


def upsert_vendor(db_path: str, name: str, address: str = "") -> int:
    """
    Insert a new vendor or reactivate an existing inactive vendor by name.

    Args:
        db_path: File system path to the SQLite database.
        name: Vendor name (unique).
        address: Optional vendor address.

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
                        SET is_active = 1, address = ?
                        WHERE id = ?
                        """,
                        (address, vendor_id),
                    )
                else:
                    connection.execute(
                        """
                        UPDATE vendors
                        SET address = ?
                        WHERE id = ?
                        """,
                        (address, vendor_id),
                    )
                return vendor_id

            cursor = connection.execute(
                """
                INSERT INTO vendors (name, address, is_active)
                VALUES (?, ?, 1)
                """,
                (name, address),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as error:
        message = f"Vendor name '{name}' already exists."
        raise RuntimeError(message) from error
    except sqlite3.Error as error:
        message = f"Failed to upsert vendor '{name}': {error}"
        raise RuntimeError(message) from error


def update_vendor(db_path: str, vendor_id: int, name: str, address: str = "") -> None:
    """
    Update an existing vendor by ID.

    Args:
        db_path: File system path to the SQLite database.
        vendor_id: ID of the vendor to update.
        name: Updated vendor name.
        address: Updated vendor address.
    """
    try:
        with get_connection(db_path) as connection:
            # Check if name conflicts with another vendor
            cursor = connection.execute(
                "SELECT id FROM vendors WHERE name = ? AND id != ?", (name, vendor_id)
            )
            if cursor.fetchone():
                raise RuntimeError(f"Vendor name '{name}' already exists.")
            
            connection.execute(
                """
                UPDATE vendors
                SET name = ?, address = ?
                WHERE id = ?
                """,
                (name, address, vendor_id),
            )
    except sqlite3.IntegrityError as error:
        message = f"Vendor name '{name}' already exists."
        raise RuntimeError(message) from error
    except sqlite3.Error as error:
        message = f"Failed to update vendor id {vendor_id}: {error}"
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
                    c.fuel_type,
                    c.company,
                    c.driver_name,
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
    db_path: str, plate_number: str, model: str, vendor_id: Optional[int] = None, fuel_type: Optional[str] = None, company: Optional[str] = None, driver_name: Optional[str] = None
) -> int:
    """
    Insert a new car or reactivate/update an existing one by plate number.

    Args:
        db_path: File system path to the SQLite database.
        plate_number: Unique vehicle plate number.
        model: Vehicle model description.
        vendor_id: Optional linked vendor id.
        fuel_type: Optional fuel type (Diesel, Unleaded Gasoline, Premium Gasoline).
        company: Optional company name.
        driver_name: Optional driver's name.

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
                    SET model = ?, vendor_id = ?, fuel_type = ?, company = ?, driver_name = ?, is_active = 1
                    WHERE id = ?
                    """,
                    (model, vendor_id, fuel_type, company, driver_name, car_id),
                )
                return car_id

            cursor = connection.execute(
                """
                INSERT INTO cars (plate_number, model, vendor_id, fuel_type, company, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (plate_number, model, vendor_id, fuel_type, company),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as error:
        message = f"Car plate '{plate_number}' already exists."
        raise RuntimeError(message) from error
    except sqlite3.Error as error:
        message = f"Failed to upsert car '{plate_number}': {error}"
        raise RuntimeError(message) from error


def update_car(
    db_path: str, car_id: int, plate_number: str, model: str, vendor_id: Optional[int] = None, fuel_type: Optional[str] = None, company: Optional[str] = None
) -> None:
    """
    Update an existing car by ID.

    Args:
        db_path: File system path to the SQLite database.
        car_id: ID of the car to update.
        plate_number: Updated plate number.
        model: Updated vehicle model.
        vendor_id: Updated optional vendor ID.
        fuel_type: Updated optional fuel type (Diesel, Unleaded Gasoline, Premium Gasoline).
    """
    try:
        with get_connection(db_path) as connection:
            # Check if plate number conflicts with another car
            cursor = connection.execute(
                "SELECT id FROM cars WHERE plate_number = ? AND id != ?",
                (plate_number, car_id),
            )
            if cursor.fetchone():
                raise RuntimeError(f"Car plate '{plate_number}' already exists.")
            
            connection.execute(
                """
                UPDATE cars
                SET plate_number = ?, model = ?, vendor_id = ?, fuel_type = ?, company = ?
                WHERE id = ?
                """,
                (plate_number, model, vendor_id, fuel_type, company, car_id),
            )
    except sqlite3.IntegrityError as error:
        message = f"Car plate '{plate_number}' already exists."
        raise RuntimeError(message) from error
    except sqlite3.Error as error:
        message = f"Failed to update car id {car_id}: {error}"
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
                SELECT id, username, role, is_active, created_at, full_name, email
                FROM users
                ORDER BY username
                """
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to list users: {error}"
        raise RuntimeError(message) from error


def create_user(
    db_path: str,
    username: str,
    hashed_password: str,
    role: str = "user",
    full_name: Optional[str] = None,
    email: Optional[str] = None,
) -> int:
    """
    Create a new user.

    Args:
        db_path: File system path to the SQLite database.
        username: Unique username.
        hashed_password: Bcrypt-hashed password.
        role: User role (user, approver, purchaser, accounting, superuser).
        full_name: Full name of the user (required).
        email: Optional email (for password reset).

    Returns:
        The new user ID.
    """
    if not full_name or not full_name.strip():
        raise RuntimeError("Full name is required.")
    
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (username, hashed_password, role, is_active, full_name, email)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (username, hashed_password, role, full_name.strip(), (email or "").strip() or None),
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
    full_name: Optional[str] = None,
    email: Optional[str] = None,
) -> None:
    """
    Update user fields (username, role, password, full_name, or email).

    Args:
        db_path: File system path to the SQLite database.
        user_id: User ID to update.
        username: Optional new username.
        role: Optional new role.
        hashed_password: Optional new hashed password.
        full_name: Optional new full name.
        email: Optional new email (empty string clears it).
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
            if full_name is not None:
                if not full_name.strip():
                    raise RuntimeError("Full name cannot be empty.")
                updates.append("full_name = ?")
                params.append(full_name.strip())
            if email is not None:
                updates.append("email = ?")
                params.append((email or "").strip() or None)
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


def get_monthly_usage_by_vehicle(db_path: str, year: int, month: int) -> List[Dict[str, Any]]:
    """
    Get monthly fuel usage aggregated by vehicle for a specific month.
    Excludes FULLTANK requests (only includes numeric quantities).

    Args:
        db_path: File system path to the SQLite database.
        year: Year (e.g., 2025).
        month: Month (1-12).

    Returns:
        List of dictionaries with vehicle info and total quantity.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT
                    c.plate_number,
                    c.model,
                    c.company,
                    SUM(r.quantity) AS total_quantity,
                    COUNT(r.id) AS request_count
                FROM requisitions r
                INNER JOIN cars c ON c.id = r.vehicle_id
                WHERE r.is_active = 1
                    AND r.unit != 'FULLTANK'
                    AND strftime('%Y', r.created_at) = ?
                    AND strftime('%m', r.created_at) = ?
                GROUP BY c.id, c.plate_number, c.model, c.company
                ORDER BY total_quantity DESC
                """,
                (str(year), f"{month:02d}"),
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to get monthly usage by vehicle: {error}"
        raise RuntimeError(message) from error


def get_monthly_usage_by_company(db_path: str, year: int, month: int) -> List[Dict[str, Any]]:
    """
    Get monthly fuel usage aggregated by company for a specific month.
    Excludes FULLTANK requests (only includes numeric quantities).

    Args:
        db_path: File system path to the SQLite database.
        year: Year (e.g., 2025).
        month: Month (1-12).

    Returns:
        List of dictionaries with company and total quantity.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT
                    c.company,
                    SUM(r.quantity) AS total_quantity,
                    COUNT(r.id) AS request_count
                FROM requisitions r
                INNER JOIN cars c ON c.id = r.vehicle_id
                WHERE r.is_active = 1
                    AND r.unit != 'FULLTANK'
                    AND c.company IS NOT NULL
                    AND strftime('%Y', r.created_at) = ?
                    AND strftime('%m', r.created_at) = ?
                GROUP BY c.company
                ORDER BY total_quantity DESC
                """,
                (str(year), f"{month:02d}"),
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to get monthly usage by company: {error}"
        raise RuntimeError(message) from error


def get_top_vehicles_per_company(db_path: str, year: int, month: int, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get top N consuming vehicles per company for a specific month.
    Excludes FULLTANK requests (only includes numeric quantities).

    Args:
        db_path: File system path to the SQLite database.
        year: Year (e.g., 2025).
        month: Month (1-12).
        limit: Number of top vehicles to return per company (default 10).

    Returns:
        Dictionary with company names as keys and lists of top vehicles as values.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT
                    c.company,
                    c.plate_number,
                    c.model,
                    SUM(r.quantity) AS total_quantity,
                    COUNT(r.id) AS request_count
                FROM requisitions r
                INNER JOIN cars c ON c.id = r.vehicle_id
                WHERE r.is_active = 1
                    AND r.unit != 'FULLTANK'
                    AND c.company IS NOT NULL
                    AND strftime('%Y', r.created_at) = ?
                    AND strftime('%m', r.created_at) = ?
                GROUP BY c.company, c.id, c.plate_number, c.model
                ORDER BY c.company, total_quantity DESC
                """,
                (str(year), f"{month:02d}"),
            )
            
            # Group by company and limit to top N per company
            result = {}
            current_company = None
            company_count = 0
            
            for row in cursor.fetchall():
                company = row["company"]
                if company != current_company:
                    current_company = company
                    company_count = 0
                    result[company] = []
                
                if company_count < limit:
                    result[company].append(dict(row))
                    company_count += 1
            
            return result
    except sqlite3.Error as error:
        message = f"Failed to get top vehicles per company: {error}"
        raise RuntimeError(message) from error


def get_fulltank_requests_by_month(db_path: str, year: int, month: int) -> List[Dict[str, Any]]:
    """
    Get FULLTANK requests for a specific month.

    Args:
        db_path: File system path to the SQLite database.
        year: Year (e.g., 2025).
        month: Month (1-12).

    Returns:
        List of FULLTANK requisitions with vehicle and company info.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT
                    r.id,
                    r.serial_number,
                    r.created_at,
                    c.plate_number,
                    c.model,
                    c.company,
                    r.status
                FROM requisitions r
                INNER JOIN cars c ON c.id = r.vehicle_id
                WHERE r.is_active = 1
                    AND r.unit = 'FULLTANK'
                    AND strftime('%Y', r.created_at) = ?
                    AND strftime('%m', r.created_at) = ?
                ORDER BY c.company, c.plate_number, r.created_at DESC
                """,
                (str(year), f"{month:02d}"),
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to get FULLTANK requests: {error}"
        raise RuntimeError(message) from error


def get_fuel_price_trend(db_path: str, months: int = 12, vendor_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get monthly average fuel prices grouped by fuel type for the last N months.
    Only includes requisitions with confirmed prices (po_generated, received, or billed status).

    Args:
        db_path: File system path to the SQLite database.
        months: Number of months to look back (default 12).
        vendor_id: Optional vendor ID to filter by. If None, includes all vendors.

    Returns:
        List of dictionaries with year, month, fuel_type, avg_price, and transaction_count.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            
            # Calculate the cutoff date (months ago from today)
            cutoff_date = datetime.now().replace(day=1)
            for _ in range(months):
                # Go back one month
                if cutoff_date.month == 1:
                    cutoff_date = cutoff_date.replace(year=cutoff_date.year - 1, month=12)
                else:
                    cutoff_date = cutoff_date.replace(month=cutoff_date.month - 1)
            
            cutoff_str = cutoff_date.strftime("%Y-%m-01")
            
            # Build query with optional vendor filter
            query = """
                SELECT
                    strftime('%Y', r.created_at) AS year,
                    strftime('%m', r.created_at) AS month,
                    r.fuel_type,
                    AVG(r.unit_price) AS avg_price,
                    COUNT(r.id) AS transaction_count
                FROM requisitions r
                WHERE r.is_active = 1
                    AND r.status IN ('po_generated', 'received', 'billed')
                    AND r.unit_price IS NOT NULL
                    AND r.unit_price > 0
                    AND r.fuel_type IS NOT NULL
                    AND r.unit != 'FULLTANK'
                    AND r.created_at >= ?
            """
            params = [cutoff_str]
            
            if vendor_id is not None:
                query += " AND r.vendor_id = ?"
                params.append(vendor_id)
            
            query += """
                GROUP BY year, month, r.fuel_type
                ORDER BY year, month, r.fuel_type
            """
            
            cursor = connection.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to get fuel price trend: {error}"
        raise RuntimeError(message) from error
