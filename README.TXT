Fuel Requisition System

Prerequisites:
- Python 3.11 or 3.12 (recommended). Python 3.14 may work but is not tested.
- Node.js LTS (for production frontend build).
- Windows Server or Windows 10/11 for production deployment.
- PowerShell.

Installation (development):
1) Clone: git clone https://github.com/mtei-admin/FuelApp.git
2) Create venv: py -m venv .venv && .venv\Scripts\activate
3) Install: pip install -r REQUIREMENTS.TXT && pip install -r api\requirements.txt
4) Copy env.example to .env and set APP_BASE_URL / SMTP if using Forgot Password.
5) Seed admin: python init_admin.py
6) Dev servers:
     deploy\run_api.bat       (http://127.0.0.1:8000)
     deploy\run_frontend.bat  (http://localhost:5173)

Production deployment (Windows Server):
- Full guide: DEPLOYMENT.TXT
- Automated install: powershell -ExecutionPolicy Bypass -File deploy\install_windows.ps1
- Build UI: deploy\build_frontend.bat
- Production API (localhost, for IIS): deploy\run_production.bat
- LAN access (no HTTPS): deploy\run_lan.bat
- Windows service (auto-start): deploy\install_service.ps1 (requires NSSM)
- IIS reverse proxy: web.config in project root (see deploy\IIS_SETUP.txt)

Default credentials:
- Created by init_admin.py (default username: accounting). No default password.

Project structure:
- api/                  FastAPI backend (production)
- frontend/             React + TypeScript SPA
- app.py                Legacy Streamlit UI (deprecated; use deploy\run_streamlit.bat)
- data/                 SQLite database (fuel_system.db)
- deploy/               Windows production scripts and IIS config
- src/database.py       Database schema and CRUD (shared by API and legacy Streamlit)
- src/modules/          Legacy Streamlit screens
- src/utils/            PDF generation, email, styling
- pwa/                  PWA manifest and service worker (optional, serve via IIS)
- assets/               Company logos for UI and PO PDFs

See also: MIGRATION.TXT, DEPLOYMENT.TXT, SMTP_SETUP.txt, SCRIPTS_OVERVIEW.TXT
