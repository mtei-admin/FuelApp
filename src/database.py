"""Database initialization utilities for the Fuel Requisition System."""
import calendar
import hashlib
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from src.session_policy import (
    SESSION_IDLE_MINUTES,
    is_session_idle_expired,
    workday_session_expires_at,
)
from src.utils.plate import normalize_plate_number, plate_identity_key


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
                    role TEXT NOT NULL DEFAULT 'encoder',
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
            _ensure_car_assigned_to_column(connection)
            _ensure_car_registration_columns(connection)
            _backfill_company_owned_if_needed(connection)
            _ensure_pms_tables(connection)
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
            _ensure_user_company_column(connection)
            _migrate_user_role_to_encoder(connection)
            _ensure_user_email_column(connection)
            _ensure_user_permissions_column(connection)
            _backfill_user_permissions_from_roles(connection)
            _backfill_approver_sign_po_permission(connection)
            _backfill_sign_po_role_alignment(connection)
            _backfill_purchaser_request_permissions(connection)
            _backfill_po_created_at(connection)
            _ensure_password_reset_tokens_table(connection)
            _ensure_vendor_fuel_prices_table(connection)
            _ensure_user_sessions_table(connection)
            _ensure_user_session_activity_columns(connection)
            _ensure_system_sequences_table(connection)
            _ensure_audit_log_table(connection)
            _ensure_companies_table(connection)
            _seed_default_companies(connection)
            _ensure_service_centers_table(connection)
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


def _ensure_user_company_column(connection: sqlite3.Connection) -> None:
    """Ensure company column exists on users (encoder company scope)."""
    cursor = connection.execute("PRAGMA table_info(users);")
    columns = {row[1] for row in cursor.fetchall()}
    if "company" not in columns:
        try:
            connection.execute("ALTER TABLE users ADD COLUMN company TEXT;")
        except sqlite3.OperationalError:
            pass


def _ensure_user_permissions_column(connection: sqlite3.Connection) -> None:
    """Ensure permissions JSON column exists on users."""
    cursor = connection.execute("PRAGMA table_info(users);")
    columns = {row[1] for row in cursor.fetchall()}
    if "permissions" not in columns:
        try:
            connection.execute("ALTER TABLE users ADD COLUMN permissions TEXT;")
        except sqlite3.OperationalError:
            pass


def _backfill_user_permissions_from_roles(connection: sqlite3.Connection) -> None:
    """
    One-time backfill: map legacy users.role to explicit permissions JSON.

    Skips rows that already have non-empty permissions.
    """
    from src.permissions import permissions_for_backfill

    try:
        connection.row_factory = sqlite3.Row
        cursor = connection.execute(
            """
            SELECT id, username, role, permissions
            FROM users
            WHERE permissions IS NULL OR TRIM(permissions) = ''
            """
        )
        rows = cursor.fetchall()
        for row in rows:
            payload = permissions_for_backfill(
                row["role"] or "encoder",
                row["username"] or "",
            )
            connection.execute(
                "UPDATE users SET permissions = ? WHERE id = ?",
                (payload, row["id"]),
            )
    except sqlite3.Error:
        pass


def _backfill_approver_sign_po_permission(connection: sqlite3.Connection) -> None:
    """
    Add purchasing.sign_po to active approver accounts missing it.

    Preserves legacy behavior where approvers appear in the PO signatory list
    without granting full purchasing module access.
    """
    from src.permissions import (
        PURCHASING_SIGN_PO,
        parse_stored_permissions,
        permissions_for_role,
        serialize_permissions,
        user_has_permission,
    )

    try:
        connection.row_factory = sqlite3.Row
        cursor = connection.execute(
            """
            SELECT id, role, permissions
            FROM users
            WHERE is_active = 1
              AND LOWER(TRIM(role)) = 'approver'
            """
        )
        for row in cursor.fetchall():
            user = dict(row)
            if user_has_permission(user, PURCHASING_SIGN_PO):
                continue
            stored = parse_stored_permissions(user.get("permissions"))
            if stored is None:
                codes = permissions_for_role("approver")
            else:
                codes = list(stored)
                if PURCHASING_SIGN_PO not in codes:
                    codes.append(PURCHASING_SIGN_PO)
            connection.execute(
                "UPDATE users SET permissions = ? WHERE id = ?",
                (serialize_permissions(codes), user["id"]),
            )
    except sqlite3.Error:
        pass


def _backfill_sign_po_role_alignment(connection: sqlite3.Connection) -> None:
    """
    Align purchasing.sign_po with legacy signatory roles.

    Grant sign_po to accounting/superuser accounts missing it; remove it from
    purchasers (they pick a signatory but do not sign POs themselves).
    """
    from src.permissions import (
        PURCHASING_SIGN_PO,
        parse_stored_permissions,
        permissions_for_role,
        serialize_permissions,
    )

    sign_po_roles = {"approver", "accounting", "superuser"}
    try:
        connection.row_factory = sqlite3.Row
        cursor = connection.execute(
            "SELECT id, role, permissions FROM users WHERE is_active = 1"
        )
        for row in cursor.fetchall():
            user = dict(row)
            role = (user.get("role") or "encoder").lower()
            stored = parse_stored_permissions(user.get("permissions"))
            if stored is None:
                continue
            codes = list(stored)
            changed = False
            if role in sign_po_roles and PURCHASING_SIGN_PO not in codes:
                codes.append(PURCHASING_SIGN_PO)
                changed = True
            if role == "purchaser" and PURCHASING_SIGN_PO in codes:
                codes = [code for code in codes if code != PURCHASING_SIGN_PO]
                changed = True
            if not changed:
                continue
            if role in sign_po_roles and not codes:
                codes = permissions_for_role(role)
            connection.execute(
                "UPDATE users SET permissions = ? WHERE id = ?",
                (serialize_permissions(codes), user["id"]),
            )
    except sqlite3.Error:
        pass


def _backfill_purchaser_request_permissions(connection: sqlite3.Connection) -> None:
    """
    Add fuel request and purchasing edit permissions to active purchaser accounts.

    Purchasers may submit fuel requests and full-edit supplier, fuel, quantity, and price.
    """
    from src.permissions import (
        FUEL_REQUESTS_CREATE,
        FUEL_REQUESTS_EDIT_OWN,
        PURCHASING_ADMIN_EDIT,
        parse_stored_permissions,
        permissions_for_role,
        serialize_permissions,
        user_has_permission,
    )

    try:
        connection.row_factory = sqlite3.Row
        cursor = connection.execute(
            """
            SELECT id, role, permissions
            FROM users
            WHERE is_active = 1
              AND LOWER(TRIM(role)) = 'purchaser'
            """
        )
        for row in cursor.fetchall():
            user = dict(row)
            if (
                user_has_permission(user, FUEL_REQUESTS_CREATE)
                and user_has_permission(user, FUEL_REQUESTS_EDIT_OWN)
                and user_has_permission(user, PURCHASING_ADMIN_EDIT)
            ):
                continue
            stored = parse_stored_permissions(user.get("permissions"))
            if stored is None:
                codes = permissions_for_role("purchaser")
            else:
                codes = list(stored)
                for code in (
                    FUEL_REQUESTS_CREATE,
                    FUEL_REQUESTS_EDIT_OWN,
                    PURCHASING_ADMIN_EDIT,
                ):
                    if code not in codes:
                        codes.append(code)
            connection.execute(
                "UPDATE users SET permissions = ? WHERE id = ?",
                (serialize_permissions(codes), user["id"]),
            )
    except sqlite3.Error:
        pass


def _backfill_po_created_at(connection: sqlite3.Connection) -> None:
    """
    Backfill po_created_at for rows that already passed PO generation.

    Uses updated_at as best-effort when no explicit PO timestamp was stored.
    """
    try:
        connection.execute(
            """
            UPDATE requisitions
            SET po_created_at = updated_at
            WHERE po_created_at IS NULL
              AND is_active = 1
              AND status IN ('po_generated', 'released', 'received', 'billed')
            """
        )
    except sqlite3.Error:
        pass


def _migrate_user_role_to_encoder(connection: sqlite3.Connection) -> None:
    """Rename legacy role 'user' to 'encoder'."""
    connection.execute(
        "UPDATE users SET role = 'encoder' WHERE LOWER(TRIM(role)) = 'user'"
    )


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
            created_at TEXT,
            last_seen_at TEXT,
            ip_address TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        """
    )


def _ensure_user_session_activity_columns(connection: sqlite3.Connection) -> None:
    """Add session activity columns for online presence tracking."""
    required = {
        "created_at": "TEXT",
        "last_seen_at": "TEXT",
        "ip_address": "TEXT",
    }
    cursor = connection.execute("PRAGMA table_info(user_sessions);")
    existing = {row[1] for row in cursor.fetchall()}
    for column_name, column_type in required.items():
        if column_name not in existing:
            connection.execute(
                f"ALTER TABLE user_sessions ADD COLUMN {column_name} {column_type};"
            )

    now = _get_local_timestamp()
    connection.execute(
        """
        UPDATE user_sessions
        SET created_at = COALESCE(created_at, expires_at),
            last_seen_at = COALESCE(last_seen_at, expires_at)
        WHERE created_at IS NULL OR last_seen_at IS NULL
        """,
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


def _ensure_car_assigned_to_column(connection: sqlite3.Connection) -> None:
    """
    Ensure assigned_to column exists on cars (renamed from legacy driver_name).
    """
    cursor = connection.execute("PRAGMA table_info(cars);")
    columns = {row[1] for row in cursor.fetchall()}

    if "assigned_to" in columns:
        return

    if "driver_name" in columns:
        try:
            connection.execute("ALTER TABLE cars RENAME COLUMN driver_name TO assigned_to;")
        except sqlite3.OperationalError:
            connection.execute("ALTER TABLE cars ADD COLUMN assigned_to TEXT;")
            connection.execute(
                "UPDATE cars SET assigned_to = driver_name WHERE assigned_to IS NULL"
            )
        return

    try:
        connection.execute("ALTER TABLE cars ADD COLUMN assigned_to TEXT;")
    except sqlite3.OperationalError:
        pass


# Days before LTO expiry that count as "due soon" for Registrations alerts.
REGISTRATION_DUE_SOON_DAYS = 30


def _ensure_car_registration_columns(connection: sqlite3.Connection) -> None:
    """
    Ensure LTO / OR-CR registration columns exist on cars.
    """
    cursor = connection.execute("PRAGMA table_info(cars);")
    columns = {row[1] for row in cursor.fetchall()}
    for column_name, column_type in (
        ("lto_expiry", "TEXT"),
        ("registration_date", "TEXT"),
        ("or_number", "TEXT"),
        ("cr_number", "TEXT"),
        ("mv_file_no", "TEXT"),
        ("registration_remarks", "TEXT"),
        ("is_company_owned", "INTEGER NOT NULL DEFAULT 0"),
    ):
        if column_name in columns:
            continue
        try:
            connection.execute(
                f"ALTER TABLE cars ADD COLUMN {column_name} {column_type};"
            )
        except sqlite3.OperationalError:
            pass


def _backfill_company_owned_if_needed(connection: sqlite3.Connection) -> None:
    """
    One-time backfill for DBs that existed before is_company_owned was added.

    Active master-data vehicles are treated as company-owned fleet so they appear
    in Registrations/Renewal without manual re-save.
    """
    _ensure_system_sequences_table(connection)
    cursor = connection.execute(
        "SELECT 1 FROM system_sequences WHERE key = ?",
        ("migration_company_owned_backfill",),
    )
    if cursor.fetchone():
        return
    connection.execute(
        """
        UPDATE cars
        SET is_company_owned = 1
        WHERE is_active = 1 AND IFNULL(is_company_owned, 0) = 0
        """
    )
    connection.execute(
        """
        INSERT INTO system_sequences (key, next_value)
        VALUES ('migration_company_owned_backfill', 1)
        """
    )


def _normalize_optional_iso_date(value: Optional[str], label: str = "LTO expiry") -> Optional[str]:
    """
    Normalize an optional calendar date to YYYY-MM-DD, or None if blank.

    Args:
        value: Raw date string from API/UI.
        label: Field name used in the validation error.

    Returns:
        ISO date string or None.

    Raises:
        RuntimeError: If the value is non-blank but not a valid YYYY-MM-DD date.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as error:
        raise RuntimeError(f"{label} must be a valid date (YYYY-MM-DD).") from error


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    """Strip optional text; empty becomes None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def registration_alert_status(
    lto_expiry: Optional[str],
    today: Optional[date] = None,
    due_soon_days: int = REGISTRATION_DUE_SOON_DAYS,
) -> str:
    """
    Classify a vehicle registration for alerts.

    Returns one of: missing, expired, due_soon, current.
    """
    as_of = today or date.today()
    if not lto_expiry or not str(lto_expiry).strip():
        return "missing"
    try:
        expiry = date.fromisoformat(str(lto_expiry).strip())
    except ValueError:
        return "missing"
    if expiry < as_of:
        return "expired"
    if expiry <= as_of + timedelta(days=due_soon_days):
        return "due_soon"
    return "current"


def days_until_lto_expiry(
    lto_expiry: Optional[str],
    today: Optional[date] = None,
) -> Optional[int]:
    """Return days until LTO expiry (negative if past), or None if missing/invalid."""
    if not lto_expiry or not str(lto_expiry).strip():
        return None
    try:
        expiry = date.fromisoformat(str(lto_expiry).strip())
    except ValueError:
        return None
    as_of = today or date.today()
    return (expiry - as_of).days


def _ensure_system_sequences_table(connection: sqlite3.Connection) -> None:
    """
    Store next values for system-generated serial numbers.

    Keys:
    - requisition_serial: next fuel request serial (e.g. 2827)
    - po_serial: next PO reference number when purchaser leaves PO Ref blank
    """
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS system_sequences (
            key TEXT PRIMARY KEY,
            next_value INTEGER NOT NULL
        );
        """
    )


def set_system_sequence(connection: sqlite3.Connection, key: str, next_value: int) -> None:
    """
    Set or replace the next value for a named sequence.

    The next call that consumes this sequence returns next_value as a string,
    then increments the stored counter.
    """
    connection.execute(
        """
        INSERT INTO system_sequences (key, next_value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET next_value = excluded.next_value
        """,
        (key, next_value),
    )


def _ensure_audit_log_table(connection: sqlite3.Connection) -> None:
    """Create append-only audit_log table if missing."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            actor_user_id INTEGER,
            actor_username TEXT,
            actor_role TEXT,
            actor_name TEXT,
            old_values TEXT,
            new_values TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_log_entity
        ON audit_log (entity_type, entity_id, created_at DESC);
        """
    )


def set_system_sequences(
    db_path: str,
    requisition_serial: int,
    po_serial: int,
) -> None:
    """Persist starting serial counters for requests and PO references."""
    try:
        with get_connection(db_path) as connection:
            set_system_sequence(connection, "requisition_serial", requisition_serial)
            set_system_sequence(connection, "po_serial", po_serial)
    except sqlite3.Error as error:
        message = f"Failed to set system sequences: {error}"
        raise RuntimeError(message) from error


def _consume_system_sequence(connection: sqlite3.Connection, key: str) -> Optional[str]:
    """
    Return the next sequence value and increment the counter.

    Returns:
        String value to assign, or None if the sequence key is not configured.
    """
    cursor = connection.execute(
        "SELECT next_value FROM system_sequences WHERE key = ?",
        (key,),
    )
    row = cursor.fetchone()
    if row is None:
        return None

    next_value = int(row[0])
    connection.execute(
        "UPDATE system_sequences SET next_value = ? WHERE key = ?",
        (next_value + 1, key),
    )
    return str(next_value)


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
            connection.execute("BEGIN;")
            connection.execute("DELETE FROM requisitions;")
            connection.execute("DELETE FROM vendor_fuel_prices;")
            try:
                connection.execute("DELETE FROM password_reset_tokens;")
            except sqlite3.OperationalError:
                pass
            try:
                connection.execute("DELETE FROM user_sessions;")
            except sqlite3.OperationalError:
                pass
            connection.commit()
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to delete transactional data: {error}") from error


