"""Tests for authentication module."""
import pytest

from src.auth import hash_password, verify_password


def test_hash_password():
    """Test that password hashing produces a different string."""
    password = "test_password_123"
    hashed = hash_password(password)
    assert hashed != password
    assert len(hashed) > 0


def test_verify_password_correct():
    """Test that correct password verification works."""
    password = "test_password_123"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Test that incorrect password verification fails."""
    password = "test_password_123"
    wrong_password = "wrong_password"
    hashed = hash_password(password)
    assert verify_password(wrong_password, hashed) is False


def test_hash_password_different_salts():
    """Test that same password produces different hashes (different salts)."""
    password = "test_password_123"
    hashed1 = hash_password(password)
    hashed2 = hash_password(password)
    assert hashed1 != hashed2  # Different salts should produce different hashes
    # But both should verify correctly
    assert verify_password(password, hashed1) is True
    assert verify_password(password, hashed2) is True

