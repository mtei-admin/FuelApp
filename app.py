"""Streamlit entry point for the Fuel Requisition System."""
import os
from pathlib import Path
from typing import Optional

# Load .env so SMTP and APP_BASE_URL are available for Forgot Password
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st
import streamlit.components.v1 as components

from src.auth import hash_password, verify_password
from src.database import (
    create_password_reset_token,
    create_user_session,
    delete_user_session,
    fetch_user_by_email,
    fetch_user_by_id,
    fetch_user_by_username,
    find_valid_reset_token,
    get_user_id_from_session,
    init_database,
    invalidate_reset_token,
    list_pending_requisitions,
    update_user,
)
from src.utils.email import send_password_reset_email
from src.modules.approvals import render as render_approvals
from src.modules.billing import render as render_billing
from src.modules.dashboard import render as render_dashboard
from src.modules.master_data import render as render_master_data
from src.modules.purchasing import render as render_purchasing
from src.modules.reports import render as render_reports
from src.modules.requests import render as render_requests
from src.modules.user_management import render as render_user_management

# ============================================================================
# TEMPORARY STYLING TOGGLE
# ============================================================================
# Set to False to disable custom styling and revert to default Streamlit theme
# To completely remove: Delete .streamlit/config.toml and comment out the import/apply lines below
ENABLE_CUSTOM_STYLING = True


DB_PATH = Path("data") / "fuel_system.db"
SESSION_USER_KEY = "current_user"
SESSION_PAGE_KEY = "selected_page"
SESSION_COOKIE_NAME = "fuel_session"

# Default landing page per role after login (role lower-case -> page key)
ROLE_DEFAULT_PAGE = {
    "user": "requests",
    "approver": "approvals",
    "purchaser": "purchasing",
    "accounting": "reports",
    "superuser": "dashboard",
}


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
    # Create session for cookie-based persistence across refresh
    token = create_user_session(str(DB_PATH), user["id"])
    st.session_state["_set_cookie"] = token
    return None