def reset_transactions_and_sequences(
    db_path: str,
    requisition_serial: int,
    po_serial: int,
) -> None:
    """
    Clear sample/transactional data and set the next request and PO serial numbers.

    Args:
        db_path: SQLite database path.
        requisition_serial: Next serial_number for a new fuel request.
        po_serial: Next po_reference when PO Ref is left blank on generate.
    """
    try:
        with get_connection(db_path) as connection:
            connection.execute("BEGIN;")
            connection.execute("DELETE FROM requisitions;")
            connection.execute("DELETE FROM vendor_fuel_prices;")
            try:
                connection.execute("DELETE FROM password_reset_tokens;")
            except sqlite3.OperationalError:
                pass
            try:
                connection.execute("DELETE FROM user_sessions;")
            except sqlite3.OperationalError:
                pass
            _ensure_system_sequences_table(connection)
            set_system_sequence(connection, "requisition_serial", requisition_serial)
            set_system_sequence(connection, "po_serial", po_serial)
            connection.commit()
    except sqlite3.Error as error:
        message = f"Failed to reset transactions and sequences: {error}"
        raise RuntimeError(message) from error


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
        "po_signatory": "TEXT",
        "actual_quantity": "REAL",
        "actual_unit_price": "REAL",
        "receipt_number": "TEXT",
        "received_date": "TEXT",
        "requestor_name": "TEXT",
        "cancel_reason": "TEXT",
        "cancelled_by": "TEXT",
        "released_date": "TEXT",
        "released_by": "TEXT",
        "release_remarks": "TEXT",
        "receiving_remarks": "TEXT",
        "settlement_type": "TEXT",
        "cc_card_reference": "TEXT",
        "cc_statement_reference": "TEXT",
        "cc_reconcile_report_no": "TEXT",
        "cc_reconciled_at": "TEXT",
        "cc_reconciled_by": "TEXT",
        "po_created_at": "TEXT",
    }
    cursor = connection.execute("PRAGMA table_info(requisitions);")
    existing = {row[1] for row in cursor.fetchall()}
    for column_name, column_type in required.items():
        if column_name not in existing:
            connection.execute(
                f"ALTER TABLE requisitions ADD COLUMN {column_name} {column_type};"
            )


SETTLEMENT_VENDOR_INVOICE = "vendor_invoice"
SETTLEMENT_CREDIT_CARD = "credit_card"
LEGACY_CC_VIA_PO_NOTE = "[Legacy CC via PO]"

DEFAULT_COMPANY_SEEDS: List[Tuple[str, str]] = [
    ("MTEI", "MTEI"),
    ("DSRDC", "DSRDC"),
    ("DIC", "DIC"),
    ("GCEIC", "GCEIC"),
    ("MTEI Trucking", "MTEI Trucking"),
]


def normalize_request_serial(value: Optional[str]) -> str:
    """
    Normalize a fuel request serial number to 5-digit zero-padded text.

    Accepts values like 2827, "02827", or "Request 2827".
    """
    cleaned = "".join(ch for ch in str(value or "").strip() if ch.isdigit())
    if not cleaned:
        return ""
    return f"{int(cleaned):05d}"


def normalize_settlement_type(value: Optional[str]) -> str:
    """Return a valid settlement type; default vendor invoice for legacy rows."""
    cleaned = (value or "").strip().lower()
    if cleaned == SETTLEMENT_CREDIT_CARD:
        return SETTLEMENT_CREDIT_CARD
    return SETTLEMENT_VENDOR_INVOICE


def _requisition_list_select() -> str:
    """Shared SELECT columns for requisition list queries."""
    return """
                SELECT
                    r.id,
                    r.serial_number,
                    r.quantity,
                    r.unit,
                    r.unit_price,
                    r.total_price,
                    r.actual_quantity,
                    r.actual_unit_price,
                    r.receipt_number,
                    r.received_date,
                    r.released_date,
                    r.released_by,
                    r.release_remarks,
                    r.receiving_remarks,
                    r.status,
                    r.notes,
                    r.po_reference,
                    r.invoice_number,
                    r.fuel_type,
                    r.settlement_type,
                    r.cc_card_reference,
                    r.cc_statement_reference,
                    r.cc_reconcile_report_no,
                    r.cc_reconciled_at,
                    r.cc_reconciled_by,
                    r.created_at,
                    r.po_created_at,
                    r.updated_at,
                    r.requester_id,
                    r.requestor_name,
                    r.prepared_by,
                    r.approved_by,
                    r.po_signatory,
                    COALESCE(NULLIF(TRIM(r.requestor_name), ''), u.username) AS requester_name,
                    r.vehicle_id,
                    c.plate_number,
                    c.model,
                    c.company,
                    r.vendor_id,
                    v.name AS vendor_name,
                    v.address AS vendor_address
    """


def list_requisitions_filtered(
    db_path: str,
    statuses: List[str],
    settlement_type: Optional[str] = None,
    cc_unreconciled_only: bool = False,
    company: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List active requisitions with optional settlement and CC reconciliation filters.

    Args:
        db_path: SQLite database path.
        statuses: Status values to include.
        settlement_type: When set, filter by normalized settlement type.
        cc_unreconciled_only: When True, only paid_cc rows without reconciliation.
        company: When set, filter by vehicle company (encoder scope).

    Returns:
        Matching requisition rows ordered oldest first for queue views.
    """
    if not statuses:
        return []
    placeholders = ",".join("?" for _ in statuses)
    where_parts = [f"r.is_active = 1 AND r.status IN ({placeholders})"]
    params: List[Any] = list(statuses)
    if settlement_type is not None:
        where_parts.append(
            "COALESCE(NULLIF(TRIM(r.settlement_type), ''), 'vendor_invoice') = ?"
        )
        params.append(normalize_settlement_type(settlement_type))
    if cc_unreconciled_only:
        where_parts.append("r.status = 'paid_cc' AND r.cc_reconciled_at IS NULL")
    if company:
        where_parts.append("c.company = ?")
        params.append(company.strip())
    where_sql = " AND ".join(where_parts)
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                f"""
                {_requisition_list_select()}
                FROM requisitions r
                INNER JOIN users u ON u.id = r.requester_id
                INNER JOIN cars c ON c.id = r.vehicle_id
                LEFT JOIN vendors v ON v.id = r.vendor_id
                WHERE {where_sql}
                ORDER BY r.created_at ASC
                """,
                params,
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to list filtered requisitions: {error}"
        raise RuntimeError(message) from error


def count_requisitions_filtered(
    db_path: str,
    statuses: List[str],
    settlement_type: Optional[str] = None,
    cc_unreconciled_only: bool = False,
    company: Optional[str] = None,
) -> int:
    """Count requisitions matching list_requisitions_filtered criteria."""
    if not statuses:
        return 0
    placeholders = ",".join("?" for _ in statuses)
    where_parts = [f"r.is_active = 1 AND r.status IN ({placeholders})"]
    params: List[Any] = list(statuses)
    if settlement_type is not None:
        where_parts.append(
            "COALESCE(NULLIF(TRIM(r.settlement_type), ''), 'vendor_invoice') = ?"
        )
        params.append(normalize_settlement_type(settlement_type))
    if cc_unreconciled_only:
        where_parts.append("r.status = 'paid_cc' AND r.cc_reconciled_at IS NULL")
    if company:
        where_parts.append(
            "EXISTS (SELECT 1 FROM cars c WHERE c.id = r.vehicle_id AND c.company = ?)"
        )
        params.append(company.strip())
    where_sql = " AND ".join(where_parts)
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                f"SELECT COUNT(*) FROM requisitions r WHERE {where_sql}",
                params,
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0
    except sqlite3.Error as error:
        message = f"Failed to count filtered requisitions: {error}"
        raise RuntimeError(message) from error


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
                SELECT id, username, hashed_password, role, is_active, full_name, email, company, permissions
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
                SELECT id, username, hashed_password, role, is_active, full_name, email, company, permissions
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


def create_user_session(
    db_path: str,
    user_id: int,
    ip_address: Optional[str] = None,
) -> str:
    """
    Create a session for the user; returns the raw token to store in a cookie.

    Sessions expire at workday end or after SESSION_IDLE_MINUTES without API activity.

    Args:
        db_path: Database path.
        user_id: User ID.
        ip_address: Client IP captured at login.

    Returns:
        Raw token string (store in cookie; pass to get_user_id_from_session / delete_user_session).
    """
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = _get_local_timestamp()
    expires_at = workday_session_expires_at()
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                INSERT INTO user_sessions (
                    token_hash, user_id, expires_at, created_at, last_seen_at, ip_address
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (token_hash, user_id, expires_at, now, now, ip_address),
            )
        return token
    except sqlite3.Error as error:
        message = f"Failed to create session: {error}"
        raise RuntimeError(message) from error


def touch_user_session(
    db_path: str,
    token: str,
    ip_address: Optional[str] = None,
) -> None:
    """
    Update last_seen_at (and IP when provided) for a valid session token.

    Args:
        db_path: Database path.
        token: Raw session token from cookie.
        ip_address: Current client IP from the request.
    """
    if not token or not token.strip():
        return
    token_hash = hashlib.sha256(token.strip().encode()).hexdigest()
    now = _get_local_timestamp()
    ip_value = (ip_address or "").strip() or None
    try:
        with get_connection(db_path) as connection:
            if ip_value:
                connection.execute(
                    """
                    UPDATE user_sessions
                    SET last_seen_at = ?, ip_address = ?
                    WHERE token_hash = ? AND expires_at > ?
                    """,
                    (now, ip_value, token_hash, now),
                )
            else:
                connection.execute(
                    """
                    UPDATE user_sessions
                    SET last_seen_at = ?
                    WHERE token_hash = ? AND expires_at > ?
                    """,
                    (now, token_hash, now),
                )
    except sqlite3.Error:
        pass


def list_active_user_sessions(
    db_path: str,
    idle_minutes: int = 15,
) -> List[Dict[str, Any]]:
    """
    List non-expired sessions with user profile fields for presence tracking.

    Args:
        db_path: Database path.
        idle_minutes: Minutes of inactivity before a session is not "online".

    Returns:
        Flat list of session rows (caller may collapse by user_id).
    """
    now = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT
                    s.user_id,
                    u.username,
                    u.full_name,
                    u.role,
                    s.created_at,
                    s.last_seen_at,
                    s.ip_address
                FROM user_sessions s
                INNER JOIN users u ON u.id = s.user_id
                WHERE s.expires_at > ?
                  AND u.is_active = 1
                ORDER BY s.last_seen_at DESC
                """,
                (now,),
            )
            rows = []
            for row in cursor.fetchall():
                last_seen = row["last_seen_at"] or row["created_at"] or ""
                rows.append(
                    {
                        "user_id": int(row["user_id"]),
                        "username": row["username"],
                        "full_name": row["full_name"],
                        "role": row["role"],
                        "login_at": row["created_at"] or "",
                        "last_seen_at": last_seen,
                        "ip_address": row["ip_address"],
                        "is_online": _is_recent_activity(last_seen, idle_minutes),
                    }
                )
            return rows
    except sqlite3.Error as error:
        message = f"Failed to list active sessions: {error}"
        raise RuntimeError(message) from error


def _is_recent_activity(timestamp: str, idle_minutes: int) -> bool:
    """Return True if timestamp is within idle_minutes of now."""
    if not timestamp:
        return False
    try:
        seen_at = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return False
    return datetime.now() - seen_at <= timedelta(minutes=idle_minutes)


def get_user_id_from_session(db_path: str, token: str) -> Optional[int]:
    """
    Validate session token and return user_id if valid and not expired.

    Invalidates sessions idle longer than SESSION_IDLE_MINUTES or past expires_at.

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
                SELECT user_id, last_seen_at FROM user_sessions
                WHERE token_hash = ? AND expires_at > ?
                """,
                (token_hash, now),
            )
            row = cursor.fetchone()
            if not row:
                return None
            last_seen = row[1]
            if is_session_idle_expired(last_seen, SESSION_IDLE_MINUTES):
                connection.execute(
                    "DELETE FROM user_sessions WHERE token_hash = ?",
                    (token_hash,),
                )
                return None
            return int(row[0])
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

    Uses system_sequences.requisition_serial when configured; otherwise falls back
    to MAX(serial_number) + 1 with 5-digit zero padding.
    """
    sequenced = _consume_system_sequence(connection, "requisition_serial")
    if sequenced is not None:
        return sequenced

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


def _get_next_po_reference(connection: sqlite3.Connection) -> str:
    """
    Generate the next PO reference when the purchaser leaves PO Ref blank.

    Uses system_sequences.po_serial when configured; otherwise returns empty string.
    """
    sequenced = _consume_system_sequence(connection, "po_serial")
    return sequenced or ""


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
    settlement_type: str = SETTLEMENT_VENDOR_INVOICE,
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
    settlement = normalize_settlement_type(settlement_type)
    try:
        with get_connection(db_path) as connection:
            serial_number = _get_next_serial_number(connection)
            cursor = connection.execute(
                """
                INSERT INTO requisitions (
                    serial_number, requester_id, vehicle_id, vendor_id, quantity, unit,
                    unit_price, total_price, status, notes, fuel_type, requestor_name,
                    settlement_type, is_active, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    serial_number,
                    requester_id,
                    vehicle_id,
                    vendor_id,
                    quantity,
                    unit,
                    unit_price,
                    total_price,
                    notes,
                    fuel_type,
                    (requestor_name or "").strip() or None,
                    settlement,
                    timestamp,
                    timestamp,
                ),
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
                    r.fuel_type,
                    r.settlement_type,
                    r.created_at,
                    r.po_created_at,
                    r.updated_at,
                    r.is_edited,
                    r.edited_by,
                    r.requester_id,
                    r.requestor_name,
                    r.vehicle_id,
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
                    r.po_created_at,
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


