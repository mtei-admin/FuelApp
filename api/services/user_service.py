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
from src.permissions import (
    ADMIN_MANAGE_USERS,
    detect_template,
    effective_permissions,
    normalize_permission_selection,
    permission_summary,
    permissions_require_company,
    serialize_permissions,
    stored_permissions_list,
)


def _user_snapshot(user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return audit-safe user fields (never passwords)."""
    return pick_fields(user, USER_AUDIT_FIELDS)


def _admin_user_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich a database user row for admin API responses."""
    explicit = stored_permissions_list(row)
    template = detect_template(explicit)
    return {
        **row,
        "permissions": explicit,
        "permission_summary": permission_summary(
            effective_permissions(row),
        ),
        "role": template or row.get("role") or "encoder",
    }


def _validate_permissions_update(
    db_path: str,
    user_id: int,
    permissions: List[str],
    company: Optional[str],
    actor: Optional[Dict[str, Any]],
) -> str:
    """
    Validate permission selection and return serialized JSON for storage.

    Raises:
        RuntimeError: When validation fails or last manage-users holder would be removed.
    """
    try:
        explicit = normalize_permission_selection(permissions)
    except ValueError as error:
        raise RuntimeError(str(error)) from error

    if permissions_require_company(explicit) and not (company or "").strip():
        raise RuntimeError(
            "Company is required for users with encode (receipt / CC fill) permissions.",
        )

    if actor and actor.get("id") == user_id:
        if ADMIN_MANAGE_USERS not in explicit:
            before = fetch_user_by_id(db_path, user_id)
            if before and ADMIN_MANAGE_USERS in effective_permissions(before):
                others = 0
                for row in list_users(db_path):
                    if not row.get("is_active") or row["id"] == user_id:
                        continue
                    if ADMIN_MANAGE_USERS in effective_permissions(row):
                        others += 1
                if others == 0:
                    raise RuntimeError(
                        "You cannot remove Manage users from the last admin account.",
                    )

    return serialize_permissions(explicit)


def get_all_users(db_path: str) -> List[Dict[str, Any]]:
    """Return all users (active and inactive) with permission metadata."""
    return [_admin_user_row(row) for row in list_users(db_path)]


def enroll_user(
    db_path: str,
    username: str,
    password: str,
    full_name: str,
    permissions: List[str],
    email: Optional[str] = None,
    company: Optional[str] = None,
    actor: Optional[Dict[str, Any]] = None,
) -> int:
    """Create a new user with a bcrypt-hashed password and explicit permissions."""
    permissions_json = _validate_permissions_update(
        db_path,
        user_id=0,
        permissions=permissions,
        company=company,
        actor=actor,
    )
    explicit = normalize_permission_selection(permissions)
    template = detect_template(explicit)
    role = template or "encoder"

    company_value = None
    if permissions_require_company(explicit):
        company_value = assert_company_assignable(db_path, company or "")

    hashed = hash_password(password)
    user_id = create_user(
        db_path,
        username.strip(),
        hashed,
        role,
        full_name.strip(),
        email=(email or "").strip() or None,
        company=company_value,
        permissions=permissions_json,
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
    permissions: Optional[List[str]] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    company: Optional[str] = None,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Update user profile fields and permission set."""
    before = fetch_user_by_id(db_path, user_id)
    if not before:
        raise RuntimeError("User not found.")

    effective_company = company if company is not None else before.get("company")
    if permissions is not None:
        permissions_json = _validate_permissions_update(
            db_path,
            user_id,
            permissions,
            effective_company,
            actor,
        )
        template = detect_template(normalize_permission_selection(permissions))
        update_user(db_path, user_id, permissions=permissions_json)
        if template:
            update_user(db_path, user_id, role=template)

    if username is not None:
        update_user(db_path, user_id, username=username.strip())
    if full_name is not None:
        update_user(db_path, user_id, full_name=full_name.strip())
    if email is not None:
        update_user(db_path, user_id, email=email)
    if company is not None:
        current = fetch_user_by_id(db_path, user_id)
        needs_company = permissions_require_company(
            stored_permissions_list(current or before),
        )
        if needs_company:
            previous_company = (current or before).get("company")
            company_value = assert_company_assignable(
                db_path,
                company,
                previous_code=previous_company,
            )
            update_user(db_path, user_id, company=company_value)
        else:
            update_user(
                db_path,
                user_id,
                company=(company or "").strip() or None,
            )
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
