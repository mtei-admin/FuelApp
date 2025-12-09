"""Quick test runner script for manual testing."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import init_database
from src.auth import hash_password, verify_password


def test_auth():
    """Test authentication functions."""
    print("Testing authentication...")
    password = "test123"
    hashed = hash_password(password)
    assert verify_password(password, hashed), "Password verification failed"
    assert not verify_password("wrong", hashed), "Wrong password should fail"
    print("✓ Authentication tests passed")


def test_database_init():
    """Test database initialization."""
    print("Testing database initialization...")
    test_db = Path("data") / "test_fuel_system.db"
    init_database(str(test_db))
    assert test_db.exists(), "Database file not created"
    print("✓ Database initialization test passed")
    # Cleanup
    if test_db.exists():
        test_db.unlink()


def run_quick_tests():
    """Run quick smoke tests."""
    print("Running quick tests...\n")
    try:
        test_auth()
        test_database_init()
        print("\n✅ All quick tests passed!")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_quick_tests()
    sys.exit(0 if success else 1)

