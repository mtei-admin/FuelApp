"""Tests for database module."""
import gc
import os
import tempfile
import time

import pytest

from datetime import date, timedelta

from src.database import (
    create_requisition,
    create_user,
    fetch_user_by_username,
    init_database,
    list_cars,
    list_requisitions_by_status,
    list_users,
    list_vehicle_registrations,
    list_vendors,
    registration_alert_status,
    update_vehicle_registration,
    create_service_center,
    fetch_service_center_by_id,
    list_service_centers,
    reactivate_service_center,
    soft_delete_service_center,
    update_service_center,
    upsert_car,
    upsert_vendor,
)


def _remove_sqlite_files(path: str) -> None:
    """Best-effort delete of SQLite db + WAL sidecars (Windows file locks)."""
    gc.collect()
    for candidate in (path, f"{path}-wal", f"{path}-shm"):
        for _ in range(5):
            try:
                if os.path.exists(candidate):
                    os.unlink(candidate)
                break
            except PermissionError:
                time.sleep(0.05)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_database(path)
    yield path
    _remove_sqlite_files(path)


def test_init_database(temp_db):
    """Test that database initialization creates required tables."""
    assert os.path.exists(temp_db)
    # Database should be accessible
    users = list_users(temp_db)
    assert isinstance(users, list)


def test_create_user(temp_db):
    """Test user creation."""
    from src.auth import hash_password
    
    username = "testuser"
    password = "testpass123"
    hashed = hash_password(password)
    user_id = create_user(temp_db, username, hashed, "encoder", full_name="Test User")
    assert user_id > 0
    
    # Verify user exists
    user = fetch_user_by_username(temp_db, username)
    assert user is not None
    assert user["username"] == username
    assert user["role"] == "encoder"


def test_upsert_vendor(temp_db):
    """Test vendor creation and reactivation."""
    vendor_id = upsert_vendor(temp_db, "Test Vendor", "contact@test.com")
    assert vendor_id > 0
    
    vendors = list_vendors(temp_db)
    assert len(vendors) == 1
    assert vendors[0]["name"] == "Test Vendor"
    
    # Test reactivation (upsert existing)
    vendor_id2 = upsert_vendor(temp_db, "Test Vendor", "newcontact@test.com")
    assert vendor_id == vendor_id2  # Same vendor


def test_upsert_car(temp_db):
    """Test car creation with hyphenated plate."""
    vendor_id = upsert_vendor(temp_db, "Test Vendor")
    car_id = upsert_car(temp_db, "ABC-123", "Test Model", vendor_id, assigned_to="Driver")
    assert car_id > 0
    
    cars = list_cars(temp_db)
    assert len(cars) == 1
    assert cars[0]["plate_number"] == "ABC-123"
    assert cars[0]["model"] == "Test Model"


def test_upsert_car_rejects_special_characters(temp_db):
    """Disallowed punctuation is rejected."""
    vendor_id = upsert_vendor(temp_db, "Test Vendor")
    with pytest.raises(RuntimeError, match="letters, numbers"):
        upsert_car(temp_db, "ABC/123", "Test Model", vendor_id, assigned_to="Driver")


def test_create_requisition(temp_db):
    """Test requisition creation."""
    from src.auth import hash_password
    
    # Setup: create user and car
    user_id = create_user(
        temp_db, "requester", hash_password("pass"), "encoder", full_name="Requester"
    )
    vendor_id = upsert_vendor(temp_db, "Fuel Vendor")
    car_id = upsert_car(temp_db, "XYZ789", "Test Car", vendor_id, assigned_to="Driver")
    
    # Create requisition
    req_id = create_requisition(
        temp_db,
        requester_id=user_id,
        vehicle_id=car_id,
        vendor_id=vendor_id,
        quantity=50.0,
        unit="liters",
        unit_price=1.50,
        notes="Test request",
    )
    assert req_id > 0
    
    # Verify requisition exists
    pending = list_requisitions_by_status(temp_db, ["pending"])
    assert len(pending) == 1
    assert pending[0]["quantity"] == 50.0
    assert pending[0]["unit_price"] == 1.50
    assert pending[0]["total_price"] == 75.0  # 50 * 1.50