def fetch_requisition_by_serial(
    db_path: str, serial_number: str
) -> Optional[Dict[str, Any]]:
    """
    Fetch an active requisition by request serial number.

    Accepts padded or unpadded serials (e.g. 2827 or 02827).

    Args:
        db_path: SQLite database path.
        serial_number: Request serial number as shown in the UI.

    Returns:
        Requisition row dict or None if not found.
    """
    padded = normalize_request_serial(serial_number)
    if not padded:
        return None
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT r.id
                FROM requisitions r
                WHERE r.is_active = 1
                  AND (
                    r.serial_number = ?
                    OR CAST(r.serial_number AS INTEGER) = CAST(? AS INTEGER)
                  )
                LIMIT 1
                """,
                (padded, padded),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return fetch_requisition_by_id(db_path, int(row["id"]))
    except sqlite3.Error as error:
        message = f"Failed to fetch requisition serial {serial_number}: {error}"
        raise RuntimeError(message) from error


def mark_legacy_cc_via_po(db_path: str, requisition_id: int) -> Dict[str, Any]:
    """
    Tag a historical CC fill that was entered through the PO/vendor workflow.

    Sets settlement_type to credit_card and appends LEGACY_CC_VIA_PO_NOTE to notes.
    Reverts po_generated/released to approved so the request appears in CC Fills.
    Does not change status for received/billed rows (stay on the PO billing path).

    Args:
        db_path: SQLite database path.
        requisition_id: Target requisition ID.

    Returns:
        Dict with id, serial_number, status, changed flag, and message.

    Raises:
        RuntimeError: If requisition not found or already on the new CC path.
    """
    record = fetch_requisition_record(db_path, requisition_id)
    if not record:
        raise RuntimeError("Requisition not found.")

    status = (record.get("status") or "").lower()
    if status == "paid_cc":
        raise RuntimeError(
            "Request already uses the new CC fill path (paid_cc); no legacy tag needed."
        )

    current_settlement = normalize_settlement_type(record.get("settlement_type"))
    notes = (record.get("notes") or "").strip()
    already_tagged = LEGACY_CC_VIA_PO_NOTE in notes
    already_cc = current_settlement == SETTLEMENT_CREDIT_CARD
    revert_to_approved = status in {"po_generated", "released"}
    new_status = "approved" if revert_to_approved else status

    if already_cc and already_tagged and not revert_to_approved:
        return {
            "id": requisition_id,
            "serial_number": record.get("serial_number"),
            "status": status,
            "changed": False,
            "message": "Already tagged as legacy CC via PO.",
        }

    new_notes = notes
    if not already_tagged:
        new_notes = f"{notes} {LEGACY_CC_VIA_PO_NOTE}".strip()

    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            if revert_to_approved:
                connection.execute(
                    """
                    UPDATE requisitions
                    SET settlement_type = ?,
                        notes = ?,
                        status = 'approved',
                        po_created_at = NULL,
                        updated_at = ?
                    WHERE id = ? AND is_active = 1
                    """,
                    (SETTLEMENT_CREDIT_CARD, new_notes or None, timestamp, requisition_id),
                )
            else:
                connection.execute(
                    """
                    UPDATE requisitions
                    SET settlement_type = ?,
                        notes = ?,
                        updated_at = ?
                    WHERE id = ? AND is_active = 1
                    """,
                    (SETTLEMENT_CREDIT_CARD, new_notes or None, timestamp, requisition_id),
                )
    except sqlite3.Error as error:
        message = f"Failed to tag legacy CC requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error

    message = "Tagged as legacy CC via PO."
    if revert_to_approved:
        message = f"Moved to CC Fills (approved); was {status}."

    return {
        "id": requisition_id,
        "serial_number": record.get("serial_number"),
        "status": new_status,
        "changed": True,
        "message": message,
    }


def fetch_requisition_vehicle_company(
    db_path: str, requisition_id: int
) -> Optional[str]:
    """
    Return the vehicle company for a requisition (encoder scope checks).

    Args:
        db_path: SQLite database path.
        requisition_id: Requisition primary key.

    Returns:
        Company name or None if not found.
    """
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                SELECT c.company
                FROM requisitions r
                INNER JOIN cars c ON c.id = r.vehicle_id
                WHERE r.id = ? AND r.is_active = 1
                """,
                (requisition_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return (row[0] or "").strip() or None
    except sqlite3.Error as error:
        message = f"Failed to fetch company for requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def get_role_hierarchy_level(role: str) -> int:
    """
    Get the hierarchy level of a role (higher number = higher privilege).

    Role hierarchy: encoder (1) < approver (2) < purchaser (3) < accounting (4) < superuser (5)

    Args:
        role: User role string (case-insensitive).

    Returns:
        Integer hierarchy level (1-5).
    """
    role_lower = role.lower()
    if role_lower == "user":
        role_lower = "encoder"
    hierarchy = {
        "encoder": 1,
        "approver": 2,
        "purchaser": 3,
        "accounting": 4,
        "superuser": 5,
    }
    return hierarchy.get(role_lower, 1)


def can_user_edit_requisition(
    db_path: str,
    requisition_id: int,
    user_id: int,
    user_role: str = "",
    user: Optional[Dict[str, Any]] = None,
) -> tuple:
    """
    Check if a user can edit a requisition.

    Rules:
    - Users with fuel.requests.edit_any override all restrictions
    - Only creator (with edit_own) or higher level users can edit
    - Can only be edited once (if is_edited = 1, cannot edit again)
    - Cannot edit if status is not 'pending' (already in workflow)

    Args:
        db_path: File system path to the SQLite database.
        requisition_id: ID of the requisition to check.
        user_id: ID of the user attempting to edit.
        user_role: Legacy role string (fallback when user dict omitted).
        user: Optional public/DB user dict with permissions.

    Returns:
        Tuple of (can_edit: bool, error_message: Optional[str]).
    """
    from src.permissions import (
        user_can_edit_any_requisition,
        user_can_edit_own_requests,
    )

    req = fetch_requisition_by_id(db_path, requisition_id)
    if not req:
        return False, "Requisition not found."

    if user and user_can_edit_any_requisition(user):
        return True, None

    # Legacy superuser fallback
    if (user_role or "").lower() == "superuser":
        return True, None

    # Check if already edited
    if req.get("is_edited", 0) == 1:
        return False, "This requisition has already been edited and cannot be edited again."

    # Check if status allows editing (only pending can be edited)
    if req.get("status", "").lower() != "pending":
        return False, "Only pending requisitions can be edited."

    # Check if user is creator
    if req.get("requester_id") == user_id:
        if user and not user_can_edit_own_requests(user):
            return False, "You do not have permission to edit requests."
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
    settlement_type: Optional[str] = None,
    user: Optional[Dict[str, Any]] = None,
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
    can_edit, error_msg = can_user_edit_requisition(
        db_path, requisition_id, user_id, user_role, user=user
    )
    if not can_edit:
        raise RuntimeError(error_msg or "Edit not allowed.")

    from src.permissions import user_can_edit_any_requisition, user_is_purchasing_admin

    skip_edit_flag = False
    if user:
        skip_edit_flag = user_can_edit_any_requisition(user) or user_is_purchasing_admin(user)
    if (user_role or "").lower() == "superuser":
        skip_edit_flag = True

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
                "edited_by = ?",
                "updated_at = ?",
            ]
            # Override edits don't consume the one-time edit flag
            if not skip_edit_flag:
                updates.append("is_edited = 1")
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
            if settlement_type is not None:
                updates.append("settlement_type = ?")
                params.insert(-1, normalize_settlement_type(settlement_type))
            connection.execute(
                f"UPDATE requisitions SET {', '.join(updates)} WHERE id = ? AND is_active = 1",
                params,
            )
    except sqlite3.Error as error:
        message = f"Failed to update requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


# Columns that the superuser admin-edit endpoint may set directly.
_ADMIN_EDITABLE_COLUMNS = {
    "status",
    "vehicle_id",
    "vendor_id",
    "quantity",
    "unit",
    "fuel_type",
    "unit_price",
    "po_reference",
    "notes",
    "requestor_name",
    "actual_unit_price",
    "actual_quantity",
    "receipt_number",
    "received_date",
    "released_date",
    "released_by",
    "release_remarks",
    "receiving_remarks",
    "invoice_number",
    "approved_by",
    "prepared_by",
    "po_signatory",
    "settlement_type",
    "cc_card_reference",
    "cc_statement_reference",
    "cc_reconcile_report_no",
    "cc_reconciled_at",
    "cc_reconciled_by",
    "cancel_reason",
    "cancelled_by",
}

_ADMIN_EDITABLE_STATUSES = {
    "pending",
    "approved",
    "po_generated",
    "released",
    "received",
    "billed",
    "paid_cc",
    "cancelled",
    "rejected",
}


def admin_update_requisition(
    db_path: str, requisition_id: int, fields: Dict[str, Any]
) -> None:
    """
    Update arbitrary requisition fields (superuser only, no status/edit restrictions).

    Recalculates total_price when price or quantity fields change.

    Args:
        db_path: Database path.
        requisition_id: Target requisition.
        fields: Dict of column→value to set (only allowed columns).

    Raises:
        RuntimeError: If requisition not found or DB error.
    """
    allowed = {k: v for k, v in fields.items() if k in _ADMIN_EDITABLE_COLUMNS}
    if not allowed:
        raise RuntimeError("No valid fields to update.")

    if "status" in allowed:
        status_val = (allowed["status"] or "").strip().lower()
        if status_val not in _ADMIN_EDITABLE_STATUSES:
            raise RuntimeError(f"Invalid status: {allowed['status']}")
        allowed["status"] = status_val

    if "settlement_type" in allowed:
        allowed["settlement_type"] = normalize_settlement_type(allowed.get("settlement_type"))

    timestamp = _get_local_timestamp()
    pre_po_statuses = {"pending", "approved", "cancelled", "rejected", "paid_cc"}

    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                "SELECT quantity, unit_price, actual_quantity, actual_unit_price, status, po_created_at "
                "FROM requisitions WHERE id = ? AND is_active = 1",
                (requisition_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("Requisition not found.")

            cur_qty, cur_price, cur_act_qty, cur_act_price, cur_status, cur_po_created = row

            if "status" in allowed:
                new_status = allowed["status"]
                if new_status in pre_po_statuses:
                    allowed["po_created_at"] = None
                elif new_status == "po_generated" and not cur_po_created:
                    allowed["po_created_at"] = timestamp

            # Merge current values with incoming changes for recalc
            new_qty = allowed.get("quantity", cur_qty)
            new_price = allowed.get("unit_price", cur_price)
            new_act_qty = allowed.get("actual_quantity", cur_act_qty)
            new_act_price = allowed.get("actual_unit_price", cur_act_price)

            # Recalculate total_price: prefer actual if available
            if new_act_qty and new_act_price and new_act_qty > 0 and new_act_price > 0:
                allowed["total_price"] = new_act_qty * new_act_price
            elif new_qty and new_price and new_qty > 0 and new_price > 0:
                allowed["total_price"] = new_qty * new_price

            allowed["updated_at"] = timestamp

            set_clause = ", ".join(f"{col} = ?" for col in allowed)
            params = list(allowed.values()) + [requisition_id]
            connection.execute(
                f"UPDATE requisitions SET {set_clause} WHERE id = ? AND is_active = 1",
                params,
            )
    except sqlite3.Error as error:
        message = f"Admin edit failed for requisition {requisition_id}: {error}"
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
                    r.po_created_at,
                    r.updated_at,
                    r.requester_id,
                    r.vehicle_id,
                    r.vendor_id,
                    r.fuel_type,
                    r.requestor_name,
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


def list_vehicle_requisition_history(
    db_path: str, vehicle_id: int, limit: int = 10
) -> List[Dict[str, Any]]:
    """
    List recent requisitions for a vehicle (all statuses), newest first.

    Args:
        db_path: File system path to the SQLite database.
        vehicle_id: Vehicle whose history is fetched.
        limit: Maximum rows to return (default 10).

    Returns:
        A list of requisition summary records for approval context.
    """
    safe_limit = max(1, min(int(limit), 50))
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
                    r.status,
                    r.fuel_type,
                    r.total_price,
                    r.created_at,
                    COALESCE(NULLIF(TRIM(r.requestor_name), ''), u.username) AS requestor_name,
                    v.name AS vendor_name
                FROM requisitions r
                INNER JOIN users u ON u.id = r.requester_id
                LEFT JOIN vendors v ON v.id = r.vendor_id
                WHERE r.vehicle_id = ? AND r.is_active = 1
                ORDER BY r.created_at DESC
                LIMIT ?
                """,
                (vehicle_id, safe_limit),
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to list vehicle requisition history: {error}"
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


MIN_CANCEL_REASON_LENGTH = 10
ADMIN_CANCEL_STATUSES = frozenset(
    {"pending", "approved", "po_generated", "released", "received"}
)


def cancel_approved_requisition(
    db_path: str,
    requisition_id: int,
    cancelled_by_user_id: int,
    reason: str,
) -> None:
    """
    Cancel an approved requisition before PO generation.

    Args:
        db_path: File system path to the SQLite database.
        requisition_id: Requisition to cancel.
        cancelled_by_user_id: User performing the cancellation.
        reason: Required explanation (anti-abuse; minimum length enforced).

    Raises:
        RuntimeError: If not cancellable or validation fails.
    """
    cleaned_reason = (reason or "").strip()
    if len(cleaned_reason) < MIN_CANCEL_REASON_LENGTH:
        raise RuntimeError(
            f"Cancel reason must be at least {MIN_CANCEL_REASON_LENGTH} characters."
        )

    req = fetch_requisition_by_id(db_path, requisition_id)
    if not req:
        raise RuntimeError("Requisition not found.")
    if (req.get("status") or "").lower() != "approved":
        raise RuntimeError("Only approved requests awaiting PO can be cancelled.")

    cancelled_by_name = fetch_full_name_by_id(db_path, cancelled_by_user_id)
    timestamp = _get_local_timestamp()

    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                UPDATE requisitions
                SET status = 'cancelled',
                    cancel_reason = ?,
                    cancelled_by = ?,
                    updated_at = ?
                WHERE id = ? AND is_active = 1 AND status = 'approved'
                """,
                (cleaned_reason, cancelled_by_name, timestamp, requisition_id),
            )
            if connection.total_changes == 0:
                raise RuntimeError(
                    "Request is no longer approved; refresh and try again."
                )
    except sqlite3.Error as error:
        message = f"Failed to cancel requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def admin_cancel_requisition(
    db_path: str,
    requisition_id: int,
    cancelled_by_user_id: int,
    reason: str,
) -> None:
    """
    Superuser cancel for Request through Received (not billed).

    Keeps po_reference, po_created_at, and receipt fields so a voided PO
    remains auditable.

    Args:
        db_path: File system path to the SQLite database.
        requisition_id: Requisition to cancel.
        cancelled_by_user_id: Superuser performing the cancellation.
        reason: Required explanation (minimum length enforced).

    Raises:
        RuntimeError: If not cancellable or validation fails.
    """
    cleaned_reason = (reason or "").strip()
    if len(cleaned_reason) < MIN_CANCEL_REASON_LENGTH:
        raise RuntimeError(
            f"Cancel reason must be at least {MIN_CANCEL_REASON_LENGTH} characters."
        )

    req = fetch_requisition_by_id(db_path, requisition_id)
    if not req:
        raise RuntimeError("Requisition not found.")
    current_status = (req.get("status") or "").lower()
    if current_status not in ADMIN_CANCEL_STATUSES:
        raise RuntimeError(
            "Only pending, approved, PO-generated, released, or received "
            "requests can be cancelled."
        )

    cancelled_by_name = fetch_full_name_by_id(db_path, cancelled_by_user_id)
    timestamp = _get_local_timestamp()
    allowed = tuple(ADMIN_CANCEL_STATUSES)

    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                UPDATE requisitions
                SET status = 'cancelled',
                    cancel_reason = ?,
                    cancelled_by = ?,
                    updated_at = ?
                WHERE id = ? AND is_active = 1
                  AND lower(status) IN (?, ?, ?, ?, ?)
                """,
                (
                    cleaned_reason,
                    cancelled_by_name,
                    timestamp,
                    requisition_id,
                    *allowed,
                ),
            )
            if connection.total_changes == 0:
                raise RuntimeError(
                    "Request is no longer cancellable; refresh and try again."
                )
    except sqlite3.Error as error:
        message = f"Failed to admin-cancel requisition {requisition_id}: {error}"
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
                    r.po_created_at,
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


def list_po_signatories(db_path: str) -> List[Dict[str, Any]]:
    """
    List active users who may sign purchase orders on the PDF.

    Users with purchasing.sign_po permission are eligible.

    Args:
        db_path: File system path to the SQLite database.

    Returns:
        User rows with id, username, full_name, and role ordered by display name.
    """
    from src.permissions import PURCHASING_SIGN_PO, user_has_permission

    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT id, username, role, full_name, permissions, is_active
                FROM users
                WHERE is_active = 1
                ORDER BY COALESCE(NULLIF(TRIM(full_name), ''), username)
                """
            )
            rows = [dict(row) for row in cursor.fetchall()]
        return [
            {
                "id": row["id"],
                "username": row["username"],
                "role": row["role"],
                "full_name": row.get("full_name"),
            }
            for row in rows
            if user_has_permission(row, PURCHASING_SIGN_PO)
        ]
    except sqlite3.Error as error:
        message = f"Failed to list PO signatories: {error}"
        raise RuntimeError(message) from error


