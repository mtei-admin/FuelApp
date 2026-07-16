"""HTTP request helpers for the API."""
from typing import Optional

from fastapi import Request


def get_client_ip(request: Request) -> Optional[str]:
    """
    Resolve the client IP, honoring X-Forwarded-For from IIS/reverse proxies.

    Args:
        request: Incoming FastAPI request.

    Returns:
        Client IP string or None if unavailable.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