def test_registration_alert_status_categories():
    """LTO expiry maps to missing / expired / due_soon / current."""
    today = date(2026, 8, 13)
    assert registration_alert_status(None, today=today) == "missing"
    assert registration_alert_status("2026-08-01", today=today) == "expired"
    assert registration_alert_status("2026-08-20", today=today) == "due_soon"
    assert registration_alert_status("2026-12-01", today=today) == "current"


def test_update_vehicle_registration(temp_db):
    """Company-owned registration fields appear in registrations list."""
    vendor_id = upsert_vendor(temp_db, "Test Vendor")
    car_id = upsert_car(
        temp_db,
        "REG-001",
        "Van",
        vendor_id,
        assigned_to="Alex",
        is_company_owned=True,
        registration_date="2025-01-15",
        expiration_date=(date.today() + timedelta(days=10)).isoformat(),
    )
    expiry = (date.today() + timedelta(days=10)).isoformat()

    update_vehicle_registration(
        temp_db,
        car_id,
        registration_date="2025-01-15",
        lto_expiry=expiry,
        or_number="OR-99",
        cr_number="CR-88",
        mv_file_no="MV-77",
        registration_remarks="Renewed",
    )

    rows = list_vehicle_registrations(temp_db)
    match = next(row for row in rows if row["id"] == car_id)
    assert match["registration_date"] == "2025-01-15"
    assert match["lto_expiry"] == expiry
    assert match["or_number"] == "OR-99"
    assert match["cr_number"] == "CR-88"
    assert match["mv_file_no"] == "MV-77"
    assert match["alert_status"] == "due_soon"


def test_non_company_owned_excluded_from_registrations(temp_db):
    """Non–company-owned vehicles are not tracked for renewals."""
    vendor_id = upsert_vendor(temp_db, "Test Vendor")
    upsert_car(
        temp_db,
        "PRIV-1",
        "Sedan",
        vendor_id,
        assigned_to="Pat",
        is_company_owned=False,
        expiration_date=(date.today() + timedelta(days=5)).isoformat(),
    )
    assert list_vehicle_registrations(temp_db) == []


def test_update_requisition_po_sets_po_created_at(temp_db):
    """Generating a PO stores po_created_at for PO-date display."""
    from src.auth import hash_password
    from src.database import (
        create_requisition,
        create_user,
        fetch_requisition_by_id,
        list_po_signatories,
        update_requisition_po,
        update_requisition_status,
        upsert_car,
        upsert_vendor,
    )

    user_id = create_user(
        temp_db, "buyer", hash_password("pass"), "purchaser", full_name="Buyer"
    )
    create_user(temp_db, "signer", hash_password("pass"), "approver", full_name="Signer")
    vendor_id = upsert_vendor(temp_db, "Fuel Vendor")
    car_id = upsert_car(temp_db, "ABC123", "Test Car", vendor_id, assigned_to="Driver")
    req_id = create_requisition(
        temp_db,
        requester_id=user_id,
        vehicle_id=car_id,
        vendor_id=vendor_id,
        quantity=40.0,
        unit="liters",
        unit_price=None,
        notes="",
    )
    update_requisition_status(temp_db, req_id, "approved", user_id)
    signatories = list_po_signatories(temp_db)
    assert signatories
    update_requisition_po(
        temp_db,
        req_id,
        "PO-TEST-1",
        unit_price=50.0,
        prepared_by_user_id=user_id,
        signatory_user_id=signatories[0]["id"],
    )
    row = fetch_requisition_by_id(temp_db, req_id)
    assert row is not None
    assert row.get("status") == "po_generated"
    assert row.get("po_created_at")