def update_requisition_po(
    db_path: str,
    requisition_id: int,
    po_reference: str,
    unit_price: Optional[float] = None,
    prepared_by_user_id: Optional[int] = None,
    signatory_user_id: Optional[int] = None,
) -> None:
    """
    Mark a requisition as having a generated purchase order and set unit price.

    Args:
        db_path: File system path to the SQLite database.
        requisition_id: ID of the requisition to update.
        po_reference: Optional PO reference text.
        unit_price: Optional price per unit (set by purchaser).
        prepared_by_user_id: Optional user ID of who prepared the PO.
        signatory_user_id: User ID of the PO signatory (stored as po_signatory full name).
    """
    timestamp = _get_local_timestamp()
    prepared_by_full_name = None
    if prepared_by_user_id:
        prepared_by_full_name = fetch_full_name_by_id(db_path, prepared_by_user_id)

    if signatory_user_id:
        signatory_user = fetch_user_by_id(db_path, signatory_user_id)
        if not signatory_user or not signatory_user.get("is_active"):
            raise RuntimeError("Signatory not found or inactive.")
        from src.permissions import PURCHASING_SIGN_PO, user_has_permission

        if not user_has_permission(signatory_user, PURCHASING_SIGN_PO):
            raise RuntimeError("Selected user cannot sign purchase orders.")
        po_signatory_name = (
            (signatory_user.get("full_name") or signatory_user.get("username") or "").strip()
        )
        if not po_signatory_name:
            raise RuntimeError("Signatory has no display name.")
    else:
        po_signatory_name = None
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                "SELECT settlement_type, status FROM requisitions WHERE id = ? AND is_active = 1",
                (requisition_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise RuntimeError(f"Requisition {requisition_id} not found or inactive")
            settlement = normalize_settlement_type(row[0])
            if settlement == SETTLEMENT_CREDIT_CARD:
                raise RuntimeError(
                    "Credit card requests skip PO workflow. Record the CC fill instead."
                )
            if (row[1] or "").lower() != "approved":
                raise RuntimeError("Only approved requests can generate a PO.")

            po_reference = (po_reference or "").strip()
            if not po_reference:
                po_reference = _get_next_po_reference(connection)

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
                if po_signatory_name:
                    connection.execute(
                        """
                        UPDATE requisitions
                        SET status = 'po_generated',
                            po_reference = ?,
                            unit_price = ?,
                            total_price = ?,
                            prepared_by = ?,
                            po_signatory = ?,
                            po_created_at = ?,
                            updated_at = ?
                        WHERE id = ? AND is_active = 1
                        """,
                        (
                            po_reference,
                            unit_price,
                            total_price,
                            prepared_by_full_name,
                            po_signatory_name,
                            timestamp,
                            timestamp,
                            requisition_id,
                        ),
                    )
                else:
                    connection.execute(
                        """
                        UPDATE requisitions
                        SET status = 'po_generated',
                            po_reference = ?,
                            unit_price = ?,
                            total_price = ?,
                            prepared_by = ?,
                            po_created_at = ?,
                            updated_at = ?
                        WHERE id = ? AND is_active = 1
                        """,
                        (
                            po_reference,
                            unit_price,
                            total_price,
                            prepared_by_full_name,
                            timestamp,
                            timestamp,
                            requisition_id,
                        ),
                    )
            elif po_signatory_name:
                connection.execute(
                    """
                    UPDATE requisitions
                    SET status = 'po_generated',
                        po_reference = ?,
                        unit_price = ?,
                        total_price = ?,
                        po_signatory = ?,
                        po_created_at = ?,
                        updated_at = ?
                    WHERE id = ? AND is_active = 1
                    """,
                    (
                        po_reference,
                        unit_price,
                        total_price,
                        po_signatory_name,
                        timestamp,
                        timestamp,
                        requisition_id,
                    ),
                )
            else:
                connection.execute(
                    """
                    UPDATE requisitions
                    SET status = 'po_generated',
                        po_reference = ?,
                        unit_price = ?,
                        total_price = ?,
                        po_created_at = ?,
                        updated_at = ?
                    WHERE id = ? AND is_active = 1
                    """,
                    (po_reference, unit_price, total_price, timestamp, timestamp, requisition_id),
                )
    except sqlite3.Error as error:
        message = f"Failed to mark PO for requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def mark_po_released(
    db_path: str,
    requisition_id: int,
    released_by_user_id: int,
    released_date: str,
    remarks: str = "",
) -> None:
    """
    Mark a PO-generated requisition as released to the driver.

    Args:
        db_path: Database path.
        requisition_id: Requisition to release.
        released_by_user_id: User performing the release.
        released_date: Date PO was released (YYYY-MM-DD).
        remarks: Optional release notes.

    Raises:
        RuntimeError: If not releasable or validation fails.
    """
    if not (released_date or "").strip():
        raise RuntimeError("Release date is required.")

    req = fetch_requisition_by_id(db_path, requisition_id)
    if not req:
        raise RuntimeError("Requisition not found.")
    if (req.get("status") or "").lower() != "po_generated":
        raise RuntimeError("Only PO-generated requests can be released.")

    released_by_name = fetch_full_name_by_id(db_path, released_by_user_id)
    timestamp = _get_local_timestamp()
    cleaned_remarks = (remarks or "").strip() or None

    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                UPDATE requisitions
                SET status = 'released',
                    released_date = ?,
                    released_by = ?,
                    release_remarks = ?,
                    updated_at = ?
                WHERE id = ? AND is_active = 1 AND status = 'po_generated'
                """,
                (
                    released_date.strip(),
                    released_by_name,
                    cleaned_remarks,
                    timestamp,
                    requisition_id,
                ),
            )
            if connection.total_changes == 0:
                raise RuntimeError(
                    "Request is no longer PO-generated; refresh and try again."
                )
    except sqlite3.Error as error:
        message = f"Failed to release PO for requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def undo_po_release(db_path: str, requisition_id: int) -> None:
    """
    Revert a released PO back to po_generated (superuser only, not yet received).

    Args:
        db_path: Database path.
        requisition_id: Requisition to revert.

    Raises:
        RuntimeError: If not in released status or DB error.
    """
    req = fetch_requisition_by_id(db_path, requisition_id)
    if not req:
        raise RuntimeError("Requisition not found.")
    if (req.get("status") or "").lower() != "released":
        raise RuntimeError("Only released requests can be undone.")

    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                UPDATE requisitions
                SET status = 'po_generated',
                    released_date = NULL,
                    released_by = NULL,
                    release_remarks = NULL,
                    updated_at = ?
                WHERE id = ? AND is_active = 1 AND status = 'released'
                """,
                (timestamp, requisition_id),
            )
            if connection.total_changes == 0:
                raise RuntimeError("Request is no longer released; refresh and try again.")
    except sqlite3.Error as error:
        message = f"Failed to undo release for requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def save_requisition_receiving(
    db_path: str,
    requisition_id: int,
    received_date: str,
    actual_unit_price: float,
    actual_quantity: float,
    receipt_number: str,
    user_role: str = "",
    receiving_remarks: Optional[str] = None,
    user: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Save delivery/receipt details when marking received or editing before billed.

    Keeps PO unit_price unchanged; stores actual_unit_price and recalculates total_price.

    Args:
        db_path: Database path.
        requisition_id: Requisition ID.
        received_date: Delivery date (YYYY-MM-DD).
        actual_unit_price: Price per liter at delivery.
        actual_quantity: Liters delivered (decimals allowed).
        receipt_number: Vendor delivery receipt number.
        user_role: Legacy role string (fallback when user dict omitted).
        receiving_remarks: Optional remarks about the delivery/receipt.
        user: Optional public/DB user dict with permissions.

    Raises:
        RuntimeError: On validation failure or DB error.
    """
    receipt = (receipt_number or "").strip()
    if not receipt:
        raise RuntimeError("Receipt number is required.")
    if not (received_date or "").strip():
        raise RuntimeError("Received date is required.")
    if actual_unit_price <= 0:
        raise RuntimeError("Actual price must be greater than 0.")
    if actual_quantity <= 0:
        raise RuntimeError("Actual quantity must be greater than 0.")

    total_price = actual_quantity * actual_unit_price
    timestamp = _get_local_timestamp()
    remarks_value = (receiving_remarks or "").strip() or None

    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                "SELECT status FROM requisitions WHERE id = ? AND is_active = 1",
                (requisition_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("Requisition not found.")
            status = row[0]
            from src.permissions import user_is_encode_receipt_only, user_is_purchasing_admin

            is_admin_override = False
            is_encoder = False
            if user:
                is_admin_override = user_is_purchasing_admin(user)
                is_encoder = user_is_encode_receipt_only(user)
            else:
                is_admin_override = (user_role or "").lower() == "superuser"
                is_encoder = (user_role or "").lower() in {"encoder", "user"}
            if is_encoder:
                if status != "released":
                    raise RuntimeError(
                        "Encoder can only record receipt for released POs."
                    )
            elif not is_admin_override:
                if status == "billed":
                    raise RuntimeError("Cannot edit receiving after item is billed.")
                if status == "received":
                    pass
                elif status == "released":
                    pass
                else:
                    raise RuntimeError(
                        "PO must be released to the driver before recording receipt."
                    )
            else:
                if status == "billed":
                    raise RuntimeError("Cannot edit receiving after item is billed.")
                if status not in ("po_generated", "released", "received"):
                    raise RuntimeError(
                        "Receiving can only be recorded for PO-generated, released, or received items."
                    )

            new_status = "received"
            connection.execute(
                """
                UPDATE requisitions
                SET status = ?,
                    received_date = ?,
                    actual_unit_price = ?,
                    actual_quantity = ?,
                    receipt_number = ?,
                    receiving_remarks = ?,
                    total_price = ?,
                    updated_at = ?
                WHERE id = ? AND is_active = 1
                """,
                (
                    new_status,
                    received_date.strip(),
                    actual_unit_price,
                    actual_quantity,
                    receipt,
                    remarks_value,
                    total_price,
                    timestamp,
                    requisition_id,
                ),
            )
    except sqlite3.Error as error:
        message = f"Failed to save receiving for requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def update_approved_settlement_type(
    db_path: str,
    requisition_id: int,
    settlement_type: str,
) -> None:
    """
    Change payment method on an approved requisition (requestor path already set; purchaser may override).

    Args:
        db_path: Database path.
        requisition_id: Requisition to update.
        settlement_type: vendor_invoice or credit_card.

    Raises:
        RuntimeError: If not approved or DB error.
    """
    timestamp = _get_local_timestamp()
    settlement = normalize_settlement_type(settlement_type)
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                "SELECT status FROM requisitions WHERE id = ? AND is_active = 1",
                (requisition_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("Requisition not found.")
            if (row[0] or "").lower() != "approved":
                raise RuntimeError("Payment method can only be changed while approved.")
            connection.execute(
                """
                UPDATE requisitions
                SET settlement_type = ?, updated_at = ?
                WHERE id = ? AND is_active = 1 AND status = 'approved'
                """,
                (settlement, timestamp, requisition_id),
            )
    except sqlite3.Error as error:
        message = f"Failed to update settlement type for requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def record_cc_fill(
    db_path: str,
    requisition_id: int,
    fill_date: str,
    actual_unit_price: float,
    actual_quantity: float,
    receipt_number: str,
    cc_card_reference: str = "",
    settlement_type: Optional[str] = None,
) -> None:
    """
    Record a credit-card fill for an approved request (skips PO/release; terminal paid_cc).

    Args:
        db_path: Database path.
        requisition_id: Approved CC requisition ID.
        fill_date: Date of fill (YYYY-MM-DD).
        actual_unit_price: Price per liter at pump.
        actual_quantity: Liters delivered.
        receipt_number: Pump / vendor receipt reference.
        cc_card_reference: Optional card label or last four digits.
        settlement_type: Optional purchaser override to credit_card before recording.

    Raises:
        RuntimeError: On validation failure or DB error.
    """
    receipt = (receipt_number or "").strip()
    if not receipt:
        raise RuntimeError("Receipt number is required.")
    if not (fill_date or "").strip():
        raise RuntimeError("Fill date is required.")
    if actual_unit_price <= 0:
        raise RuntimeError("Actual price must be greater than 0.")
    if actual_quantity <= 0:
        raise RuntimeError("Actual quantity must be greater than 0.")

    total_price = actual_quantity * actual_unit_price
    timestamp = _get_local_timestamp()
    card_ref = (cc_card_reference or "").strip() or None

    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                SELECT status, settlement_type
                FROM requisitions WHERE id = ? AND is_active = 1
                """,
                (requisition_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("Requisition not found.")
            if (row[0] or "").lower() != "approved":
                raise RuntimeError("Only approved requests can record a CC fill.")
            current_settlement = normalize_settlement_type(row[1])
            if settlement_type is not None:
                current_settlement = normalize_settlement_type(settlement_type)
            if current_settlement != SETTLEMENT_CREDIT_CARD:
                raise RuntimeError(
                    "This request is not marked for credit card payment. "
                    "Change payment method to Credit card first."
                )
            connection.execute(
                """
                UPDATE requisitions
                SET status = 'paid_cc',
                    settlement_type = ?,
                    received_date = ?,
                    actual_unit_price = ?,
                    actual_quantity = ?,
                    receipt_number = ?,
                    cc_card_reference = ?,
                    total_price = ?,
                    updated_at = ?
                WHERE id = ? AND is_active = 1 AND status = 'approved'
                """,
                (
                    SETTLEMENT_CREDIT_CARD,
                    fill_date.strip(),
                    actual_unit_price,
                    actual_quantity,
                    receipt,
                    card_ref,
                    total_price,
                    timestamp,
                    requisition_id,
                ),
            )
            if connection.total_changes == 0:
                raise RuntimeError("Request is no longer approved; refresh and try again.")
    except sqlite3.Error as error:
        message = f"Failed to record CC fill for requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def _generate_cc_reconcile_report_no(connection: sqlite3.Connection) -> str:
    """
    Allocate a local-time report number as yyyymmddhhmmss (suffix if collision).

    Args:
        connection: Open SQLite connection.

    Returns:
        Unique report number string.
    """
    base = datetime.now().strftime("%Y%m%d%H%M%S")
    candidate = base
    suffix = 0
    while True:
        cursor = connection.execute(
            """
            SELECT 1 FROM requisitions
            WHERE cc_reconcile_report_no = ?
            LIMIT 1
            """,
            (candidate,),
        )
        if cursor.fetchone() is None:
            return candidate
        suffix += 1
        candidate = f"{base}-{suffix:02d}"


def mark_cc_reconciled(
    db_path: str,
    requisition_ids: List[int],
    statement_reference: str,
    reconciled_by: str,
    report_number: Optional[str] = None,
) -> str:
    """
    Mark paid_cc requisitions as reconciled against a card statement.

    Args:
        db_path: Database path.
        requisition_ids: IDs to reconcile.
        statement_reference: Optional card statement period or reference number.
        reconciled_by: Display name of accounting user.
        report_number: Optional pre-allocated report number; generated if omitted.

    Returns:
        The system report number applied to the batch (yyyymmddhhmmss).

    Raises:
        RuntimeError: If validation fails or rows are not eligible.
    """
    if not requisition_ids:
        raise RuntimeError("Select at least one item to reconcile.")
    statement_ref = (statement_reference or "").strip() or None
    actor = (reconciled_by or "").strip() or None
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            report_no = (report_number or "").strip() or _generate_cc_reconcile_report_no(
                connection
            )
            for req_id in requisition_ids:
                cursor = connection.execute(
                    """
                    SELECT status, cc_reconciled_at
                    FROM requisitions WHERE id = ? AND is_active = 1
                    """,
                    (req_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise RuntimeError(f"Requisition {req_id} not found.")
                if (row[0] or "").lower() != "paid_cc":
                    raise RuntimeError(
                        f"Request {req_id} is not a credit card fill awaiting reconciliation."
                    )
                if row[1]:
                    raise RuntimeError(f"Request {req_id} is already reconciled.")
                connection.execute(
                    """
                    UPDATE requisitions
                    SET cc_statement_reference = ?,
                        cc_reconcile_report_no = ?,
                        cc_reconciled_at = ?,
                        cc_reconciled_by = ?,
                        updated_at = ?
                    WHERE id = ? AND is_active = 1 AND status = 'paid_cc'
                    """,
                    (statement_ref, report_no, timestamp, actor, timestamp, req_id),
                )
            return report_no
    except sqlite3.Error as error:
        message = f"Failed to reconcile credit card fills: {error}"
        raise RuntimeError(message) from error


def update_requisition_received(
    db_path: str, requisition_id: int
) -> None:
    """
    Mark a requisition as received (legacy one-click; prefer save_requisition_receiving).

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


def update_billed_invoice_number(
    db_path: str, requisition_id: int, invoice_number: str
) -> None:
    """
    Change billing reference on a billed requisition (status stays billed).

    Args:
        db_path: Database path.
        requisition_id: Requisition ID.
        invoice_number: New vendor billing reference (non-empty).

    Raises:
        RuntimeError: If update fails or row is not billed.
    """
    invoice_num = (invoice_number or "").strip()
    if not invoice_num:
        raise RuntimeError("Billing reference is required.")
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                UPDATE requisitions
                SET invoice_number = ?,
                    updated_at = ?
                WHERE id = ? AND is_active = 1 AND status = 'billed'
                """,
                (invoice_num, timestamp, requisition_id),
            )
            if cursor.rowcount == 0:
                raise RuntimeError(
                    f"Requisition {requisition_id} is not billed or was not found."
                )
    except sqlite3.Error as error:
        message = f"Failed to update billing reference for requisition {requisition_id}: {error}"
        raise RuntimeError(message) from error


def unbill_requisition(db_path: str, requisition_id: int) -> None:
    """
    Remove a requisition from billing: status back to received, clear invoice.

    Args:
        db_path: Database path.
        requisition_id: Requisition ID.

    Raises:
        RuntimeError: If row is not billed or update fails.
    """
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                UPDATE requisitions
                SET status = 'received',
                    invoice_number = NULL,
                    updated_at = ?
                WHERE id = ? AND is_active = 1 AND status = 'billed'
                """,
                (timestamp, requisition_id),
            )
            if cursor.rowcount == 0:
                raise RuntimeError(
                    f"Requisition {requisition_id} is not billed or was not found."
                )
    except sqlite3.Error as error:
        message = f"Failed to unbill requisition {requisition_id}: {error}"
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
                {_requisition_list_select()}
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


def _ensure_companies_table(connection: sqlite3.Connection) -> None:
    """Create companies master table if missing."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        """
    )


def _seed_default_companies(connection: sqlite3.Connection) -> None:
    """Insert default companies when the table is empty."""
    cursor = connection.execute("SELECT COUNT(*) FROM companies")
    if cursor.fetchone()[0] > 0:
        return
    for code, name in DEFAULT_COMPANY_SEEDS:
        connection.execute(
            """
            INSERT INTO companies (code, name, is_active)
            VALUES (?, ?, 1)
            """,
            (code, name),
        )


def list_companies(db_path: str, active_only: bool = True) -> List[Dict[str, Any]]:
    """
    List company master records.

    Args:
        db_path: Database path.
        active_only: When True, return only active companies.

    Returns:
        Company rows ordered by name.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            where = "WHERE is_active = 1" if active_only else ""
            cursor = connection.execute(
                f"""
                SELECT id, code, name, is_active, created_at
                FROM companies
                {where}
                ORDER BY name
                """
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to list companies: {error}"
        raise RuntimeError(message) from error


def list_active_company_codes(db_path: str) -> List[str]:
    """Return active company codes for dropdowns (cars.company / users.company)."""
    return [row["code"] for row in list_companies(db_path, active_only=True)]


def fetch_company_by_id(db_path: str, company_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a company by primary key."""
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT id, code, name, is_active, created_at
                FROM companies
                WHERE id = ?
                """,
                (company_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as error:
        message = f"Failed to fetch company {company_id}: {error}"
        raise RuntimeError(message) from error


def fetch_company_by_code(db_path: str, code: str) -> Optional[Dict[str, Any]]:
    """Fetch a company by code (matches cars.company / users.company text)."""
    cleaned = (code or "").strip()
    if not cleaned:
        return None
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT id, code, name, is_active, created_at
                FROM companies
                WHERE code = ?
                """,
                (cleaned,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as error:
        message = f"Failed to fetch company code '{code}': {error}"
        raise RuntimeError(message) from error


def assert_company_assignable(
    db_path: str,
    code: str,
    previous_code: Optional[str] = None,
) -> str:
    """
    Validate a company code for assignment to a vehicle or encoder user.

    New assignments require an active company. Existing rows may keep an
    inactive company when the code is unchanged.

    Args:
        db_path: Database path.
        code: Company code to assign.
        previous_code: Prior company code on update (optional).

    Returns:
        Normalized company code.

    Raises:
        RuntimeError: If company is unknown or inactive for a new assignment.
    """
    cleaned = (code or "").strip()
    if not cleaned:
        raise RuntimeError("Company is required.")
    company = fetch_company_by_code(db_path, cleaned)
    if not company:
        raise RuntimeError(f"Unknown company: {cleaned}")
    previous = (previous_code or "").strip()
    if not company.get("is_active") and cleaned != previous:
        raise RuntimeError(
            f"Company '{cleaned}' is inactive. Select an active company for new assignments."
        )
    return cleaned


def create_company(db_path: str, code: str, name: str) -> int:
    """
    Create a new company master record.

    Args:
        db_path: Database path.
        code: Unique short code stored on vehicles/users.
        name: Display name.

    Returns:
        New company id.
    """
    company_code = (code or "").strip()
    company_name = (name or "").strip()
    if not company_code:
        raise RuntimeError("Company code is required.")
    if not company_name:
        raise RuntimeError("Company name is required.")
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO companies (code, name, is_active)
                VALUES (?, ?, 1)
                """,
                (company_code, company_name),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as error:
        message = f"Company code '{company_code}' already exists."
        raise RuntimeError(message) from error
    except sqlite3.Error as error:
        message = f"Failed to create company '{company_code}': {error}"
        raise RuntimeError(message) from error


def update_company(db_path: str, company_id: int, name: str) -> None:
    """
    Update company display name (code is immutable).

    Args:
        db_path: Database path.
        company_id: Company id.
        name: Updated display name.
    """
    company_name = (name or "").strip()
    if not company_name:
        raise RuntimeError("Company name is required.")
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                UPDATE companies
                SET name = ?
                WHERE id = ?
                """,
                (company_name, company_id),
            )
    except sqlite3.Error as error:
        message = f"Failed to update company {company_id}: {error}"
        raise RuntimeError(message) from error


def soft_delete_company(db_path: str, company_id: int) -> None:
    """Deactivate a company (existing vehicle/user links are preserved)."""
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                "UPDATE companies SET is_active = 0 WHERE id = ?",
                (company_id,),
            )
    except sqlite3.Error as error:
        message = f"Failed to deactivate company {company_id}: {error}"
        raise RuntimeError(message) from error


