"""Authentication helpers for the Fuel Requisition System."""
import bcrypt


def hash_password(plain_text: str) -> str:
    """
    Hash a plain-text password securely.

    Args:
        plain_text: The password provided by the user.

    Returns:
        The hashed password string (utf-8 decoded).
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_text.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_text: str, hashed_password: str) -> bool:
    """
    Verify that a provided password matches the stored hash.

    Args:
        plain_text: The password provided by the user.
        hashed_password: The stored hashed password.

    Returns:
        True if the password matches; otherwise False.
    """
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(plain_text.encode("utf-8"), hashed_bytes)