def test_admin_cancel_pending_and_po_generated(temp_db):
    """Superuser cancel works on pending and PO-generated; keeps PO number."""
    from src.auth import hash_password
    from src.database import (
        admin_cancel_requisition,
        create_requisition,
        create_user,
        fetch_requisition_by_id,
        fetch_requisition_record,
        list_po_signatories,
        update_requisition_po,
        update_requisition_status,
        upsert_car,
        upsert_vendor,
    )

    admin_id = create_user(
        temp_db, "admin", hash_password("pass"), "superuser", full_name="Admin User"
    )
    create_user(temp_db, "signer", hash_password("pass"), "approver", full_name="Signer")
    vendor_id = upsert_vendor(temp_db, "Fuel Vendor")
    car_id = upsert_car(temp_db, "XYZ999", "Test Car", vendor_id, assigned_to="Driver")
    pending_id = create_requisition(
        temp_db,
        requester_id=admin_id,
        vehicle_id=car_id,
        vendor_id=vendor_id,
        quantity=20.0,
        unit="liters",
        unit_price=None,
        notes="",
    )
    admin_cancel_requisition(temp_db, pending_id, admin_id, "Duplicate request filed in error")
    pending_row = fetch_requisition_by_id(temp_db, pending_id)
    pending_raw = fetch_requisition_record(temp_db, pending_id)
    assert pending_row is not None
    assert pending_raw is not None
    assert pending_row.get("status") == "cancelled"
    assert pending_raw.get("cancelled_by") == "Admin User"

    po_id = create_requisition(
        temp_db,
        requester_id=admin_id,
        vehicle_id=car_id,
        vendor_id=vendor_id,
        quantity=30.0,
        unit="liters",
        unit_price=None,
        notes="",
    )
    update_requisition_status(temp_db, po_id, "approved", admin_id)
    signatories = list_po_signatories(temp_db)
    assert signatories
    update_requisition_po(
        temp_db,
        po_id,
        "PO-VOID-1",
        unit_price=50.0,
        prepared_by_user_id=admin_id,
        signatory_user_id=signatories[0]["id"],
    )
    po_before = fetch_requisition_record(temp_db, po_id)
    assert po_before is not None
    po_created_at = po_before.get("po_created_at")
    admin_cancel_requisition(temp_db, po_id, admin_id, "Vendor cannot supply this order")
    po_row = fetch_requisition_by_id(temp_db, po_id)
    po_raw = fetch_requisition_record(temp_db, po_id)
    assert po_row is not None
    assert po_raw is not None
    assert po_row.get("status") == "cancelled"
    assert po_raw.get("po_reference") == "PO-VOID-1"
    assert po_raw.get("po_created_at") == po_created_at