def reactivate_company(db_path: str, company_id: int) -> None:
    """Reactivate a deactivated company."""
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                "UPDATE companies SET is_active = 1 WHERE id = ?",
                (company_id,),
            )
    except sqlite3.Error as error:
        message = f"Failed to reactivate company {company_id}: {error}"
        raise RuntimeError(message) from error


def _ensure_service_centers_table(connection: sqlite3.Connection) -> None:
    """Create the service center master table if it is missing."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS service_centers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL DEFAULT '',
            contact_no TEXT NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_service_centers_name
        ON service_centers (name COLLATE NOCASE);
        """
    )


def list_service_centers(db_path: str, active_only: bool = False) -> List[Dict[str, Any]]:
    """
    List service center master records.

    Args:
        db_path: Database path.
        active_only: When True, return only active service centers.

    Returns:
        Service center rows ordered by name.
    """
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            query = """
                SELECT id, name, address, contact_no, is_active, created_at
                FROM service_centers
                ORDER BY name COLLATE NOCASE
                """
            if active_only:
                query = """
                    SELECT id, name, address, contact_no, is_active, created_at
                    FROM service_centers
                    WHERE is_active = 1
                    ORDER BY name COLLATE NOCASE
                    """
            cursor = connection.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        message = f"Failed to list service centers: {error}"
        raise RuntimeError(message) from error


def fetch_service_center_by_id(
    db_path: str,
    service_center_id: int,
) -> Optional[Dict[str, Any]]:
    """Fetch one service center by primary key."""
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT id, name, address, contact_no, is_active, created_at
                FROM service_centers
                WHERE id = ?
                """,
                (service_center_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as error:
        message = f"Failed to fetch service center {service_center_id}: {error}"
        raise RuntimeError(message) from error


def _clean_service_center_fields(
    name: str,
    address: str,
    contact_no: str,
) -> tuple[str, str, str]:
    """Normalize service center text fields and require a name."""
    cleaned_name = (name or "").strip()
    cleaned_address = (address or "").strip()
    cleaned_contact = (contact_no or "").strip()
    if not cleaned_name:
        raise RuntimeError("Service center name is required.")
    return cleaned_name, cleaned_address, cleaned_contact


def create_service_center(
    db_path: str,
    name: str,
    address: str = "",
    contact_no: str = "",
) -> int:
    """
    Create a service center master record.

    Args:
        db_path: Database path.
        name: Unique display name.
        address: Street or location text.
        contact_no: Phone or mobile number.

    Returns:
        New service center id.
    """
    cleaned_name, cleaned_address, cleaned_contact = _clean_service_center_fields(
        name, address, contact_no
    )
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO service_centers (name, address, contact_no, is_active)
                VALUES (?, ?, ?, 1)
                """,
                (cleaned_name, cleaned_address, cleaned_contact),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as error:
        message = f"A service center named '{cleaned_name}' already exists."
        raise RuntimeError(message) from error
    except sqlite3.Error as error:
        message = f"Failed to create service center '{cleaned_name}': {error}"
        raise RuntimeError(message) from error


def update_service_center(
    db_path: str,
    service_center_id: int,
    name: str,
    address: str = "",
    contact_no: str = "",
) -> None:
    """Update a service center's name, address, and contact number."""
    existing = fetch_service_center_by_id(db_path, service_center_id)
    if not existing:
        raise RuntimeError("Service center not found.")
    cleaned_name, cleaned_address, cleaned_contact = _clean_service_center_fields(
        name, address, contact_no
    )
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                UPDATE service_centers
                SET name = ?, address = ?, contact_no = ?
                WHERE id = ?
                """,
                (cleaned_name, cleaned_address, cleaned_contact, service_center_id),
            )
    except sqlite3.IntegrityError as error:
        message = f"A service center named '{cleaned_name}' already exists."
        raise RuntimeError(message) from error
    except sqlite3.Error as error:
        message = f"Failed to update service center {service_center_id}: {error}"
        raise RuntimeError(message) from error


def soft_delete_service_center(db_path: str, service_center_id: int) -> None:
    """Deactivate a service center. Master rows are never hard-deleted."""
    existing = fetch_service_center_by_id(db_path, service_center_id)
    if not existing:
        raise RuntimeError("Service center not found.")
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                "UPDATE service_centers SET is_active = 0 WHERE id = ?",
                (service_center_id,),
            )
    except sqlite3.Error as error:
        message = f"Failed to deactivate service center {service_center_id}: {error}"
        raise RuntimeError(message) from error


def reactivate_service_center(db_path: str, service_center_id: int) -> None:
    """Reactivate a deactivated service center."""
    existing = fetch_service_center_by_id(db_path, service_center_id)
    if not existing:
        raise RuntimeError("Service center not found.")
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                "UPDATE service_centers SET is_active = 1 WHERE id = ?",
                (service_center_id,),
            )
    except sqlite3.Error as error:
        message = f"Failed to reactivate service center {service_center_id}: {error}"
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
                    c.assigned_to,
                    c.registration_date,
                    c.lto_expiry,
                    c.is_company_owned,
                    v.name AS vendor_name,
                    c.is_active,
                    c.created_at
                FROM cars c
                LEFT JOIN vendors v ON v.id = c.vendor_id
                WHERE c.is_active = 1
                ORDER BY c.plate_number
                """
            )
            rows = []
            for row in cursor.fetchall():
                item = dict(row)
                item["is_company_owned"] = bool(item.get("is_company_owned"))
                item["expiration_date"] = item.get("lto_expiry")
                rows.append(item)
            return rows
    except sqlite3.Error as error:
        message = f"Failed to list cars: {error}"
        raise RuntimeError(message) from error


def upsert_car(
    db_path: str,
    plate_number: str,
    model: str,
    vendor_id: Optional[int] = None,
    fuel_type: Optional[str] = None,
    company: Optional[str] = None,
    assigned_to: Optional[str] = None,
    registration_date: Optional[str] = None,
    expiration_date: Optional[str] = None,
    is_company_owned: bool = False,
) -> int:
    """
    Insert a new car or reactivate/update an existing one by plate number.

    Plate numbers are validated (letters/digits/hyphen/space/& only), uppercased, and unique
    by identity key (spaces/hyphens ignored for matching).

    Args:
        db_path: File system path to the SQLite database.
        plate_number: Unique vehicle plate number.
        model: Vehicle model description.
        vendor_id: Optional linked vendor id.
        fuel_type: Optional fuel type (Diesel, Unleaded Gasoline, Premium Gasoline).
        company: Optional company name.
        assigned_to: Person assigned to the vehicle (required).
        registration_date: Optional registration date (YYYY-MM-DD); cleared if not company-owned.
        expiration_date: Optional LTO expiry (YYYY-MM-DD); cleared if not company-owned.
        is_company_owned: When True, vehicle is included in Registrations/Renewal tracking.

    Returns:
        The car id.

    Raises:
        RuntimeError: If assigned_to is missing, plate invalid, or DB operation fails.
    """
    assignee = (assigned_to or "").strip()
    if not assignee:
        raise RuntimeError("Assigned To is required.")

    owned = bool(is_company_owned)
    reg_date = _normalize_optional_iso_date(registration_date) if owned else None
    exp_date = _normalize_optional_iso_date(expiration_date) if owned else None
    owned_flag = 1 if owned else 0

    try:
        plate_number = normalize_plate_number(plate_number)
    except ValueError as error:
        raise RuntimeError(str(error)) from error

    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                "SELECT id, is_active, plate_number FROM cars"
            )
            for existing_id, _is_active, existing_plate in cursor.fetchall():
                if plate_identity_key(existing_plate) != plate_identity_key(plate_number):
                    continue
                car_id = int(existing_id)
                connection.execute(
                    """
                    UPDATE cars
                    SET plate_number = ?, model = ?, vendor_id = ?, fuel_type = ?, company = ?,
                        assigned_to = ?, registration_date = ?, lto_expiry = ?,
                        is_company_owned = ?, is_active = 1
                    WHERE id = ?
                    """,
                    (
                        plate_number,
                        model,
                        vendor_id,
                        fuel_type,
                        company,
                        assignee,
                        reg_date,
                        exp_date,
                        owned_flag,
                        car_id,
                    ),
                )
                return car_id

            cursor = connection.execute(
                """
                INSERT INTO cars (
                    plate_number, model, vendor_id, fuel_type, company, assigned_to,
                    registration_date, lto_expiry, is_company_owned, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    plate_number,
                    model,
                    vendor_id,
                    fuel_type,
                    company,
                    assignee,
                    reg_date,
                    exp_date,
                    owned_flag,
                ),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as error:
        message = f"Car plate '{plate_number}' already exists."
        raise RuntimeError(message) from error
    except sqlite3.Error as error:
        message = f"Failed to upsert car '{plate_number}': {error}"
        raise RuntimeError(message) from error


def update_car(
    db_path: str,
    car_id: int,
    plate_number: str,
    model: str,
    vendor_id: Optional[int] = None,
    fuel_type: Optional[str] = None,
    company: Optional[str] = None,
    assigned_to: Optional[str] = None,
    registration_date: Optional[str] = None,
    expiration_date: Optional[str] = None,
    is_company_owned: bool = False,
) -> None:
    """
    Update an existing car by ID.

    Plate numbers are validated (letters/digits/hyphen/space/& only), uppercased, and unique
    by identity key (spaces/hyphens ignored for matching).

    Args:
        db_path: File system path to the SQLite database.
        car_id: ID of the car to update.
        plate_number: Updated plate number.
        model: Updated vehicle model.
        vendor_id: Updated optional vendor ID.
        fuel_type: Updated optional fuel type (Diesel, Unleaded Gasoline, Premium Gasoline).
        company: Updated company name.
        assigned_to: Person assigned to the vehicle (required).
        registration_date: Optional registration date (YYYY-MM-DD); cleared if not company-owned.
        expiration_date: Optional LTO expiry (YYYY-MM-DD); cleared if not company-owned.
        is_company_owned: When True, vehicle is included in Registrations/Renewal tracking.

    Raises:
        RuntimeError: If assigned_to is missing, plate invalid, or DB operation fails.
    """
    assignee = (assigned_to or "").strip()
    if not assignee:
        raise RuntimeError("Assigned To is required.")

    owned = bool(is_company_owned)
    reg_date = _normalize_optional_iso_date(registration_date) if owned else None
    exp_date = _normalize_optional_iso_date(expiration_date) if owned else None
    owned_flag = 1 if owned else 0

    try:
        plate_number = normalize_plate_number(plate_number)
    except ValueError as error:
        raise RuntimeError(str(error)) from error

    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute("SELECT id, plate_number FROM cars")
            for other_id, existing_plate in cursor.fetchall():
                if int(other_id) == car_id:
                    continue
                if plate_identity_key(existing_plate) == plate_identity_key(plate_number):
                    raise RuntimeError(f"Car plate '{plate_number}' already exists.")

            connection.execute(
                """
                UPDATE cars
                SET plate_number = ?, model = ?, vendor_id = ?, fuel_type = ?,
                    company = ?, assigned_to = ?, registration_date = ?,
                    lto_expiry = ?, is_company_owned = ?
                WHERE id = ?
                """,
                (
                    plate_number,
                    model,
                    vendor_id,
                    fuel_type,
                    company,
                    assignee,
                    reg_date,
                    exp_date,
                    owned_flag,
                    car_id,
                ),
            )
    except RuntimeError:
        raise
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
                SELECT id, username, role, is_active, created_at, full_name, email, company, permissions
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
    role: str = "encoder",
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    company: Optional[str] = None,
    permissions: Optional[str] = None,
) -> int:
    """
    Create a new user.

    Args:
        db_path: File system path to the SQLite database.
        username: Unique username.
        hashed_password: Bcrypt-hashed password.
        role: User role (encoder, approver, purchaser, accounting, superuser).
        full_name: Full name of the user (required).
        email: Optional email (for password reset).
        company: Optional company scope for encoder accounts.
        permissions: Optional JSON array of explicit permission codes.

    Returns:
        The new user ID.
    """
    if not full_name or not full_name.strip():
        raise RuntimeError("Full name is required.")
    
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (username, hashed_password, role, is_active, full_name, email, company, permissions)
                VALUES (?, ?, ?, 1, ?, ?, ?, ?)
                """,
                (
                    username,
                    hashed_password,
                    role,
                    full_name.strip(),
                    (email or "").strip() or None,
                    (company or "").strip() or None,
                    (permissions or "").strip() or None,
                ),
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
    company: Optional[str] = None,
    permissions: Optional[str] = None,
) -> None:
    """
    Update user fields (username, role, password, full_name, email, or company).

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
            if company is not None:
                updates.append("company = ?")
                params.append((company or "").strip() or None)
            if permissions is not None:
                updates.append("permissions = ?")
                params.append((permissions or "").strip() or None)
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


def insert_audit_log(
    db_path: str,
    entity_type: str,
    entity_id: int,
    action: str,
    actor_user_id: Optional[int],
    actor_username: str,
    actor_role: str,
    actor_name: str,
    old_values_json: str,
    new_values_json: str,
    metadata_json: str,
) -> None:
    """
    Insert one immutable audit log row.

    Args:
        db_path: Database path.
        entity_type: Entity category.
        entity_id: Entity primary key.
        action: Action verb.
        actor_user_id: Acting user id (optional).
        actor_username: Acting username snapshot.
        actor_role: Acting role snapshot.
        actor_name: Acting display name snapshot.
        old_values_json: JSON string of previous values.
        new_values_json: JSON string of new values.
        metadata_json: JSON string of extra context.
    """
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                INSERT INTO audit_log (
                    entity_type, entity_id, action,
                    actor_user_id, actor_username, actor_role, actor_name,
                    old_values, new_values, metadata, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entity_type,
                    entity_id,
                    action,
                    actor_user_id,
                    actor_username,
                    actor_role,
                    actor_name,
                    old_values_json,
                    new_values_json,
                    metadata_json,
                    timestamp,
                ),
            )
    except sqlite3.Error as error:
        message = f"Failed to insert audit log: {error}"
        raise RuntimeError(message) from error


def list_audit_log(
    db_path: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    limit: int = 100,
    q: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List audit log entries newest first.

    Args:
        db_path: Database path.
        entity_type: Optional filter by entity type.
        entity_id: Optional filter by entity id.
        limit: Maximum rows (default 100).
        q: Optional search across request id, PO number, plate, and requestor name.

    Returns:
        Audit log rows as dicts with parsed JSON fields.
    """
    import json

    clauses = []
    params: List[Any] = []
    if entity_type:
        clauses.append("a.entity_type = ?")
        params.append(entity_type)
    if entity_id is not None:
        clauses.append("a.entity_id = ?")
        params.append(entity_id)
    needle = (q or "").strip().upper()
    if needle:
        like = f"%{needle}%"
        clauses.append(
            """
            (
                (
                    a.entity_type = 'requisition'
                    AND a.entity_id IN (
                        SELECT r.id
                        FROM requisitions r
                        LEFT JOIN cars c ON c.id = r.vehicle_id
                        WHERE UPPER(CAST(r.id AS TEXT)) LIKE ?
                           OR UPPER(COALESCE(r.serial_number, '')) LIKE ?
                           OR UPPER(COALESCE(r.po_reference, '')) LIKE ?
                           OR UPPER(COALESCE(c.plate_number, '')) LIKE ?
                           OR UPPER(COALESCE(r.requestor_name, '')) LIKE ?
                    )
                )
                OR (
                    a.entity_type = 'vehicle'
                    AND a.entity_id IN (
                        SELECT c.id
                        FROM cars c
                        WHERE UPPER(COALESCE(c.plate_number, '')) LIKE ?
                    )
                )
                OR UPPER(COALESCE(json_extract(a.new_values, '$.serial_number'), '')) LIKE ?
                OR UPPER(COALESCE(json_extract(a.old_values, '$.serial_number'), '')) LIKE ?
                OR UPPER(COALESCE(json_extract(a.new_values, '$.po_reference'), '')) LIKE ?
                OR UPPER(COALESCE(json_extract(a.old_values, '$.po_reference'), '')) LIKE ?
                OR UPPER(COALESCE(json_extract(a.new_values, '$.plate_number'), '')) LIKE ?
                OR UPPER(COALESCE(json_extract(a.old_values, '$.plate_number'), '')) LIKE ?
                OR UPPER(COALESCE(json_extract(a.new_values, '$.requestor_name'), '')) LIKE ?
                OR UPPER(COALESCE(json_extract(a.old_values, '$.requestor_name'), '')) LIKE ?
                OR (
                    a.entity_type = 'requisition'
                    AND UPPER(CAST(a.entity_id AS TEXT)) LIKE ?
                )
            )
            """
        )
        params.extend([like] * 15)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(max(1, min(limit, 500)))

    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                f"""
                SELECT
                    a.id,
                    a.entity_type,
                    a.entity_id,
                    a.action,
                    a.actor_user_id,
                    a.actor_username,
                    a.actor_role,
                    a.actor_name,
                    a.old_values,
                    a.new_values,
                    a.metadata,
                    a.created_at
                FROM audit_log a
                {where_sql}
                ORDER BY a.created_at DESC, a.id DESC
                LIMIT ?
                """,
                params,
            )
            rows = []
            for row in cursor.fetchall():
                item = dict(row)
                for key in ("old_values", "new_values", "metadata"):
                    raw = item.get(key)
                    if raw:
                        try:
                            item[key] = json.loads(raw)
                        except json.JSONDecodeError:
                            item[key] = {}
                    else:
                        item[key] = {}
                rows.append(item)
            return rows
    except sqlite3.Error as error:
        message = f"Failed to list audit log: {error}"
        raise RuntimeError(message) from error


