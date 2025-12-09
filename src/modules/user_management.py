"""User management screen for Finance role."""
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
    if current_user.get("role", "").lower() not in {"finance"}:
        st.error("You do not have permission to manage users.")
        return

    path = db_path or str(DEFAULT_DB_PATH)
    st.title("User Management")
    st.caption("Add, edit, and manage system users.")

    render_add_user_form(path)
    st.divider()
    render_user_list(path)


def render_add_user_form(db_path: str) -> None:
    """Render form to add a new user."""
    st.subheader("Add New User")
    with st.form("add_user_form"):
        username = st.text_input("Username", key="new_username")
        password = st.text_input("Password", type="password", key="new_password")
        role = st.selectbox(
            "Role",
            ["user", "supervisor", "purchaser", "finance"],
            key="new_role",
        )
        submitted = st.form_submit_button("Create User")

    if submitted:
        if not username.strip() or not password.strip():
            st.error("Username and password are required.")
            return
        try:
            hashed = hash_password(password)
            create_user(db_path, username.strip(), hashed, role)
            st.success(f"User '{username}' created.")
            st.rerun()
        except Exception as error:
            st.error(str(error))


def render_user_list(db_path: str) -> None:
    """Display list of users with edit/deactivate options."""
    st.subheader("All Users")
    users = safe_list_users(db_path)
    if not users:
        st.info("No users found.")
        return

    for user in users:
        status = "Active" if user["is_active"] else "Inactive"
        status_color = "🟢" if user["is_active"] else "🔴"
        cols = st.columns([2, 2, 2, 2, 2])
        cols[0].markdown(f"**{user['username']}**")
        cols[1].write(f"{status_color} {status}")
        cols[2].write(user["role"].title())
        cols[3].write(user["created_at"])

        if user["is_active"]:
            if cols[4].button("Deactivate", key=f"deact_{user['id']}"):
                try:
                    soft_delete_user(db_path, user["id"])
                    st.success(f"User '{user['username']}' deactivated.")
                    st.rerun()
                except Exception as error:
                    st.error(str(error))
        else:
            if cols[4].button("Reactivate", key=f"react_{user['id']}"):
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
    role_options = ["user", "supervisor", "purchaser", "finance"]
    current_role = user["role"].lower()
    try:
        role_index = role_options.index(current_role)
    except ValueError:
        role_index = 0  # Default to "user" if role not found
    
    with st.form(f"edit_user_{user['id']}"):
        new_username = st.text_input("Username", value=user["username"], key=f"edit_username_{user['id']}")
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
            updates = {}
            if new_username != user["username"]:
                updates["username"] = new_username.strip()
            if new_role.lower() != user["role"].lower():
                updates["role"] = new_role
            if new_password.strip():
                updates["hashed_password"] = hash_password(new_password)
            if updates:
                if "username" in updates:
                    update_user(db_path, user["id"], username=updates["username"])
                if "role" in updates:
                    update_user(db_path, user["id"], role=updates["role"])
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