def test_dashboard_summary_and_lists(temp_db):
    """Used cards count received/billed; PO cards require a PO number."""
    from src.auth import hash_password
    from src.database import (
        create_requisition,
        create_user,
        get_dashboard_summary,
        list_dashboard_requisitions,
        list_dashboard_vehicles,
        list_po_signatories,
        update_requisition_po,
        update_requisition_status,
        upsert_car,
        upsert_vendor,
    )

    user_id = create_user(
        temp_db, "dashuser", hash_password("pass"), "encoder", full_name="Dash User"
    )
    create_user(temp_db, "signer", hash_password("pass"), "approver", full_name="Signer")
    vendor_id = upsert_vendor(temp_db, "Dash Vendor")
    car_id = upsert_car(
        temp_db,
        "DASH-1",
        "Van",
        vendor_id,
        assigned_to="Driver",
        fuel_type="Diesel",
        company="MTEI",
    )

    pending_id = create_requisition(
        temp_db, user_id, car_id, vendor_id, 10.0, "liters", 50.0, "pending row"
    )
    used_id = create_requisition(
        temp_db, user_id, car_id, vendor_id, 20.0, "liters", 50.0, "used row"
    )
    cc_id = create_requisition(
        temp_db, user_id, car_id, vendor_id, 15.0, "liters", 50.0, "cc row"
    )
    po_used_id = create_requisition(
        temp_db, user_id, car_id, vendor_id, 30.0, "liters", 50.0, "po used"
    )
    po_cancel_id = create_requisition(
        temp_db, user_id, car_id, vendor_id, 40.0, "liters", 50.0, "po cancel"
    )

    update_requisition_status(temp_db, used_id, "received", user_id)
    update_requisition_status(temp_db, cc_id, "paid_cc", user_id)
    update_requisition_status(temp_db, pending_id, "cancelled", user_id)

    signatories = list_po_signatories(temp_db)
    assert signatories
    for req_id, po_no in ((po_used_id, "PO-DASH-1"), (po_cancel_id, "PO-DASH-2")):
        update_requisition_status(temp_db, req_id, "approved", user_id)
        update_requisition_po(
            temp_db,
            req_id,
            po_no,
            unit_price=50.0,
            prepared_by_user_id=user_id,
            signatory_user_id=signatories[0]["id"],
        )
    update_requisition_status(temp_db, po_used_id, "received", user_id)
    update_requisition_status(temp_db, po_cancel_id, "cancelled", user_id)

    counts = get_dashboard_summary(temp_db)
    assert counts["vehicles"] == 1
    assert counts["vendors"] == 1
    assert counts["companies"] >= 1
    assert counts["all_requests"] == 5
    assert counts["used_requests"] == 2
    assert counts["cancelled_requests"] == 2
    assert counts["all_pos"] == 2
    assert counts["used_pos"] == 1
    assert counts["cancelled_pos"] == 1

    vehicles = list_dashboard_vehicles(temp_db, company="MTEI", fuel_type="Diesel")
    assert len(vehicles) == 1
    assert vehicles[0]["plate_number"] == "DASH-1"
    assert vehicles[0]["total_quantity"] == 115
    assert vehicles[0]["total_price"] == 5750

    used_requests = list_dashboard_requisitions(temp_db, scope="used")
    used_ids = {row["id"] for row in used_requests}
    assert used_ids == {used_id, po_used_id}
    assert all(row.get("total_price") is not None for row in used_requests)

    all_pos = list_dashboard_requisitions(temp_db, scope="all", po_only=True)
    assert {row["id"] for row in all_pos} == {po_used_id, po_cancel_id}


def test_audit_log_search_request_po_plate_requestor(temp_db):
    """Transaction log search matches request id, PO number, plate, and requestor."""
    import json

    from src.auth import hash_password
    from src.database import (
        create_requisition,
        create_user,
        insert_audit_log,
        list_audit_log,
        upsert_car,
        upsert_vendor,
    )

    user_id = create_user(
        temp_db, "acct1", hash_password("pass"), "encoder", full_name="Account User"
    )
    vendor_id = upsert_vendor(temp_db, "Search Vendor")
    car_id = upsert_car(temp_db, "PLT-99", "Van", vendor_id, assigned_to="Driver")
    req_id = create_requisition(
        temp_db,
        requester_id=user_id,
        vehicle_id=car_id,
        vendor_id=vendor_id,
        quantity=10.0,
        unit="liters",
        unit_price=50.0,
        notes="notes",
        requestor_name="Juan Dela Cruz",
    )
    insert_audit_log(
        temp_db,
        "requisition",
        req_id,
        "created",
        user_id,
        "acct1",
        "encoder",
        "Account User",
        "{}",
        json.dumps({"serial_number": "00001", "po_reference": "PO-SRCH-1"}),
        "{}",
    )
    insert_audit_log(
        temp_db,
        "vendor",
        vendor_id,
        "created",
        user_id,
        "acct1",
        "encoder",
        "Account User",
        "{}",
        json.dumps({"name": "Search Vendor"}),
        "{}",
    )

    def ids(rows):
        return {row["entity_id"] for row in rows if row["entity_type"] == "requisition"}

    assert req_id in ids(list_audit_log(temp_db, q="PLT-99"))
    assert req_id in ids(list_audit_log(temp_db, q="Dela"))
    assert req_id not in ids(list_audit_log(temp_db, q="Account User"))
    assert req_id not in ids(list_audit_log(temp_db, q="acct1"))
    assert req_id in ids(list_audit_log(temp_db, q="PO-SRCH-1"))
    assert req_id in ids(list_audit_log(temp_db, q=str(req_id)))
    assert list_audit_log(temp_db, q="ZZZNOMATCH") == []


