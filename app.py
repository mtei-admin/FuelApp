"""Streamlit entry point for the Fuel Requisition System."""
from pathlib import Path
from typing import Optional

import streamlit as st

from src.auth import verify_password
from src.database import fetch_user_by_username, init_database
from src.modules.approvals import render as render_approvals
from src.modules.billing import render as render_billing
from src.modules.master_data import render as render_master_data
from src.modules.purchasing import render as render_purchasing
from src.modules.reports import render as render_reports
from src.modules.requests import render as render_requests
from src.modules.user_management import render as render_user_management


DB_PATH = Path("data") / "fuel_system.db"
SESSION_USER_KEY = "current_user"


def ensure_session_state() -> None:
    """Initialize required session state keys."""
    if SESSION_USER_KEY not in st.session_state:
        st.session_state[SESSION_USER_KEY] = None


def get_user_display_name(user: dict) -> str:
    """Return a friendly display string for the logged-in user."""
    return f"{user.get('username', '')} ({user.get('role', '').title()})"


def handle_login(username: str, password: str) -> Optional[str]:
    """
    Attempt to authenticate the user.

    Args:
        username: Entered username.
        password: Entered password.

    Returns:
        None on success, or an error message string on failure.
    """
    user = fetch_user_by_username(str(DB_PATH), username)
    if not user or not user.get("is_active"):
        return "Invalid credentials or inactive account."

    hashed_password = user.get("hashed_password", "")
    if not verify_password(password, hashed_password):
        return "Invalid credentials or inactive account."

    st.session_state[SESSION_USER_KEY] = {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
    }
    return None


def render_login() -> None:
    """Render the login form."""
    st.title("Fuel Requisition System")
    st.caption("Please sign in to continue.")

    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Sign In")

    if submitted:
        error = handle_login(username, password)
        if error:
            st.error(error)
        else:
            st.success("Login successful.")
            st.rerun()


def render_sidebar(role: str) -> str:
    """
    Render the sidebar navigation based on role.

    Args:
        role: Current user's role.

    Returns:
        The selected page identifier.
    """
    st.sidebar.title("Navigation")
    st.sidebar.write(f"Role: {role.title()}")
    if st.sidebar.button("Log out", key="logout_button"):
        st.session_state[SESSION_USER_KEY] = None
        st.rerun()

    base_pages = {
        "requests": "Requests",
        "approvals": "Approvals",
        "purchasing": "Purchasing",
        "billing": "Billing",
        "reports": "Reports",
        "master_data": "Master Data",
        "user_management": "User Management",
    }

    role_pages = {
        "user": ["requests"],
        "supervisor": ["requests", "approvals"],
        "purchaser": ["requests", "approvals", "purchasing"],
        "finance": [
            "requests",
            "approvals",
            "purchasing",
            "billing",
            "reports",
            "master_data",
            "user_management",
        ],
    }

    allowed_keys = role_pages.get(role.lower(), list(base_pages.keys()))
    allowed_pages = {key: base_pages[key] for key in allowed_keys}
    return st.sidebar.radio("Go to", list(allowed_pages.keys()), format_func=allowed_pages.get)


def render_page(page: str, db_path: str, current_user: dict) -> None:
    """Dispatch to the selected page renderer."""
    if page == "requests":
        render_requests(db_path=db_path, current_user=current_user)
    elif page == "approvals":
        render_approvals(db_path=db_path, current_user=current_user)
    elif page == "purchasing":
        render_purchasing(db_path=db_path, current_user=current_user)
    elif page == "billing":
        render_billing(db_path=db_path, current_user=current_user)
    elif page == "reports":
        render_reports(db_path=db_path, current_user=current_user)
    elif page == "master_data":
        render_master_data(db_path=db_path)
    elif page == "user_management":
        render_user_management(db_path=db_path, current_user=current_user)
    else:
        st.warning("Unknown page selected.")


def main() -> None:
    """Initialize the app and route based on authentication state."""
    st.set_page_config(page_title="Fuel Requisition System", layout="wide")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    init_database(str(DB_PATH))
    ensure_session_state()

    current_user = st.session_state[SESSION_USER_KEY]
    if not current_user:
        render_login()
        return

    st.sidebar.success(get_user_display_name(current_user))
    page = render_sidebar(current_user["role"])
    render_page(page, str(DB_PATH), current_user)


if __name__ == "__main__":
    main()

