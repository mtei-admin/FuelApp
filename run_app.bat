@echo off
rem Launch Streamlit for the Fuel Requisition System
setlocal

if not exist ".venv" (
    echo [WARN] No virtual environment detected. Ensure dependencies are installed.
)

python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501

endlocal

