"""User management screen for Superuser only (add, modify, delete users)."""
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

from src.auth import hash_password
from src.database import (
    create_user,
    list_users,
    reactivate_user,
    soft_delete_user,
    update_user,
)

DEFAULT_DB_PATH = Path("data") / "fuel_system.db"


def render(db_path: Optional[str] = None, current_user: Optional[Dict[str, str]] = None) -> None:
    """
    Render the user management UI.

    Args:
        db_path: Optional database path override.
        current_user: Dict with user context (id, username, role).
    """
    if not current_user:
        st.error("User context missing.")
        return
    if current_user.get("role", "").lower() != "superuser":
        st.error("Only Superuser can add, modify, or delete users.")
        return

    path = db_path or str(DEFAULT_DB_PATH)
    st.title("User Management")
    st.caption("Add, edit, and manage system users.")

    render_add_user_form(path)
    render_user_list(path)


def render_add_user_form(db_path: str) -> None:
    """Render form to add a new user."""
    # Initialize session state for form visibility
    if "show_add_user_form" not in st.session_state:
        st.session_state.show_add_user_form = False
    
    # ADD USER button
    if st.button("➕ ADD USER", key="add_user_button", use_container_width=False):
        st.session_state.show_add_user_form = True
        st.rerun()
    
    # Show form only if session state is True
    if st.session_state.show_add_user_form:
        with st.form("add_user_form", clear_on_submit=False):
            st.subheader("Add New User")
            username = st.text_input("Username", key="new_username")
            full_name = st.text_input("Full Name", key="new_full_name", help="Required. Full name of the user.")
            email = st.text_input("Email", key="new_email", help="Optional. Used for password reset.")
            password = st.text_input("Password", type="password", key="new_password")
            role = st.selectbox(
                "Role",
                ["user", "approver", "purchaser", "accounting", "superuser"],
                key="new_role",
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("Create User", use_container_width=True)
            with col2:
                cancelled = st.form_submit_button("Cancel", use_container_width=True)

        if cancelled:
            st.session_state.show_add_user_form = False
            st.rerun()

        if submitted:
            if not username.strip() or not password.strip():
                st.error("Username and password are required.")
                return
            if not full_name.strip():
                st.error("Full name is required.")
                return
            try:
                hashed = hash_password(password)
                create_user(db_path, username.strip(), hashed, role, full_name.strip(), email=(email or "").strip() or None)
                st.session_state.show_add_user_form = False
                st.success(f"User '{username}' created.")
                st.rerun()
            except Exception as error:
                st.error(str(error))
    
    st.divider()


def render_user_list(db_path: str) -> None:
    """Display list of users with edit/deactivate options."""
    st.subheader("All Users")
    users = safe_list_users(db_path)
    if not users:
        st.info("No users found.")
        return

    # Header row
    header_cols = st.columns([2, 2, 2, 2, 2, 2])
    header_cols[0].markdown("**Username**")
    header_cols[1].markdown("**Full Name**")
    header_cols[2].markdown("**Email**")
    header_cols[3].markdown("**Role**")
    header_cols[4].markdown("**Status**")
    header_cols[5].markdown("**Action**")
    st.divider()

    for user in users:
        status = "Active" if user["is_active"] else "Inactive"
        status_color = "🟢" if user["is_active"] else "🔴"
        full_name_display = user.get("full_name") or user.get("username", "—")
        email_display = user.get("email") or "—"
        cols = st.columns([2, 2, 2, 2, 2, 2])
        cols[0].markdown(f"**{user['username']}**")
        cols[1].write(full_name_display)
        cols[2].write(email_display)
        cols[3].write(user["role"].title())
        cols[4].write(f"{status_color} {status}")

        if user["is_active"]:
            if cols[5].button("Deactivate", key=f"deact_{user['id']}", use_container_width=True):
                try:
                    soft_delete_user(db_path, user["id"])
                    st.success(f"User '{user['username']}' deactivated.")
                    st.rerun()
                except Exception as error:
                    st.error(str(error))
        else:
            if cols[5].button("Reactivate", key=f"react_{user['id']}", use_container_width=True):
                try:
                    reactivate_user(db_path, user["id"])
                    st.success(f"User '{user['username']}' reactivated.")
                    st.rerun()
                except Exception as error:
                    st.error(str(error))

        with st.expander(f"Edit {user['username']}", expanded=False):
            render_edit_user_form(db_path, user)


def render_edit_user_form(db_path: str, user: Dict[str, str]) -> None:
    """Render form to edit user details."""
    role_options = ["user", "approver", "purchaser", "accounting", "superuser"]
    current_role = user["role"].lower()
    try:
        role_index = role_options.index(current_role)
    except ValueError:
        role_index = 0  # Default to "user" if role not found
    
    with st.form(f"edit_user_{user['id']}"):
        new_username = st.text_input("Username", value=user["username"], key=f"edit_username_{user['id']}")
        new_full_name = st.text_input(
            "Full Name", 
            value=user.get("full_name", ""), 
            key=f"edit_full_name_{user['id']}",
            help="Required. Full name of the user."
        )
        new_email = st.text_input(
            "Email",
            value=user.get("email") or "",
            key=f"edit_email_{user['id']}",
            help="Optional. Used for password reset.",
        )
        new_role = st.selectbox(
            "Role",
            role_options,
            index=role_index,
            key=f"edit_role_{user['id']}",
        )
        new_password = st.text_input(
            "New Password (leave blank to keep current)",
            type="password",
            key=f"edit_password_{user['id']}",
        )
        submitted = st.form_submit_button("Update User")

    if submitted:
        try:
            if not new_full_name.strip():
                st.error("Full name is required.")
                return
            updates = {}
            if new_username != user["username"]:
                updates["username"] = new_username.strip()
            if new_full_name != user.get("full_name", ""):
                updates["full_name"] = new_full_name.strip()
            if new_role.lower() != user["role"].lower():
                updates["role"] = new_role
            if (new_email or "").strip() != (user.get("email") or ""):
                updates["email"] = (new_email or "").strip() or None
            if new_password.strip():
                updates["hashed_password"] = hash_password(new_password)
            if updates:
                if "username" in updates:
                    update_user(db_path, user["id"], username=updates["username"])
                if "full_name" in updates:
                    update_user(db_path, user["id"], full_name=updates["full_name"])
                if "role" in updates:
                    update_user(db_path, user["id"], role=updates["role"])
                if "email" in updates:
                    update_user(db_path, user["id"], email=updates["email"])
                if "hashed_password" in updates:
                    update_user(db_path, user["id"], hashed_password=updates["hashed_password"])
                st.success(f"User '{new_username}' updated.")
                st.rerun()
            else:
                st.info("No changes made.")
        except Exception as error:
            st.error(str(error))


def safe_list_users(db_path: str) -> List[dict]:
    """Safely list users with error handling."""
    try:
        return list_users(db_path)
    except Exception as error:
        st.error(f"Unable to load users: {error}")
        return []