def fetch_vendor_by_id(db_path: str, vendor_id: int) -> Optional[Dict[str, Any]]:
    """Fetch one vendor row by id (active or inactive)."""
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                "SELECT id, name, address, is_active, created_at FROM vendors WHERE id = ?",
                (vendor_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as error:
        message = f"Failed to fetch vendor {vendor_id}: {error}"
        raise RuntimeError(message) from error


def fetch_car_by_id(db_path: str, car_id: int) -> Optional[Dict[str, Any]]:
    """Fetch one vehicle row by id (active or inactive)."""
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT id, plate_number, model, vendor_id, fuel_type, company,
                       assigned_to, is_active, created_at,
                       registration_date, lto_expiry, is_company_owned,
                       or_number, cr_number, mv_file_no,
                       registration_remarks
                FROM cars WHERE id = ?
                """,
                (car_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            item["is_company_owned"] = bool(item.get("is_company_owned"))
            item["expiration_date"] = item.get("lto_expiry")
            return item
    except sqlite3.Error as error:
        message = f"Failed to fetch car {car_id}: {error}"
        raise RuntimeError(message) from error


def list_vehicle_registrations(db_path: str) -> List[Dict[str, Any]]:
    """
    List active company-owned vehicles with LTO / OR-CR fields and alert status.

    Non–company-owned vehicles are excluded (renewals are tracked only for owned fleet).

    Sort order: expired, due_soon, missing, current; then by expiry and plate.

    Args:
        db_path: File system path to the SQLite database.

    Returns:
        List of registration rows including alert_status and days_until_expiry.
    """
    status_rank = {"expired": 0, "due_soon": 1, "missing": 2, "current": 3}
    today = date.today()
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT
                    c.id,
                    c.plate_number,
                    c.model,
                    c.company,
                    c.assigned_to,
                    c.registration_date,
                    c.lto_expiry,
                    c.or_number,
                    c.cr_number,
                    c.mv_file_no,
                    c.registration_remarks,
                    c.is_company_owned
                FROM cars c
                WHERE c.is_active = 1
                  AND IFNULL(c.is_company_owned, 0) = 1
                ORDER BY c.plate_number
                """
            )
            rows: List[Dict[str, Any]] = []
            for row in cursor.fetchall():
                item = dict(row)
                item["is_company_owned"] = True
                item["expiration_date"] = item.get("lto_expiry")
                expiry = item.get("lto_expiry")
                item["alert_status"] = registration_alert_status(expiry, today=today)
                item["days_until_expiry"] = days_until_lto_expiry(expiry, today=today)
                rows.append(item)
            rows.sort(
                key=lambda r: (
                    status_rank.get(str(r.get("alert_status")), 99),
                    r.get("lto_expiry") or "9999-99-99",
                    r.get("plate_number") or "",
                )
            )
            return rows
    except sqlite3.Error as error:
        message = f"Failed to list vehicle registrations: {error}"
        raise RuntimeError(message) from error


def update_vehicle_registration(
    db_path: str,
    car_id: int,
    lto_expiry: Optional[str] = None,
    registration_date: Optional[str] = None,
    or_number: Optional[str] = None,
    cr_number: Optional[str] = None,
    mv_file_no: Optional[str] = None,
    registration_remarks: Optional[str] = None,
) -> None:
    """
    Update LTO / OR-CR registration fields for an active company-owned vehicle.

    Args:
        db_path: File system path to the SQLite database.
        car_id: Vehicle id to update.
        lto_expiry: Optional LTO registration expiry (YYYY-MM-DD).
        registration_date: Optional registration date (YYYY-MM-DD).
        or_number: Optional Official Receipt number.
        cr_number: Optional Certificate of Registration number.
        mv_file_no: Optional MV file number.
        registration_remarks: Optional free-text notes.

    Raises:
        RuntimeError: If the vehicle is missing/inactive/not company-owned or validation fails.
    """
    expiry = _normalize_optional_iso_date(lto_expiry)
    reg_date = _normalize_optional_iso_date(registration_date)
    or_val = _normalize_optional_text(or_number)
    cr_val = _normalize_optional_text(cr_number)
    mv_val = _normalize_optional_text(mv_file_no)
    remarks = _normalize_optional_text(registration_remarks)

    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                SELECT id, is_active, IFNULL(is_company_owned, 0)
                FROM cars WHERE id = ?
                """,
                (car_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(f"Vehicle id {car_id} not found.")
            if int(row[1]) != 1:
                raise RuntimeError(f"Vehicle id {car_id} is inactive.")
            if int(row[2]) != 1:
                raise RuntimeError(
                    "Only company-owned vehicles are tracked for registration renewals."
                )

            connection.execute(
                """
                UPDATE cars
                SET lto_expiry = ?,
                    registration_date = ?,
                    or_number = ?,
                    cr_number = ?,
                    mv_file_no = ?,
                    registration_remarks = ?
                WHERE id = ?
                """,
                (expiry, reg_date, or_val, cr_val, mv_val, remarks, car_id),
            )
    except RuntimeError:
        raise
    except sqlite3.Error as error:
        message = f"Failed to update registration for vehicle id {car_id}: {error}"
        raise RuntimeError(message) from error


# Days before the next PMS due date that count as "due soon".
PMS_DUE_SOON_DAYS = 30

PMS_JOB_TYPE = "pms"
PMS_STATUS_OPEN = "open"
PMS_STATUS_COMPLETED = "completed"
PMS_STATUS_CANCELLED = "cancelled"

PMS_REPAIR_TYPES = ("preventive_maintenance", "change_oil", "inspection")
PMS_TERMS = ("cash", "15_days", "30_days")
PMS_LINE_TYPES = ("parts", "lubricants", "services", "others")
PMS_LINE_UNITS = ("pcs", "liters", "lot", "job")

PMS_REPAIR_TYPE_LABELS = {
    "preventive_maintenance": "Preventive maintenance",
    "change_oil": "Change oil",
    "inspection": "Inspection",
}


def _ensure_pms_tables(connection: sqlite3.Connection) -> None:
    """
    Create PMS schedule and work-order tables if missing.

    interval_km and last_odometer_km are edited on the schedule form.
    Date alerts do not use them. odometer_km on a work order stores that job's reading.
    """
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS pms_schedules (
            vehicle_id INTEGER PRIMARY KEY,
            interval_months INTEGER,
            next_due_date TEXT,
            interval_km INTEGER,
            last_odometer_km INTEGER,
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (vehicle_id) REFERENCES cars (id)
        );
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS work_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            job_type TEXT NOT NULL DEFAULT 'pms',
            status TEXT NOT NULL DEFAULT 'open',
            description TEXT,
            shop_name TEXT,
            cost REAL,
            notes TEXT,
            opened_at TEXT NOT NULL,
            service_date TEXT,
            completed_at TEXT,
            completed_by_user_id INTEGER,
            odometer_km INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (vehicle_id) REFERENCES cars (id),
            FOREIGN KEY (completed_by_user_id) REFERENCES users (id)
        );
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_work_orders_one_open_pms
        ON work_orders (vehicle_id)
        WHERE job_type = 'pms' AND status = 'open';
        """
    )
    cursor = connection.execute("PRAGMA table_info(work_orders);")
    columns = {row[1] for row in cursor.fetchall()}
    for column_name, column_type in (
        ("transaction_no", "TEXT"),
        ("doc_date", "TEXT"),
        ("repair_type", "TEXT"),
        ("service_advisor", "TEXT"),
        ("technician", "TEXT"),
        ("terms", "TEXT"),
        ("previous_odometer", "INTEGER"),
        ("current_odometer", "INTEGER"),
        ("remarks", "TEXT"),
    ):
        if column_name in columns:
            continue
        connection.execute(
            f"ALTER TABLE work_orders ADD COLUMN {column_name} {column_type};"
        )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_work_orders_transaction_no
        ON work_orders (transaction_no)
        WHERE transaction_no IS NOT NULL AND TRIM(transaction_no) != '';
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_order_id INTEGER NOT NULL,
            line_no INTEGER NOT NULL,
            part_code TEXT,
            line_type TEXT NOT NULL,
            description TEXT NOT NULL,
            unit TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            discount REAL NOT NULL DEFAULT 0,
            total_amount REAL NOT NULL,
            FOREIGN KEY (work_order_id) REFERENCES work_orders (id)
        );
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_work_order_lines_number
        ON work_order_lines (work_order_id, line_no);
        """
    )


def add_calendar_months(value: date, months: int) -> date:
    """
    Add a positive number of calendar months, clamping the day to the month length.

    Args:
        value: Starting calendar date.
        months: Months to add (must be at least 1).

    Returns:
        The date that many months later.
    """
    if months < 1:
        raise RuntimeError("Interval months must be at least 1.")
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(value.day, last_day))


def pms_alert_status(
    next_due_date: Optional[str],
    today: Optional[date] = None,
    due_soon_days: int = PMS_DUE_SOON_DAYS,
) -> str:
    """
    Classify a PMS next-due date.

    Returns one of: missing, overdue, due_soon, current.
    """
    as_of = today or date.today()
    if not next_due_date or not str(next_due_date).strip():
        return "missing"
    try:
        due = date.fromisoformat(str(next_due_date).strip())
    except ValueError:
        return "missing"
    if due < as_of:
        return "overdue"
    if due <= as_of + timedelta(days=due_soon_days):
        return "due_soon"
    return "current"


def days_until_pms_due(
    next_due_date: Optional[str],
    today: Optional[date] = None,
) -> Optional[int]:
    """Return days until the PMS due date (negative if past), or None if missing."""
    if not next_due_date or not str(next_due_date).strip():
        return None
    try:
        due = date.fromisoformat(str(next_due_date).strip())
    except ValueError:
        return None
    as_of = today or date.today()
    return (due - as_of).days


def _normalize_optional_positive_int(value: Optional[int], label: str) -> Optional[int]:
    """Blank clears; a present value must be an integer of at least 1."""
    if value is None:
        return None
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"{label} must be a whole number.") from error
    if number < 1:
        raise RuntimeError(f"{label} must be at least 1.")
    return number


def _normalize_optional_cost(value: Optional[float]) -> Optional[float]:
    """Blank cost is allowed; a present cost must be zero or greater."""
    if value is None:
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError) as error:
        raise RuntimeError("Cost must be a number.") from error
    if amount < 0:
        raise RuntimeError("Cost cannot be negative.")
    return amount


def _require_pms_vehicle(connection: sqlite3.Connection, vehicle_id: int) -> None:
    """Raise if the vehicle is missing, inactive, or not company-owned."""
    cursor = connection.execute(
        """
        SELECT id, is_active, IFNULL(is_company_owned, 0)
        FROM cars WHERE id = ?
        """,
        (vehicle_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Vehicle id {vehicle_id} not found.")
    if int(row[1]) != 1:
        raise RuntimeError(f"Vehicle id {vehicle_id} is inactive.")
    if int(row[2]) != 1:
        raise RuntimeError("Only company-owned vehicles are tracked for PMS.")


def _pms_schedule_snapshot(connection: sqlite3.Connection, vehicle_id: int) -> Dict[str, Any]:
    """Return schedule fields for audit, or an empty snapshot when no row exists."""
    connection.row_factory = sqlite3.Row
    cursor = connection.execute(
        """
        SELECT vehicle_id, interval_months, next_due_date, interval_km, last_odometer_km
        FROM pms_schedules
        WHERE vehicle_id = ?
        """,
        (vehicle_id,),
    )
    row = cursor.fetchone()
    if not row:
        return {
            "vehicle_id": vehicle_id,
            "interval_months": None,
            "next_due_date": None,
            "interval_km": None,
            "last_odometer_km": None,
        }
    return dict(row)


def list_pms_vehicles(db_path: str) -> List[Dict[str, Any]]:
    """
    List active company-owned vehicles with PMS due status and any open job.

    Sort order: overdue, due_soon, missing, current; then next due date and plate.

    Args:
        db_path: SQLite database path.

    Returns:
        Vehicle rows with alert_status, days_until_due, and open work-order fields.
    """
    status_rank = {"overdue": 0, "due_soon": 1, "missing": 2, "current": 3}
    today = date.today()
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT
                    c.id,
                    c.plate_number,
                    c.model,
                    c.company,
                    c.assigned_to,
                    s.interval_months,
                    s.next_due_date,
                    s.interval_km,
                    s.last_odometer_km,
                    (
                        SELECT w.service_date
                        FROM work_orders w
                        WHERE w.vehicle_id = c.id
                          AND w.job_type = ?
                          AND w.status = ?
                        ORDER BY w.service_date DESC, w.id DESC
                        LIMIT 1
                    ) AS last_service_date,
                    (
                        SELECT w.id
                        FROM work_orders w
                        WHERE w.vehicle_id = c.id
                          AND w.job_type = ?
                          AND w.status = ?
                        LIMIT 1
                    ) AS open_work_order_id,
                    (
                        SELECT COALESCE(
                            NULLIF(TRIM(w.transaction_no), ''),
                            NULLIF(TRIM(w.description), ''),
                            w.repair_type
                        )
                        FROM work_orders w
                        WHERE w.vehicle_id = c.id
                          AND w.job_type = ?
                          AND w.status = ?
                        LIMIT 1
                    ) AS open_work_order_description,
                    (
                        SELECT w.current_odometer
                        FROM work_orders w
                        WHERE w.vehicle_id = c.id
                          AND w.job_type = ?
                          AND w.status = ?
                          AND w.current_odometer IS NOT NULL
                        ORDER BY w.service_date DESC, w.id DESC
                        LIMIT 1
                    ) AS previous_odometer
                FROM cars c
                LEFT JOIN pms_schedules s ON s.vehicle_id = c.id
                WHERE c.is_active = 1
                  AND IFNULL(c.is_company_owned, 0) = 1
                ORDER BY c.plate_number
                """,
                (
                    PMS_JOB_TYPE,
                    PMS_STATUS_COMPLETED,
                    PMS_JOB_TYPE,
                    PMS_STATUS_OPEN,
                    PMS_JOB_TYPE,
                    PMS_STATUS_OPEN,
                    PMS_JOB_TYPE,
                    PMS_STATUS_COMPLETED,
                ),
            )
            rows: List[Dict[str, Any]] = []
            for row in cursor.fetchall():
                item = dict(row)
                due = item.get("next_due_date")
                item["alert_status"] = pms_alert_status(due, today=today)
                item["days_until_due"] = days_until_pms_due(due, today=today)
                rows.append(item)
            rows.sort(
                key=lambda r: (
                    status_rank.get(str(r.get("alert_status")), 99),
                    r.get("next_due_date") or "9999-99-99",
                    r.get("plate_number") or "",
                )
            )
            return rows
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to list PMS vehicles: {error}") from error