def test_pms_alert_status_categories():
    """Next due date maps to missing / overdue / due_soon / current."""
    from src.database import pms_alert_status

    today = date(2026, 8, 13)
    assert pms_alert_status(None, today=today) == "missing"
    assert pms_alert_status("2026-08-01", today=today) == "overdue"
    assert pms_alert_status("2026-08-20", today=today) == "due_soon"
    assert pms_alert_status("2026-12-01", today=today) == "current"


def test_pms_complete_rolls_next_due_and_blocks_second_open_job(temp_db):
    """Completing a job advances the due date; a vehicle cannot have two open PMS jobs."""
    from src.database import (
        complete_pms_work_order,
        list_pms_vehicles,
        list_pms_work_order_history,
        open_pms_work_order,
        update_pms_schedule,
    )

    vendor_id = upsert_vendor(temp_db, "Shop Vendor")
    car_id = upsert_car(
        temp_db,
        "PMS-001",
        "Truck",
        vendor_id,
        assigned_to="Alex",
        is_company_owned=True,
    )
    update_pms_schedule(temp_db, car_id, interval_months=6, next_due_date="2026-01-01")
    header = {
        "transaction_no": "TX-1",
        "doc_date": "2026-03-15",
        "repair_type": "change_oil",
        "shop_name": "Lanang Shop",
        "terms": "cash",
        "current_odometer": 12000,
        "remarks": "Due service",
    }
    line = {
        "part_code": "OIL-1",
        "line_type": "lubricants",
        "description": "Engine oil",
        "unit": "liters",
        "quantity": 4,
        "unit_price": 400,
        "discount": 100,
    }
    opened = open_pms_work_order(temp_db, car_id, header, [line])
    with pytest.raises(RuntimeError, match="already has an open"):
        open_pms_work_order(temp_db, car_id, {**header, "transaction_no": "TX-2"}, [])

    result = complete_pms_work_order(
        temp_db,
        opened["id"],
        header,
        [line],
        completed_by_user_id=None,
    )
    assert result["schedule_after"]["next_due_date"] == "2026-09-15"
    assert result["work_order"]["cost"] == 1500
    assert result["work_order"]["lines"][0]["total_amount"] == 1500
    rows = list_pms_vehicles(temp_db)
    match = next(row for row in rows if row["id"] == car_id)
    assert match["last_service_date"] == "2026-03-15"
    assert match["next_due_date"] == "2026-09-15"
    assert match["previous_odometer"] == 12000
    assert match["open_work_order_id"] is None
    history = list_pms_work_order_history(temp_db, car_id)
    assert len(history) == 1
    assert history[0]["status"] == "completed"
    assert history[0]["cost"] == 1500

    with pytest.raises(RuntimeError, match="greater than the previous"):
        open_pms_work_order(
            temp_db,
            car_id,
            {**header, "transaction_no": "TX-2", "current_odometer": 12000},
            [line],
        )


def test_service_center_unique_name_and_soft_delete(temp_db):
    """Service center names are unique regardless of case, and deactivate is reversible."""
    center_id = create_service_center(temp_db, "North Shop", "123 Road", "09171234567")
    with pytest.raises(RuntimeError, match="already exists"):
        create_service_center(temp_db, "north shop", "Other", "")
    update_service_center(temp_db, center_id, "North Shop", "456 Road", "0999")
    row = fetch_service_center_by_id(temp_db, center_id)
    assert row is not None
    assert row["address"] == "456 Road"
    assert row["contact_no"] == "0999"
    soft_delete_service_center(temp_db, center_id)
    active = list_service_centers(temp_db, active_only=True)
    assert all(item["id"] != center_id for item in active)
    reactivate_service_center(temp_db, center_id)
    restored = fetch_service_center_by_id(temp_db, center_id)
    assert restored is not None
    assert restored["is_active"] == 1
