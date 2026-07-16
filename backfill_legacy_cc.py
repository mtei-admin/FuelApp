"""Tag legacy credit-card fills that were entered via the PO workflow before CC Fills existed.

Add request serial numbers to data/legacy_cc_via_po.json, then run:

  python backfill_legacy_cc.py           # dry-run (preview only)
  python backfill_legacy_cc.py --apply   # write changes + audit log

Serial numbers may be padded or not (2827 or 02827). Each tagged row gets:
  - settlement_type = credit_card
  - notes += "[Legacy CC via PO]"
Status is unchanged (billed rows stay billed).
"""
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from src.audit import REQUISITION_AUDIT_FIELDS, log_field_update
from src.database import (
    fetch_requisition_by_serial,
    fetch_requisition_record,
    init_database,
    mark_legacy_cc_via_po,
    normalize_request_serial,
)

DB_PATH = Path("data") / "fuel_system.db"
SEED_FILE = Path("data") / "legacy_cc_via_po.json"


def load_serial_numbers() -> List[str]:
    """Load request serial numbers from the JSON seed file."""
    if not SEED_FILE.is_file():
        raise FileNotFoundError(f"List file not found: {SEED_FILE}")
    with SEED_FILE.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict) and isinstance(data.get("serial_numbers"), list):
        raw_items = data["serial_numbers"]
    else:
        raise ValueError(
            "legacy_cc_via_po.json must be a JSON array of serial numbers "
            "or an object with a serial_numbers array."
        )
    serials: List[str] = []
    seen = set()
    for item in raw_items:
        serial = normalize_request_serial(str(item))
        if serial and serial not in seen:
            seen.add(serial)
            serials.append(serial)
    return serials


def process_serial(db_path: str, serial: str, apply: bool) -> Dict[str, Any]:
    """
    Preview or apply legacy CC tagging for one request serial.

    Returns:
        Result dict with outcome for console reporting.
    """
    row = fetch_requisition_by_serial(db_path, serial)
    if not row:
        return {"serial": serial, "outcome": "not_found"}

    req_id = int(row["id"])
    if not apply:
        status = (row.get("status") or "").lower()
        settlement = (row.get("settlement_type") or "vendor_invoice").lower()
        return {
            "serial": row.get("serial_number") or serial,
            "outcome": "would_tag",
            "status": status,
            "settlement_type": settlement,
            "plate_number": row.get("plate_number"),
            "vendor_name": row.get("vendor_name"),
        }

    before = fetch_requisition_record(db_path, req_id)
    result = mark_legacy_cc_via_po(db_path, req_id)
    after = fetch_requisition_record(db_path, req_id)
    if result.get("changed"):
        log_field_update(
            db_path,
            "requisition",
            req_id,
            "legacy_cc_via_po",
            None,
            before,
            after,
            REQUISITION_AUDIT_FIELDS,
            metadata={"serial_number": result.get("serial_number")},
        )
    return {
        "serial": result.get("serial_number") or serial,
        "outcome": "tagged" if result.get("changed") else "unchanged",
        "status": result.get("status"),
        "message": result.get("message"),
    }


def main() -> None:
    """Run legacy CC backfill from data/legacy_cc_via_po.json."""
    parser = argparse.ArgumentParser(
        description="Tag legacy CC fills (entered as PO) by request serial number."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Default is dry-run preview only.",
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    serials = load_serial_numbers()
    if not serials:
        print(f"No serial numbers in {SEED_FILE}.")
        print('Add entries like: ["02827", "02831", "2835"]')
        return

    db_path = str(DB_PATH)
    init_database(db_path)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Legacy CC via PO backfill ({mode}) — {len(serials)} serial(s)")
    print("-" * 60)

    counts = {"not_found": 0, "would_tag": 0, "tagged": 0, "unchanged": 0}
    for serial in serials:
        result = process_serial(db_path, serial, apply=args.apply)
        outcome = result["outcome"]
        counts[outcome] = counts.get(outcome, 0) + 1
        if outcome == "not_found":
            print(f"  {serial}: NOT FOUND")
        elif outcome == "would_tag":
            print(
                f"  {result['serial']}: would tag "
                f"(status={result['status']}, payment={result['settlement_type']}) "
                f"{result.get('plate_number')} @ {result.get('vendor_name')}"
            )
        else:
            print(f"  {result['serial']}: {outcome} — {result.get('message', '')}")

    print("-" * 60)
    print(
        f"Done. not_found={counts.get('not_found', 0)} "
        f"would_tag={counts.get('would_tag', 0)} "
        f"tagged={counts.get('tagged', 0)} "
        f"unchanged={counts.get('unchanged', 0)}"
    )
    if not args.apply and counts.get("would_tag", 0) > 0:
        print("Re-run with --apply to save changes.")


if __name__ == "__main__":
    main()
