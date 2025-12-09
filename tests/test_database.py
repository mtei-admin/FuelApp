"""Tests for database module."""
import os
import tempfile
import pytest

from src.database import (
    create_requisition,
    create_user,
    fetch_user_by_username,
    init_database,
    list_cars,
    list_requisitions_by_status,
    list_users,
    list_vendors,
    upsert_car,
    upsert_vendor,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_database(path)
    yield path
    os.unlink(path)


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
    user_id = create_user(temp_db, username, hashed, "user")
    assert user_id > 0
    
    # Verify user exists
    user = fetch_user_by_username(temp_db, username)
    assert user is not None
    assert user["username"] == username
    assert user["role"] == "user"


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
    """Test car creation."""
    vendor_id = upsert_vendor(temp_db, "Test Vendor")
    car_id = upsert_car(temp_db, "ABC-123", "Test Model", vendor_id)
    assert car_id > 0
    
    cars = list_cars(temp_db)
    assert len(cars) == 1
    assert cars[0]["plate_number"] == "ABC-123"
    assert cars[0]["model"] == "Test Model"


def test_create_requisition(temp_db):
    """Test requisition creation."""
    from src.auth import hash_password
    
    # Setup: create user and car
    user_id = create_user(temp_db, "requester", hash_password("pass"), "user")
    vendor_id = upsert_vendor(temp_db, "Fuel Vendor")
    car_id = upsert_car(temp_db, "XYZ-789", "Test Car", vendor_id)
    
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