def update_pms_schedule(
    db_path: str,
    vehicle_id: int,
    interval_months: Optional[int],
    next_due_date: Optional[str],
    interval_km: Optional[int] = None,
    last_odometer_km: Optional[int] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Set or clear the date and odometer schedule for one vehicle.

    Blank values clear that field. Due status still follows the next due date.

    Args:
        db_path: SQLite database path.
        vehicle_id: Company-owned vehicle id.
        interval_months: Months between services, or None to clear.
        next_due_date: Next due date (YYYY-MM-DD), or None to clear.
        interval_km: Kilometers between services, or None to clear.
        last_odometer_km: Last odometer reading, or None to clear.

    Returns:
        Before and after schedule snapshots.

    Raises:
        RuntimeError: If the vehicle is not tracked or the values are invalid.
    """
    months = _normalize_optional_positive_int(interval_months, "Interval months")
    due = _normalize_optional_iso_date(next_due_date, "Next due date")
    kilometers = _normalize_optional_positive_int(interval_km, "Interval kilometers")
    odometer = _normalize_optional_odometer(last_odometer_km, "Last odometer")
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            _require_pms_vehicle(connection, vehicle_id)
            before = _pms_schedule_snapshot(connection, vehicle_id)
            connection.execute(
                """
                INSERT INTO pms_schedules (
                    vehicle_id, interval_months, next_due_date,
                    interval_km, last_odometer_km, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(vehicle_id) DO UPDATE SET
                    interval_months = excluded.interval_months,
                    next_due_date = excluded.next_due_date,
                    interval_km = excluded.interval_km,
                    last_odometer_km = excluded.last_odometer_km,
                    updated_at = excluded.updated_at
                """,
                (vehicle_id, months, due, kilometers, odometer, timestamp),
            )
            after = _pms_schedule_snapshot(connection, vehicle_id)
            return before, after
    except RuntimeError:
        raise
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to update PMS schedule for vehicle {vehicle_id}: {error}") from error


def _work_order_select() -> str:
    """Shared SELECT for PMS work-order rows with vehicle and completer name."""
    return """
        SELECT
            w.id,
            w.vehicle_id,
            w.job_type,
            w.status,
            w.description,
            w.shop_name,
            w.cost,
            w.notes,
            w.remarks,
            w.opened_at,
            w.service_date,
            w.doc_date,
            w.transaction_no,
            w.repair_type,
            w.service_advisor,
            w.technician,
            w.terms,
            w.previous_odometer,
            w.current_odometer,
            w.completed_at,
            w.completed_by_user_id,
            w.odometer_km,
            c.plate_number,
            c.model,
            c.company,
            c.assigned_to,
            COALESCE(NULLIF(TRIM(u.full_name), ''), u.username) AS completed_by_name
        FROM work_orders w
        INNER JOIN cars c ON c.id = w.vehicle_id
        LEFT JOIN users u ON u.id = w.completed_by_user_id
    """


def _load_work_order_lines(
    connection: sqlite3.Connection, work_order_ids: List[int]
) -> Dict[int, List[Dict[str, Any]]]:
    """Return line rows grouped by work order id, in line number order."""
    if not work_order_ids:
        return {}
    placeholders = ",".join("?" for _ in work_order_ids)
    connection.row_factory = sqlite3.Row
    cursor = connection.execute(
        f"""
        SELECT id, work_order_id, line_no, part_code, line_type, description,
               unit, quantity, unit_price, discount, total_amount
        FROM work_order_lines
        WHERE work_order_id IN ({placeholders})
        ORDER BY line_no, id
        """,
        work_order_ids,
    )
    grouped: Dict[int, List[Dict[str, Any]]] = {}
    for row in cursor.fetchall():
        item = dict(row)
        grouped.setdefault(int(item["work_order_id"]), []).append(item)
    return grouped


def _attach_work_order_lines(
    connection: sqlite3.Connection, orders: List[Dict[str, Any]]
) -> None:
    """Add a lines list to each work-order dict."""
    grouped = _load_work_order_lines(connection, [int(order["id"]) for order in orders])
    for order in orders:
        order["lines"] = grouped.get(int(order["id"]), [])


def _latest_completed_odometer(connection: sqlite3.Connection, vehicle_id: int) -> Optional[int]:
    """Return the current odometer from the latest completed PMS job, if any."""
    cursor = connection.execute(
        """
        SELECT current_odometer
        FROM work_orders
        WHERE vehicle_id = ?
          AND job_type = ?
          AND status = ?
          AND current_odometer IS NOT NULL
        ORDER BY service_date DESC, id DESC
        LIMIT 1
        """,
        (vehicle_id, PMS_JOB_TYPE, PMS_STATUS_COMPLETED),
    )
    row = cursor.fetchone()
    if not row or row[0] is None:
        return None
    return int(row[0])


def _normalize_optional_odometer(value: Optional[int], label: str) -> Optional[int]:
    """Blank clears. A present reading must be a whole number of zero or greater."""
    if value is None or value == "":
        return None
    try:
        if isinstance(value, float) and not value.is_integer():
            raise ValueError
        number = int(value)
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"{label} must be a whole number.") from error
    if number < 0:
        raise RuntimeError(f"{label} cannot be negative.")
    return number


def _normalize_choice(value: Optional[str], allowed: tuple, label: str) -> Optional[str]:
    """Blank clears. Any other value must be one of the allowed codes."""
    text = _normalize_optional_text(value)
    if text is None:
        return None
    if text not in allowed:
        raise RuntimeError(f"{label} is not recognized.")
    return text


def _prepare_pms_lines(lines: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], float]:
    """
    Validate line items and assign line numbers.

    Returns:
        Normalized lines and the job total.
    """
    prepared: List[Dict[str, Any]] = []
    job_total = 0.0
    for raw in lines:
        description = _normalize_optional_text(raw.get("description"))
        if not description:
            raise RuntimeError("Each line needs a description.")
        line_type = _normalize_choice(raw.get("line_type"), PMS_LINE_TYPES, "Line type")
        if not line_type:
            raise RuntimeError("Each line needs a type.")
        unit = _normalize_choice(raw.get("unit"), PMS_LINE_UNITS, "Unit")
        if not unit:
            raise RuntimeError("Each line needs a unit.")
        try:
            quantity = float(raw.get("quantity"))
            unit_price = float(raw.get("unit_price"))
            discount = float(raw.get("discount") or 0)
        except (TypeError, ValueError) as error:
            raise RuntimeError("Quantity, unit price, and discount must be numbers.") from error
        if quantity <= 0:
            raise RuntimeError("Quantity must be greater than zero.")
        if unit_price < 0:
            raise RuntimeError("Unit price cannot be negative.")
        if discount < 0:
            raise RuntimeError("Discount cannot be negative.")
        gross = round(quantity * unit_price, 2)
        discount = round(discount, 2)
        if discount > gross:
            raise RuntimeError("Discount cannot be greater than quantity times unit price.")
        total_amount = round(gross - discount, 2)
        job_total = round(job_total + total_amount, 2)
        prepared.append(
            {
                "line_no": len(prepared) + 1,
                "part_code": _normalize_optional_text(raw.get("part_code")),
                "line_type": line_type,
                "description": description,
                "unit": unit,
                "quantity": quantity,
                "unit_price": round(unit_price, 2),
                "discount": discount,
                "total_amount": total_amount,
            }
        )
    return prepared, job_total


def _prepare_pms_header(
    header: Dict[str, Any],
    lines: List[Dict[str, Any]],
    previous_odometer: Optional[int],
    strict: bool,
) -> Dict[str, Any]:
    """
    Normalize a PMS job header.

    Strict mode is completion: repair type, doc date, current odometer, and one line.
    """
    prepared_lines, job_total = _prepare_pms_lines(lines)
    repair_type = _normalize_choice(header.get("repair_type"), PMS_REPAIR_TYPES, "Repair type")
    doc_date = _normalize_optional_iso_date(header.get("doc_date"), "Doc. date")
    current = _normalize_optional_odometer(header.get("current_odometer"), "Current odometer")
    if strict:
        if not repair_type:
            raise RuntimeError("Repair type is required to complete the job.")
        if not doc_date:
            raise RuntimeError("Doc. date is required to complete the job.")
        if current is None:
            raise RuntimeError("Current odometer is required to complete the job.")
        if not prepared_lines:
            raise RuntimeError("Add at least one parts or service line to complete the job.")
    if current is not None and previous_odometer is not None and current <= previous_odometer:
        raise RuntimeError("Current odometer must be greater than the previous reading.")
    summary = ""
    if prepared_lines:
        summary = prepared_lines[0]["description"]
    elif repair_type:
        summary = PMS_REPAIR_TYPE_LABELS.get(repair_type, repair_type)
    remarks = _normalize_optional_text(header.get("remarks"))
    return {
        "transaction_no": _normalize_optional_text(header.get("transaction_no")),
        "doc_date": doc_date,
        "repair_type": repair_type,
        "service_advisor": _normalize_optional_text(header.get("service_advisor")),
        "technician": _normalize_optional_text(header.get("technician")),
        "terms": _normalize_choice(header.get("terms"), PMS_TERMS, "Terms"),
        "shop_name": _normalize_optional_text(header.get("shop_name")),
        "remarks": remarks,
        "notes": remarks,
        "description": summary or "PMS job",
        "previous_odometer": previous_odometer,
        "current_odometer": current,
        "cost": job_total,
        "lines": prepared_lines,
    }


def _replace_work_order_lines(
    connection: sqlite3.Connection, work_order_id: int, lines: List[Dict[str, Any]]
) -> None:
    """Replace all lines on an open job."""
    connection.execute("DELETE FROM work_order_lines WHERE work_order_id = ?", (work_order_id,))
    for line in lines:
        connection.execute(
            """
            INSERT INTO work_order_lines (
                work_order_id, line_no, part_code, line_type, description, unit,
                quantity, unit_price, discount, total_amount
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                work_order_id,
                line["line_no"],
                line["part_code"],
                line["line_type"],
                line["description"],
                line["unit"],
                line["quantity"],
                line["unit_price"],
                line["discount"],
                line["total_amount"],
            ),
        )


def _raise_work_order_integrity(error: sqlite3.IntegrityError) -> None:
    """Turn unique-index failures into field messages."""
    message = str(error).lower()
    if "transaction" in message:
        raise RuntimeError("Transaction ID is already used.") from error
    raise RuntimeError("This vehicle already has an open PMS job.") from error


def fetch_work_order(db_path: str, work_order_id: int) -> Optional[Dict[str, Any]]:
    """Fetch one work order, or None if it does not exist."""
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                f"{_work_order_select()} WHERE w.id = ?",
                (work_order_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            _attach_work_order_lines(connection, [item])
            return item
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to fetch work order {work_order_id}: {error}") from error


def list_pms_work_order_history(db_path: str, vehicle_id: int) -> List[Dict[str, Any]]:
    """
    List completed and cancelled PMS jobs for one vehicle, newest service date first.

    Args:
        db_path: SQLite database path.
        vehicle_id: Vehicle id.

    Returns:
        Work-order rows excluding open jobs.
    """
    try:
        with get_connection(db_path) as connection:
            _require_pms_vehicle(connection, vehicle_id)
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                f"""
                {_work_order_select()}
                WHERE w.vehicle_id = ?
                  AND w.job_type = ?
                  AND w.status IN (?, ?)
                ORDER BY COALESCE(w.service_date, substr(w.opened_at, 1, 10)) DESC, w.id DESC
                """,
                (
                    vehicle_id,
                    PMS_JOB_TYPE,
                    PMS_STATUS_COMPLETED,
                    PMS_STATUS_CANCELLED,
                ),
            )
            orders = [dict(row) for row in cursor.fetchall()]
            _attach_work_order_lines(connection, orders)
            return orders
    except RuntimeError:
        raise
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to list PMS history for vehicle {vehicle_id}: {error}") from error


def _write_open_pms_job(
    connection: sqlite3.Connection,
    work_order_id: int,
    prepared: Dict[str, Any],
    timestamp: str,
) -> None:
    """Update header fields and replace lines on an open job."""
    connection.execute(
        """
        UPDATE work_orders
        SET description = ?,
            shop_name = ?,
            cost = ?,
            notes = ?,
            remarks = ?,
            doc_date = ?,
            transaction_no = ?,
            repair_type = ?,
            service_advisor = ?,
            technician = ?,
            terms = ?,
            previous_odometer = ?,
            current_odometer = ?,
            odometer_km = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            prepared["description"],
            prepared["shop_name"],
            prepared["cost"],
            prepared["notes"],
            prepared["remarks"],
            prepared["doc_date"],
            prepared["transaction_no"],
            prepared["repair_type"],
            prepared["service_advisor"],
            prepared["technician"],
            prepared["terms"],
            prepared["previous_odometer"],
            prepared["current_odometer"],
            prepared["current_odometer"],
            timestamp,
            work_order_id,
        ),
    )
    _replace_work_order_lines(connection, work_order_id, prepared["lines"])


def open_pms_work_order(
    db_path: str,
    vehicle_id: int,
    header: Dict[str, Any],
    lines: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Open one PMS work order for a vehicle.

    Header and lines may be incomplete. A second open PMS job is rejected.

    Args:
        db_path: SQLite database path.
        vehicle_id: Company-owned vehicle id.
        header: Repair, shop, odometer, and remarks fields.
        lines: Parts and service lines. May be empty.

    Returns:
        The new work-order row, including lines.

    Raises:
        RuntimeError: If validation fails or an open job already exists.
    """
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            _require_pms_vehicle(connection, vehicle_id)
            previous = _latest_completed_odometer(connection, vehicle_id)
            prepared = _prepare_pms_header(header, lines, previous, strict=False)
            cursor = connection.execute(
                """
                INSERT INTO work_orders (
                    vehicle_id, job_type, status, description, shop_name, cost, notes,
                    remarks, opened_at, doc_date, transaction_no, repair_type,
                    service_advisor, technician, terms, previous_odometer,
                    current_odometer, odometer_km, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vehicle_id,
                    PMS_JOB_TYPE,
                    PMS_STATUS_OPEN,
                    prepared["description"],
                    prepared["shop_name"],
                    prepared["cost"],
                    prepared["notes"],
                    prepared["remarks"],
                    timestamp,
                    prepared["doc_date"],
                    prepared["transaction_no"],
                    prepared["repair_type"],
                    prepared["service_advisor"],
                    prepared["technician"],
                    prepared["terms"],
                    prepared["previous_odometer"],
                    prepared["current_odometer"],
                    prepared["current_odometer"],
                    timestamp,
                    timestamp,
                ),
            )
            work_order_id = int(cursor.lastrowid)
            _replace_work_order_lines(connection, work_order_id, prepared["lines"])
        created = fetch_work_order(db_path, work_order_id)
        if not created:
            raise RuntimeError("PMS job was opened but could not be reloaded.")
        return created
    except RuntimeError:
        raise
    except sqlite3.IntegrityError as error:
        _raise_work_order_integrity(error)
        raise
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to open PMS job for vehicle {vehicle_id}: {error}") from error


def update_pms_work_order(
    db_path: str,
    work_order_id: int,
    header: Dict[str, Any],
    lines: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Replace the header and lines of an open PMS job.

    Completed jobs stay locked.

    Args:
        db_path: SQLite database path.
        work_order_id: Open PMS work order id.
        header: Repair, shop, odometer, and remarks fields.
        lines: Replacement line list. May be empty.

    Returns:
        The updated work-order row, including lines.
    """
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                "SELECT id, vehicle_id, job_type, status FROM work_orders WHERE id = ?",
                (work_order_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(f"Work order {work_order_id} not found.")
            if (row["job_type"] or "") != PMS_JOB_TYPE or (row["status"] or "") != PMS_STATUS_OPEN:
                raise RuntimeError("Only an open PMS job can be edited.")
            vehicle_id = int(row["vehicle_id"])
            _require_pms_vehicle(connection, vehicle_id)
            previous = _latest_completed_odometer(connection, vehicle_id)
            prepared = _prepare_pms_header(header, lines, previous, strict=False)
            _write_open_pms_job(connection, work_order_id, prepared, timestamp)
        updated = fetch_work_order(db_path, work_order_id)
        if not updated:
            raise RuntimeError("PMS job was saved but could not be reloaded.")
        return updated
    except RuntimeError:
        raise
    except sqlite3.IntegrityError as error:
        _raise_work_order_integrity(error)
        raise
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to save PMS job {work_order_id}: {error}") from error


def complete_pms_work_order(
    db_path: str,
    work_order_id: int,
    header: Dict[str, Any],
    lines: List[Dict[str, Any]],
    completed_by_user_id: Optional[int],
) -> Dict[str, Any]:
    """
    Save and complete an open PMS job.

    Doc. date becomes the service date. When an interval is set, the next due
    date is that doc. date plus the interval. The odometer on the schedule is
    not used for due status.

    Args:
        db_path: SQLite database path.
        work_order_id: Open PMS work order id.
        header: Repair, shop, odometer, and remarks fields.
        lines: At least one parts or service line.
        completed_by_user_id: User who recorded completion.

    Returns:
        Dict with work_order, schedule_before, and schedule_after.
    """
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                "SELECT id, vehicle_id, job_type, status FROM work_orders WHERE id = ?",
                (work_order_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(f"Work order {work_order_id} not found.")
            if (row["job_type"] or "") != PMS_JOB_TYPE or (row["status"] or "") != PMS_STATUS_OPEN:
                raise RuntimeError("Only an open PMS job can be completed.")
            vehicle_id = int(row["vehicle_id"])
            _require_pms_vehicle(connection, vehicle_id)
            previous = _latest_completed_odometer(connection, vehicle_id)
            prepared = _prepare_pms_header(header, lines, previous, strict=True)
            _write_open_pms_job(connection, work_order_id, prepared, timestamp)
            done_on = prepared["doc_date"]
            connection.execute(
                """
                UPDATE work_orders
                SET status = ?,
                    service_date = ?,
                    doc_date = ?,
                    completed_at = ?,
                    completed_by_user_id = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    PMS_STATUS_COMPLETED,
                    done_on,
                    done_on,
                    timestamp,
                    completed_by_user_id,
                    timestamp,
                    work_order_id,
                ),
            )
            schedule_before = _pms_schedule_snapshot(connection, vehicle_id)
            months = schedule_before.get("interval_months")
            next_due = schedule_before.get("next_due_date")
            last_odometer = prepared["current_odometer"]
            if months:
                next_due = add_calendar_months(date.fromisoformat(done_on), int(months)).isoformat()
            if schedule_before.get("vehicle_id") and (
                months or schedule_before.get("next_due_date") is not None or last_odometer is not None
            ):
                connection.execute(
                    """
                    UPDATE pms_schedules
                    SET next_due_date = ?,
                        last_odometer_km = ?,
                        updated_at = ?
                    WHERE vehicle_id = ?
                    """,
                    (next_due, last_odometer, timestamp, vehicle_id),
                )
            schedule_after = _pms_schedule_snapshot(connection, vehicle_id)
        completed = fetch_work_order(db_path, work_order_id)
        if not completed:
            raise RuntimeError("PMS job was completed but could not be reloaded.")
        return {
            "work_order": completed,
            "schedule_before": schedule_before,
            "schedule_after": schedule_after,
        }
    except RuntimeError:
        raise
    except sqlite3.IntegrityError as error:
        _raise_work_order_integrity(error)
        raise
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to complete PMS job {work_order_id}: {error}") from error


def cancel_pms_work_order(db_path: str, work_order_id: int) -> Dict[str, Any]:
    """
    Cancel an open PMS job without changing the due date.

    Args:
        db_path: SQLite database path.
        work_order_id: Open PMS work order id.

    Returns:
        The cancelled work-order row.

    Raises:
        RuntimeError: If the job is missing or not an open PMS job.
    """
    timestamp = _get_local_timestamp()
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                SELECT id, job_type, status
                FROM work_orders
                WHERE id = ?
                """,
                (work_order_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(f"Work order {work_order_id} not found.")
            if (row[1] or "") != PMS_JOB_TYPE or (row[2] or "") != PMS_STATUS_OPEN:
                raise RuntimeError("Only an open PMS job can be cancelled.")
            connection.execute(
                """
                UPDATE work_orders
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (PMS_STATUS_CANCELLED, timestamp, work_order_id),
            )
        cancelled = fetch_work_order(db_path, work_order_id)
        if not cancelled:
            raise RuntimeError("PMS job was cancelled but could not be reloaded.")
        return cancelled
    except RuntimeError:
        raise
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to cancel PMS job {work_order_id}: {error}") from error


def fetch_requisition_record(db_path: str, requisition_id: int) -> Optional[Dict[str, Any]]:
    """Fetch raw requisition columns for audit snapshots."""
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                "SELECT * FROM requisitions WHERE id = ?",
                (requisition_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as error:
        message = f"Failed to fetch requisition record {requisition_id}: {error}"
        raise RuntimeError(message) from error


DASHBOARD_USED_STATUSES = ("received", "billed")
_HAS_PO_SQL = "r.po_reference IS NOT NULL AND TRIM(r.po_reference) != ''"
_DASHBOARD_LITERS_SQL = """
CASE
    WHEN UPPER(COALESCE(r.unit, '')) = 'FULLTANK' THEN 0
    ELSE COALESCE(r.actual_quantity, r.quantity, 0)
END
"""


def _dashboard_count(connection: sqlite3.Connection, sql: str, params: tuple = ()) -> int:
    """Return a single COUNT(*) value."""
    cursor = connection.execute(sql, params)
    row = cursor.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def get_dashboard_summary(db_path: str) -> Dict[str, int]:
    """
    Return the nine Dashboard card counts.

    Used requests/POs are received or billed. PO cards require a PO number.
    """
    try:
        with get_connection(db_path) as connection:
            used = DASHBOARD_USED_STATUSES
            return {
                "vehicles": _dashboard_count(
                    connection, "SELECT COUNT(*) FROM cars WHERE is_active = 1"
                ),
                "vendors": _dashboard_count(
                    connection, "SELECT COUNT(*) FROM vendors WHERE is_active = 1"
                ),
                "companies": _dashboard_count(
                    connection, "SELECT COUNT(*) FROM companies WHERE is_active = 1"
                ),
                "all_requests": _dashboard_count(
                    connection,
                    "SELECT COUNT(*) FROM requisitions WHERE is_active = 1",
                ),
                "used_requests": _dashboard_count(
                    connection,
                    """
                    SELECT COUNT(*) FROM requisitions
                    WHERE is_active = 1 AND status IN (?, ?)
                    """,
                    used,
                ),
                "cancelled_requests": _dashboard_count(
                    connection,
                    """
                    SELECT COUNT(*) FROM requisitions
                    WHERE is_active = 1 AND status = 'cancelled'
                    """,
                ),
                "all_pos": _dashboard_count(
                    connection,
                    f"SELECT COUNT(*) FROM requisitions r WHERE r.is_active = 1 AND {_HAS_PO_SQL}",
                ),
                "used_pos": _dashboard_count(
                    connection,
                    f"""
                    SELECT COUNT(*) FROM requisitions r
                    WHERE r.is_active = 1 AND {_HAS_PO_SQL} AND r.status IN (?, ?)
                    """,
                    used,
                ),
                "cancelled_pos": _dashboard_count(
                    connection,
                    f"""
                    SELECT COUNT(*) FROM requisitions r
                    WHERE r.is_active = 1 AND {_HAS_PO_SQL} AND r.status = 'cancelled'
                    """,
                ),
            }
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to load dashboard summary: {error}") from error


def list_dashboard_filter_options(db_path: str) -> Dict[str, Any]:
    """Companies, vendors, and fuel types for Dashboard modal filters."""
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            companies = [
                row["company"]
                for row in connection.execute(
                    """
                    SELECT DISTINCT company
                    FROM cars
                    WHERE is_active = 1 AND company IS NOT NULL AND TRIM(company) != ''
                    ORDER BY company
                    """
                )
            ]
            vendors = [
                {"id": row["id"], "name": row["name"]}
                for row in connection.execute(
                    """
                    SELECT id, name FROM vendors
                    WHERE is_active = 1
                    ORDER BY name
                    """
                )
            ]
            fuel_types = [
                row["fuel_type"]
                for row in connection.execute(
                    """
                    SELECT DISTINCT fuel_type
                    FROM cars
                    WHERE is_active = 1 AND fuel_type IS NOT NULL AND TRIM(fuel_type) != ''
                    ORDER BY fuel_type
                    """
                )
            ]
            return {
                "companies": companies,
                "vendors": vendors,
                "fuel_types": fuel_types,
            }
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to load dashboard filter options: {error}") from error


def list_dashboard_vehicles(
    db_path: str,
    company: Optional[str] = None,
    vendor_id: Optional[int] = None,
    fuel_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List active vehicles for the Dashboard modal."""
    where = ["c.is_active = 1"]
    params: List[Any] = []
    if company:
        where.append("c.company = ?")
        params.append(company)
    if vendor_id is not None:
        where.append("c.vendor_id = ?")
        params.append(vendor_id)
    if fuel_type:
        where.append("c.fuel_type = ?")
        params.append(fuel_type)
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                f"""
                SELECT
                    c.id,
                    c.plate_number,
                    c.model,
                    c.company,
                    c.fuel_type,
                    c.assigned_to,
                    c.vendor_id,
                    v.name AS vendor_name,
                    COALESCE(agg.total_quantity, 0) AS total_quantity,
                    COALESCE(agg.total_price, 0) AS total_price
                FROM cars c
                LEFT JOIN vendors v ON v.id = c.vendor_id
                LEFT JOIN (
                    SELECT
                        r.vehicle_id,
                        SUM({_DASHBOARD_LITERS_SQL}) AS total_quantity,
                        SUM(COALESCE(r.total_price, 0)) AS total_price
                    FROM requisitions r
                    WHERE r.is_active = 1
                    GROUP BY r.vehicle_id
                ) agg ON agg.vehicle_id = c.id
                WHERE {" AND ".join(where)}
                ORDER BY c.plate_number
                """,
                tuple(params),
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to list dashboard vehicles: {error}") from error


def list_dashboard_vendors(db_path: str) -> List[Dict[str, Any]]:
    """List active vendors with request quantity and amount totals."""
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                f"""
                SELECT
                    v.id,
                    v.name,
                    v.address,
                    COALESCE(agg.total_quantity, 0) AS total_quantity,
                    COALESCE(agg.total_price, 0) AS total_price
                FROM vendors v
                LEFT JOIN (
                    SELECT
                        r.vendor_id,
                        SUM({_DASHBOARD_LITERS_SQL}) AS total_quantity,
                        SUM(COALESCE(r.total_price, 0)) AS total_price
                    FROM requisitions r
                    WHERE r.is_active = 1
                    GROUP BY r.vendor_id
                ) agg ON agg.vendor_id = v.id
                WHERE v.is_active = 1
                ORDER BY v.name
                """
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to list dashboard vendors: {error}") from error


def list_dashboard_companies(db_path: str) -> List[Dict[str, Any]]:
    """List active companies with request quantity and amount totals."""
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                f"""
                SELECT
                    co.id,
                    co.code,
                    co.name,
                    COALESCE(agg.total_quantity, 0) AS total_quantity,
                    COALESCE(agg.total_price, 0) AS total_price
                FROM companies co
                LEFT JOIN (
                    SELECT
                        c.company AS company_code,
                        SUM({_DASHBOARD_LITERS_SQL}) AS total_quantity,
                        SUM(COALESCE(r.total_price, 0)) AS total_price
                    FROM requisitions r
                    INNER JOIN cars c ON c.id = r.vehicle_id
                    WHERE r.is_active = 1
                    GROUP BY c.company
                ) agg ON agg.company_code = co.code
                WHERE co.is_active = 1
                ORDER BY co.name
                """
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to list dashboard companies: {error}") from error


def list_dashboard_requisitions(
    db_path: str,
    *,
    scope: str,
    po_only: bool = False,
    plate: Optional[str] = None,
    vendor_id: Optional[int] = None,
    company: Optional[str] = None,
    fuel_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    cancelled_from: Optional[str] = None,
    cancelled_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List requisitions or POs for a Dashboard modal.

    scope: all | used | cancelled
    Date filters apply to created_at (requests) or po_created_at (POs).
    Cancelled date uses updated_at on cancelled rows.
    """
    normalized = (scope or "all").strip().lower()
    if normalized not in {"all", "used", "cancelled"}:
        raise RuntimeError("Invalid dashboard scope.")

    where = ["r.is_active = 1"]
    params: List[Any] = []
    if po_only:
        where.append(_HAS_PO_SQL)
    if normalized == "used":
        where.append("r.status IN (?, ?)")
        params.extend(DASHBOARD_USED_STATUSES)
    elif normalized == "cancelled":
        where.append("r.status = 'cancelled'")

    if plate:
        where.append("UPPER(c.plate_number) LIKE ?")
        params.append(f"%{plate.strip().upper()}%")
    if vendor_id is not None:
        where.append("r.vendor_id = ?")
        params.append(vendor_id)
    if company:
        where.append("c.company = ?")
        params.append(company)
    if fuel_type:
        where.append("r.fuel_type = ?")
        params.append(fuel_type)

    date_column = "r.po_created_at" if po_only else "r.created_at"
    if date_from:
        where.append(f"date({date_column}) >= date(?)")
        params.append(date_from)
    if date_to:
        where.append(f"date({date_column}) <= date(?)")
        params.append(date_to)
    if normalized == "cancelled" and cancelled_from:
        where.append("date(r.updated_at) >= date(?)")
        params.append(cancelled_from)
    if normalized == "cancelled" and cancelled_to:
        where.append("date(r.updated_at) <= date(?)")
        params.append(cancelled_to)

    order = "r.po_created_at DESC, r.id DESC" if po_only else "r.created_at DESC, r.id DESC"
    try:
        with get_connection(db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                f"""
                SELECT
                    r.id,
                    r.serial_number,
                    r.po_reference,
                    r.quantity,
                    r.unit,
                    r.total_price,
                    r.status,
                    r.fuel_type,
                    r.created_at,
                    r.po_created_at,
                    r.updated_at,
                    r.cancel_reason,
                    r.cancelled_by,
                    c.plate_number,
                    c.model,
                    c.company,
                    v.name AS vendor_name
                FROM requisitions r
                INNER JOIN cars c ON c.id = r.vehicle_id
                LEFT JOIN vendors v ON v.id = r.vendor_id
                WHERE {" AND ".join(where)}
                ORDER BY {order}
                """,
                tuple(params),
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to list dashboard requisitions: {error}") from error
