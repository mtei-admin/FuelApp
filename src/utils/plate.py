"""Vehicle plate number validation and normalization."""
import re
from typing import Final

# Letters, digits, hyphen, spaces, and ampersand only (after uppercase).
_PLATE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Z0-9\-\s&]+$")
_HAS_LETTER_OR_DIGIT: Final[re.Pattern[str]] = re.compile(r"[A-Z0-9]")
# Uniqueness ignores formatting spaces/hyphens; & remains significant.
_FORMAT_CHARS: Final[re.Pattern[str]] = re.compile(r"[\s\-]")

PLATE_INVALID_MESSAGE: Final[str] = (
    'Plate number may only contain letters, numbers, hyphens, spaces, and "&".'
)


def plate_identity_key(plate_number: str) -> str:
    """
    Build a comparison key for uniqueness.

    Spaces and hyphens are ignored so LAB-7523 matches LAB7523 / LAB 7523.
    Ampersand is kept as a meaningful character.
    """
    return _FORMAT_CHARS.sub("", (plate_number or "").strip().upper())


def normalize_plate_number(plate_number: str) -> str:
    """
    Validate and normalize a plate number for storage.

    Rules:
        - Trim leading/trailing whitespace
        - Uppercase
        - Allow letters, digits, hyphen, spaces, and &
        - Reject all other characters
        - Must contain at least one letter or digit

    Args:
        plate_number: Raw plate value from the user or API.

    Returns:
        Normalized plate number (uppercase; hyphen/space/& preserved).

    Raises:
        ValueError: If empty or contains disallowed characters.
    """
    normalized = (plate_number or "").strip().upper()
    if not normalized:
        raise ValueError("Plate number is required.")
    if not _PLATE_PATTERN.fullmatch(normalized):
        raise ValueError(PLATE_INVALID_MESSAGE)
    if not _HAS_LETTER_OR_DIGIT.search(normalized):
        raise ValueError(PLATE_INVALID_MESSAGE)
    return normalized