def _inject_set_cookie_script(token: str) -> None:
    """Set session cookie in the browser (path=/, 7 days)."""
    name = SESSION_COOKIE_NAME
    max_age = 7 * 24 * 60 * 60
    # Escape for use inside JS string
    safe_token = token.replace("\\", "\\\\").replace("'", "\\'")
    components.html(
        f"""
        <script>
        (function() {{
            document.cookie = "{name}=" + "{safe_token}" + "; path=/; max-age={max_age}; SameSite=Lax";
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def _inject_clear_cookie_script() -> None:
    """Clear session cookie in the browser."""
    name = SESSION_COOKIE_NAME
    components.html(
        f"""
        <script>
        (function() {{
            document.cookie = "{name}=; path=/; max-age=0";
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def _inject_pwa_meta() -> None:
    """Inject manifest link and register service worker for PWA installability."""
    components.html(
        """
        <script>
        (function() {
            var link = document.createElement('link');
            link.rel = 'manifest';
            link.href = '/manifest.webmanifest';
            document.head.appendChild(link);
            if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) {
                navigator.serviceWorker.register('/sw.js').catch(function() {});
            }
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def _inject_cookie_redirect_script() -> None:
    """If session cookie exists, redirect to ?_session=TOKEN so Python can restore session."""
    name = SESSION_COOKIE_NAME
    components.html(
        f"""
        <script>
        (function() {{
            var c = document.cookie.split(';').filter(function(s) {{
                return s.trim().indexOf("{name}=") === 0;
            }})[0];
            if (c) {{
                var val = c.split('=').slice(1).join('=').trim();
                if (val && window.location.search.indexOf('_session=') === -1) {{
                    var sep = window.location.search ? '&' : '?';
                    window.location.href = window.location.pathname + window.location.search + sep + '_session=' + encodeURIComponent(val);
                }}
            }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def render_reset_password(token: str) -> None:
    """Render set-new-password form when user arrives via reset link."""
    from pathlib import Path
    logo_path = Path("assets") / "mte_logo.png"
    if logo_path.exists():
        col_logo1, col_logo2, col_logo3 = st.columns([3, 1, 3])
        with col_logo2:
            st.image(str(logo_path), width=150)
        st.write("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("Set New Password")
        st.caption("Enter your new password below.")
        user_id = find_valid_reset_token(str(DB_PATH), token)
        if not user_id:
            st.error("This reset link is invalid or has expired. Please request a new one.")
            if st.button("Back to login"):
                st.query_params.clear()
                st.rerun()
            return
        with st.form("reset_password_form"):
            new_password = st.text_input("New password", type="password", key="reset_new_password")
            confirm = st.text_input("Confirm password", type="password", key="reset_confirm_password")
            submitted = st.form_submit_button("Set password", use_container_width=True)
        if submitted:
            if not new_password or not confirm:
                st.error("Please fill in both fields.")
            elif new_password != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    hashed = hash_password(new_password)
                    update_user(str(DB_PATH), user_id, hashed_password=hashed)
                    invalidate_reset_token(str(DB_PATH), token)
                    st.success("Password updated. You can now sign in.")
                    st.session_state["login_success_message"] = "Password updated. Please sign in."
                    st.query_params.clear()
                    st.rerun()
                except Exception as e:
                    st.error(str(e))


def render_forgot_password() -> None:
    """Render forgot-password form (email input, then generic message)."""
    from pathlib import Path
    import base64

    # Show all company logos with same spacing/sizing as login screen
    assets_dir = Path("assets")
    logo_files = ["mte_logo.png", "planters_logo.png", "DSRDC_logo.png", "eskina_logo.png", "dic_logo.png"]
    logo_paths = [assets_dir / f for f in logo_files if (assets_dir / f).exists()]
    if logo_paths:
        img_tags = []
        for path in logo_paths:
            with open(path, "rb") as img_file:
                b64 = base64.b64encode(img_file.read()).decode("utf-8")
            ext = path.suffix.lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            img_tags.append(
                f'<img src="data:{mime};base64,{b64}" '
                f'style="width:100px; height:auto; display:block;" alt="" />'
            )
        logos_html = (
            '<div style="display:flex; align-items:center; justify-content:center; '
            f'gap:8px; flex-wrap:nowrap;">{"".join(img_tags)}</div>'
        )
        st.markdown(logos_html, unsafe_allow_html=True)
        st.write("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("Forgot Password")
        st.caption("Enter the email address for your account.")
        with st.form("forgot_form"):
            email = st.text_input("Email", key="forgot_email", type="default")
            submitted = st.form_submit_button("Send reset link", use_container_width=True)
        if submitted and email and email.strip():
            user = fetch_user_by_email(str(DB_PATH), email.strip())
            if user:
                try:
                    raw_token, _ = create_password_reset_token(str(DB_PATH), user["id"])
                    base_url = os.environ.get("APP_BASE_URL", "").rstrip("/")
                    if not base_url and hasattr(st, "get_option"):
                        try:
                            base_url = st.get_option("server.baseUrlPath") or ""
                        except Exception:
                            base_url = ""
                    if not base_url:
                        base_url = "http://localhost:8501"
                    reset_link = f"{base_url}?token={raw_token}"
                    err = send_password_reset_email(user.get("email") or email.strip(), reset_link)
                    if err:
                        pass  # Log but still show generic message
                except Exception:
                    pass
            st.info("If an account exists for that email, you will receive a reset link shortly. Check your inbox and spam folder.")
        if st.button("Back to login", key="forgot_back"):
            st.query_params.clear()
            st.rerun()


def render_login() -> None:
    """Render the login form."""
    from pathlib import Path
    import base64

    if st.session_state.pop("_clear_cookie", False):
        _inject_clear_cookie_script()

    # Show all company logos in a single centered row on the login screen
    assets_dir = Path("assets")
    logo_files = ["mte_logo.png", "planters_logo.png", "DSRDC_logo.png", "eskina_logo.png", "dic_logo.png"]
    logo_paths = [assets_dir / f for f in logo_files if (assets_dir / f).exists()]
    if logo_paths:
        img_tags = []
        for path in logo_paths:
            with open(path, "rb") as img_file:
                b64 = base64.b64encode(img_file.read()).decode("utf-8")
            ext = path.suffix.lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            img_tags.append(
                f'<img src="data:{mime};base64,{b64}" '
                f'style="width:100px; height:auto; display:block;" alt="" />'
            )
        logos_html = (
            '<div style="display:flex; align-items:center; justify-content:center; '
            f'gap:8px; flex-wrap:nowrap;">{"".join(img_tags)}</div>'
        )
        st.markdown(logos_html, unsafe_allow_html=True)
        st.write("")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.get("login_success_message"):
            st.success(st.session_state.pop("login_success_message", None))
        st.title("Fuel Requisition System")
        st.caption("Please sign in to continue.")
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)
        st.markdown(
            '<p style="text-align: right;"><a href="?forgot=1">Forgot password?</a></p>',
            unsafe_allow_html=True,
        )
    if submitted:
        error = handle_login(username, password)
        if error:
            st.error(error)
        else:
            st.success("Login successful.")
            st.rerun()


def render_sidebar(role: str, db_path: str) -> str:
    """
    Render the sidebar navigation based on role.

    Args:
        role: Current user's role.
        db_path: Database path for fetching pending count.

    Returns:
        The selected page identifier.
    """
    st.sidebar.title("Navigation")
    st.sidebar.write(f"Role: {role.title()}")
    if st.sidebar.button("Log out", key="logout_button"):
        session_token = st.session_state.pop("_session_token", None)
        if session_token:
            try:
                delete_user_session(str(DB_PATH), session_token)
            except Exception:
                pass
        st.session_state["_clear_cookie"] = True
        st.session_state[SESSION_USER_KEY] = None
        for key in (SESSION_PAGE_KEY, "sidebar_page_radio"):
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    base_pages = {
        "dashboard": "Dashboard",
        "requests": "Requests",
        "approvals": "Approvals",
        "purchasing": "Purchasing",
        "billing": "Billing",
        "reports": "Reports",
        "master_data": "Master Data",
        "user_management": "User Management",
    }

    # Only superuser sees User Management (add/modify/delete users)
    accounting_pages = [
        "dashboard",
        "requests",
        "approvals",
        "purchasing",
        "billing",
        "reports",
        "master_data",
    ]
    all_pages = accounting_pages + ["user_management"]
    role_pages = {
        "user": ["requests"],
        "approver": ["requests", "approvals", "master_data"],
        "purchaser": ["requests", "approvals", "purchasing", "billing"],
        "accounting": accounting_pages,
        "superuser": all_pages,
    }

    # Get pending approvals count for higher roles
    pending_count = 0
    role_lower = role.lower()
    if role_lower in ["approver", "purchaser", "accounting", "superuser"]:
        try:
            pending_requisitions = list_pending_requisitions(db_path)
            pending_count = len(pending_requisitions)
        except Exception:
            pending_count = 0

    # Format page labels with notification badge for Approvals
    def format_page_label(key: str) -> str:
        label = base_pages.get(key, key)
        if key == "approvals" and pending_count > 0 and role_lower in ["approver", "purchaser", "accounting", "superuser"]:
            # Add badge notification with smaller red circle and count
            # Using smaller Unicode circle (appears smaller than emoji)
            return f"{label} ● ({pending_count})"
        return label

    allowed_keys = role_pages.get(role_lower, list(base_pages.keys()))
    allowed_pages = {key: format_page_label(key) for key in allowed_keys}

    # Default landing page for this role (first time after login or when selection not allowed)
    default_for_role = ROLE_DEFAULT_PAGE.get(role_lower, allowed_keys[0] if allowed_keys else "dashboard")
    if default_for_role not in allowed_keys:
        default_for_role = allowed_keys[0] if allowed_keys else "dashboard"
    current = st.session_state.get(SESSION_PAGE_KEY)
    if current not in allowed_keys:
        st.session_state[SESSION_PAGE_KEY] = default_for_role
        current = default_for_role

    # Radio default index from current selection
    try:
        default_index = list(allowed_pages.keys()).index(current)
    except ValueError:
        default_index = 0

    # Get the selected page from radio button; persist for next run
    selected_page = st.sidebar.radio(
        "Go to",
        list(allowed_pages.keys()),
        format_func=lambda k: allowed_pages[k],
        index=default_index,
        key="sidebar_page_radio",
    )
    st.session_state[SESSION_PAGE_KEY] = selected_page
    
    # Add spacing before logo to push it to the bottom
    st.sidebar.write("")  # Add some spacing
    st.sidebar.write("")  # Add more spacing
    
    # Add MTE logo at the very bottom center of sidebar
    logo_path = Path("assets") / "mte_logo.png"
    if logo_path.exists():
        # Use columns to center the logo
        col1, col2, col3 = st.sidebar.columns([1, 2, 1])
        with col2:
            st.image(str(logo_path), width=150)
    
    return selected_page


def render_page(page: str, db_path: str, current_user: dict) -> None:
    """Dispatch to the selected page renderer."""
    if page == "dashboard":
        render_dashboard(db_path=db_path, current_user=current_user)
    elif page == "requests":
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
    
    # Apply custom styling if enabled
    if ENABLE_CUSTOM_STYLING:
        try:
            from src.utils.styling import apply_custom_styles
            apply_custom_styles()
        except ImportError:
            # Silently fail if styling module doesn't exist
            pass
    
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    init_database(str(DB_PATH))
    ensure_session_state()

    current_user = st.session_state[SESSION_USER_KEY]

    # Restore session from cookie (?_session=TOKEN) after refresh
    if not current_user:
        token_param = st.query_params.get("_session")
        session_token = token_param[0] if isinstance(token_param, list) and token_param else (token_param if isinstance(token_param, str) else None)
        if session_token:
            user_id = get_user_id_from_session(str(DB_PATH), session_token)
            if user_id:
                user = fetch_user_by_id(str(DB_PATH), user_id)
                if user and user.get("is_active"):
                    st.session_state[SESSION_USER_KEY] = {
                        "id": user["id"],
                        "username": user["username"],
                        "role": user["role"],
                    }
                    st.session_state["_session_token"] = session_token
                    try:
                        del st.query_params["_session"]
                    except (KeyError, TypeError):
                        pass
                    st.rerun()
            # Invalid/expired token: fall through to show login

        token = st.query_params.get("token")
        if token:
            render_reset_password(token)
            return
        if st.query_params.get("forgot"):
            render_forgot_password()
            return
        _inject_cookie_redirect_script()
        render_login()
        return

    # After login: set cookie in browser so refresh can restore session
    if st.session_state.get("_set_cookie"):
        _inject_set_cookie_script(st.session_state["_set_cookie"])
        del st.session_state["_set_cookie"]
        st.rerun()

    # PWA: manifest + service worker for "Add to Home Screen" / install
    _inject_pwa_meta()

    st.sidebar.success(get_user_display_name(current_user))
    page = render_sidebar(current_user["role"], str(DB_PATH))
    render_page(page, str(DB_PATH), current_user)


if __name__ == "__main__":
    main()

