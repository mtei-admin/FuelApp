"""Reset transactional data and set next request / PO serial numbers."""
from pathlib import Path

from src.database import init_database, reset_transactions_and_sequences

DB_PATH = Path("data") / "fuel_system.db"
REQUISITION_SERIAL_START = 2827
PO_SERIAL_START = 2787


def main() -> None:
    """Delete all requests/POs and set the next serial counters."""
    db_path = str(DB_PATH)
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    init_database(db_path)
    reset_transactions_and_sequences(
        db_path,
        requisition_serial=REQUISITION_SERIAL_START,
        po_serial=PO_SERIAL_START,
    )
    print("Deleted all requisition / PO transaction records.")
    print(f"Next request serial_number: {REQUISITION_SERIAL_START}")
    print(f"Next auto PO reference (when PO Ref blank): {PO_SERIAL_START}")
    print("Master data (users, vendors, vehicles) unchanged.")


if __name__ == "__main__":
    main()
