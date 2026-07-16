"""Tests for plate number validation."""
import pytest

from src.utils.plate import (
    PLATE_INVALID_MESSAGE,
    normalize_plate_number,
    plate_identity_key,
)


def test_normalize_plate_uppercases_and_trims() -> None:
    """Valid plates are trimmed and uppercased."""
    assert normalize_plate_number("  lab7523 ") == "LAB7523"


def test_normalize_plate_allows_hyphen_space_ampersand() -> None:
    """Hyphen, spaces, and & are allowed and preserved."""
    assert normalize_plate_number("lab-7523") == "LAB-7523"
    assert normalize_plate_number("lab 7523") == "LAB 7523"
    assert normalize_plate_number("mte & co") == "MTE & CO"


def test_normalize_plate_rejects_other_specials() -> None:
    """Disallowed punctuation is rejected."""
    with pytest.raises(ValueError, match="letters, numbers"):
        normalize_plate_number("LAB/7523")
    with pytest.raises(ValueError, match="letters, numbers"):
        normalize_plate_number("LAB_7523")


def test_normalize_plate_rejects_empty() -> None:
    """Blank plate is rejected."""
    with pytest.raises(ValueError, match="required"):
        normalize_plate_number("   ")


def test_plate_identity_key_ignores_space_and_hyphen() -> None:
    """Identity key treats hyphen/space variants as the same plate."""
    assert plate_identity_key("LAB-7523") == "LAB7523"
    assert plate_identity_key("LAB 7523") == "LAB7523"
    assert plate_identity_key("MTE & CO") == "MTE&CO"
    assert PLATE_INVALID_MESSAGE
