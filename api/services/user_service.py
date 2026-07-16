"""User administration service (superuser only)."""
from typing import Any, Dict, List, Optional

from src.audit import USER_AUDIT_FIELDS, log_audit, log_field_update, pick_fields
from src.auth import hash_password
from src.database import (
    assert_company_assignable,
    create_user,
    fetch_user_by_id,
    list_users,
    reactivate_user,
    soft_delete_user,
    update_user,
)

VALID_ROLES = {"encoder", "approver", "purchaser", "accounting", "superuser"}


def _user_snapshot(user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return audit-safe user fields (never passwords)."""
    return pick_fields(user, USER_AUDIT_FIELDS)


def get_all_users(db_path: str) -> List[Dict[str, Any]]:
    """Return all users (active and inactive)."""
    return list_users(db_path)


def enroll_user(
    db_path: str,
    username: str,
    password: str,
    full_name: str,
    role: str,
    email: Optional[str] = None,
    company: Optional[str] = None,
    actor: Optional[Dict[str, Any]] = None,
) -> int:
    """Create a new user with a bcrypt-hashed password."""
    role_normalized = role.lower()
    if role_normalized == "user":
        role_normalized = "encoder"
    if role_normalized not in VALID_ROLES:
        raise RuntimeError(f"Invalid role: {role}")
    if role_normalized == "encoder" and not (company or "").strip():
        raise RuntimeError("Company is required for encoder accounts.")
    company_value = None
    if role_normalized == "encoder":
        company_value = assert_company_assignable(db_path, company or "")

    hashed = hash_password(password)
    user_id = create_user(
        db_path,
        username.strip(),
        hashed,
        role_normalized,
        full_name.strip(),
        email=(email or "").strip() or None,
        company=company_value,
    )
    created = fetch_user_by_id(db_path, user_id)
    log_audit(
        db_path,
        "user",
        user_id,
        "created",
        actor,
        new_values=_user_snapshot(created),
    )
    return user_id


def save_user(
    db_path: str,
    user_id: int,
    username: Optional[str] = None,
    full_name: Optional[str] = None,
    role: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    company: Optional[str] = None,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Update user profile fields."""
    if role is not None:
        role = role.lower()
        if role == "user":
            role = "encoder"
    if role is not None and role not in VALID_ROLES:
        raise RuntimeError(f"Invalid role: {role}")

    before = fetch_user_by_id(db_path, user_id)
    effective_role = (role or before.get("role") or "").lower()
    if effective_role == "user":
        effective_role = "encoder"
    if role is not None and effective_role == "encoder" and company is None:
        assert_company_assignable(
            db_path,
            before.get("company") or "",
            previous_code=before.get("company"),
        )
    if username is not None:
        update_user(db_path, user_id, username=username.strip())
    if full_name is not None:
        update_user(db_path, user_id, full_name=full_name.strip())
    if role is not None:
        update_user(db_path, user_id, role=role)
    if email is not None:
        update_user(db_path, user_id, email=email)
    if company is not None:
        effective_role = (role or before.get("role") or "").lower()
        if effective_role == "user":
            effective_role = "encoder"
        if effective_role == "encoder":
            previous_company = before.get("company")
            company_value = assert_company_assignable(
                db_path, company, previous_code=previous_company
            )
            update_user(db_path, user_id, company=company_value)
        else:
            update_user(db_path, user_id, company=(company or "").strip() or None)
    if password:
        update_user(db_path, user_id, hashed_password=hash_password(password))

    after = fetch_user_by_id(db_path, user_id)
    old_vals, new_vals = {}, {}
    if before and after:
        for key in USER_AUDIT_FIELDS:
            if before.get(key) != after.get(key):
                old_vals[key] = before.get(key)
                new_vals[key] = after.get(key)
    if password:
        new_vals["password_changed"] = True
    if old_vals or new_vals or password:
        log_audit(
            db_path,
            "user",
            user_id,
            "updated",
            actor,
            old_values=old_vals or None,
            new_values=new_vals or None,
        )


def deactivate_user(
    db_path: str,
    user_id: int,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Soft-delete a user account."""
    before = fetch_user_by_id(db_path, user_id)
    soft_delete_user(db_path, user_id)
    after = fetch_user_by_id(db_path, user_id)
    log_field_update(
        db_path,
        "user",
        user_id,
        "deactivated",
        actor,
        before,
        after,
        ["is_active"],
    )


def activate_user(
    db_path: str,
    user_id: int,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Reactivate a deactivated user account."""
    before = fetch_user_by_id(db_path, user_id)
    reactivate_user(db_path, user_id)
    after = fetch_user_by_id(db_path, user_id)
    log_field_update(
        db_path,
        "user",
        user_id,
        "activated",
        actor,
        before,
        after,
        ["is_active"],
    )
