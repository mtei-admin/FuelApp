"""Application settings loaded from environment variables."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "fuel_system.db"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

SESSION_COOKIE_NAME = "fuel_api_session"
SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60

API_PREFIX = "/api"
CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")


def get_app_base_url() -> str:
    """Return the public base URL for links in emails."""
    return os.environ.get("APP_BASE_URL", "http://localhost:5173").rstrip("/")


def is_https_base_url() -> bool:
    """True when APP_BASE_URL uses HTTPS (production behind IIS)."""
    return get_app_base_url().lower().startswith("https://")


def get_session_cookie_secure() -> bool:
    """
    Whether the session cookie requires HTTPS.

    Set SESSION_COOKIE_SECURE=true in .env to force; otherwise inferred from APP_BASE_URL.
    """
    explicit = os.environ.get("SESSION_COOKIE_SECURE", "").lower()
    if explicit in ("1", "true", "yes"):
        return True
    if explicit in ("0", "false", "no"):
        return False
    return is_https_base_url()


def get_session_cookie_samesite() -> str:
    """
    SameSite policy for the session cookie.

    Use SESSION_COOKIE_SAMESITE=none when the React app (e.g. Vercel) and API
  (e.g. fuelapp-api.mteinc.net) are on different sites. Requires Secure=true.
    """
    explicit = os.environ.get("SESSION_COOKIE_SAMESITE", "").lower()
    if explicit in ("lax", "strict", "none"):
        return explicit
    return "lax"


def get_cors_origins() -> list[str]:
    """CORS allowlist for dev servers and the configured public base URL."""
    origins = [origin.strip() for origin in CORS_ORIGINS if origin.strip()]
    base = get_app_base_url()
    if base and base not in origins:
        origins.append(base)
    return origins


def should_serve_frontend() -> bool:
    """
    Whether uvicorn should serve the React build (LAN mode without IIS).

    SERVE_FRONTEND=false disables; true forces when dist exists; auto serves when dist exists.
    """
    mode = os.environ.get("SERVE_FRONTEND", "auto").lower()
    if mode in ("0", "false", "no"):
        return False
    if not (FRONTEND_DIST / "index.html").is_file():
        return False
    if mode in ("1", "true", "yes"):
        return True
    return mode == "auto"
