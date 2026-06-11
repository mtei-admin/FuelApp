Fuel Requisition System (Prototype)

Prerequisites:
- Python 3.11+ installed.
- PowerShell or bash terminal.

Installation:
1) Create/activate a virtual environment (python -m venv .venv && .venv\Scripts\activate on Windows).
2) Install dependencies: pip install -r REQUIREMENTS.TXT

Running the app:
- Development entry point: python app.py (initializes data/fuel_system.db)
- Streamlit launcher: run_app.bat will be provided once UI is built.
 - Seed admin user: python init_admin.py (creates/updates Finance admin)
 - Streamlit (recommended): run_app.bat (serves on 0.0.0.0:8501)

Default credentials:
- None yet; admin seeding will be added with auth implementation.

Project structure:
- app.py                # Entry point, ensures DB is initialized
- data/                 # SQLite database files (created at runtime)
- src/
  - __init__.py         # Package marker
  - auth.py             # Authentication helpers (bcrypt hash/verify)
  - database.py         # Database initialization, base tables, and CRUD helpers
  - modules/            # Streamlit screens
    - __init__.py
    - master_data.py    # Vendors/cars management (create/reactivate, soft delete)
    - requests.py       # Fuel requests submission + history
    - approvals.py      # Approver approvals (approve/reject)
    - purchasing.py     # PO generation and receiving
    - billing.py        # Billing with invoice capture
    - reports.py        # Status-based summary view
  - utils/              # Helper utilities
    - __init__.py
    - pdf_gen.py        # Purchase order PDF rendering (jinja2 + xhtml2pdf)

Notes:
- All database writes must use parameterized queries and soft deletes for master data.
- Use `@st.cache_data` only for heavy read queries, not transactional updates.

