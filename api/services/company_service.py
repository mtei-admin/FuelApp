"""Company master data service."""
from typing import Any, Dict, List, Optional

from src.audit import COMPANY_AUDIT_FIELDS, log_audit, log_field_update, pick_fields
from src.database import (
    create_company,
    fetch_company_by_id,
    list_active_company_codes,
    list_companies,
    reactivate_company,
    soft_delete_company,
    update_company,
)


def get_all_companies(db_path: str) -> List[Dict[str, Any]]:
    """Return all companies (active and inactive) for master data admin."""
    return list_companies(db_path, active_only=False)


def get_active_company_codes(db_path: str) -> List[str]:
    """Return active company codes for vehicle/encoder dropdowns."""
    return list_active_company_codes(db_path)


def add_company(
    db_path: str,
    code: str,
    name: str,
    actor: Optional[Dict[str, Any]] = None,
) -> int:
    """Create a company master record."""
    company_id = create_company(db_path, code, name)
    created = fetch_company_by_id(db_path, company_id)
    log_audit(
        db_path,
        "company",
        company_id,
        "created",
        actor,
        new_values=pick_fields(created, COMPANY_AUDIT_FIELDS),
    )
    return company_id


def save_company(
    db_path: str,
    company_id: int,
    name: str,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Update company display name."""
    before = fetch_company_by_id(db_path, company_id)
    update_company(db_path, company_id, name)
    after = fetch_company_by_id(db_path, company_id)
    log_field_update(
        db_path,
        "company",
        company_id,
        "updated",
        actor,
        before,
        after,
        COMPANY_AUDIT_FIELDS,
    )


def deactivate_company(
    db_path: str,
    company_id: int,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Soft-delete a company."""
    before = fetch_company_by_id(db_path, company_id)
    soft_delete_company(db_path, company_id)
    after = fetch_company_by_id(db_path, company_id)
    log_field_update(
        db_path,
        "company",
        company_id,
        "deactivated",
        actor,
        before,
        after,
        ["is_active"],
    )


def restore_company(
    db_path: str,
    company_id: int,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Reactivate a company."""
    before = fetch_company_by_id(db_path, company_id)
    reactivate_company(db_path, company_id)
    after = fetch_company_by_id(db_path, company_id)
    log_field_update(
        db_path,
        "company",
        company_id,
        "reactivated",
        actor,
        before,
        after,
        ["is_active"],
    )
