"""FastAPI application entry point."""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Ensure project root is on sys.path when running: uvicorn api.main:app
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.core.config import (  # noqa: E402
    API_PREFIX,
    DB_PATH,
    FRONTEND_DIST,
    get_cors_origins,
    should_serve_frontend,
)
from api.routers import (  # noqa: E402
    approvals,
    auth,
    billing,
    dashboard,
    documents,
    purchasing,
    reports,
    requisitions,
    vehicles,
    vendors,
)
from src.database import init_database  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database schema on startup."""
    init_database(str(DB_PATH))
    yield


app = FastAPI(
    title="Fuel Requisition System API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(vendors.router, prefix=API_PREFIX)
app.include_router(vehicles.router, prefix=API_PREFIX)
app.include_router(requisitions.router, prefix=API_PREFIX)
app.include_router(approvals.router, prefix=API_PREFIX)
app.include_router(purchasing.router, prefix=API_PREFIX)
app.include_router(billing.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)


@app.get("/api/health")
def health_check() -> dict:
    """Simple health check for load balancers and dev scripts."""
    return {"status": "ok", "service": "fuel-api"}


@app.get("/", include_in_schema=False)
def api_root() -> dict:
    """
    Root response when SERVE_FRONTEND is off (run_production / tunnel mode).

    The React UI is served by IIS, Vercel, or run_lan.bat — not this endpoint.
    """
    if should_serve_frontend():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Not found")
    return {
        "status": "ok",
        "service": "fuel-api",
        "health": "/api/health",
        "hint": "API only. Use run_lan.bat for UI on this server, or Vercel/IIS for production UI.",
    }


def _mount_frontend_spa() -> None:
    """Serve React build for LAN mode (IIS serves static files in production)."""
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="frontend-assets",
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        """Return static files or index.html for client-side routing."""
        if full_path.startswith("api/"):
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")

        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")


if should_serve_frontend():
    _mount_frontend_spa()

