"""Tests for user permission catalog and helpers."""
from src.permissions import (
    ADMIN_MANAGE_USERS,
    FLEET_INSURANCE,
    PURCHASING_SIGN_PO,
    build_public_user,
    effective_permissions,
    normalize_permission_selection,
    permissions_for_backfill,
    permissions_for_role,
    user_has_permission,
)


def test_encoder_template_permissions() -> None:
    """Encoder role template grants fuel request and encode permissions."""
    codes = set(permissions_for_role("encoder"))
    assert "fuel.requests.create" in codes
    assert "fuel.encode.receipt" in codes
    assert FLEET_INSURANCE not in codes


def test_joseph_backfill_includes_insurance() -> None:
    """Joseph migration keeps encoder access and adds Insurance."""
    payload = permissions_for_backfill("encoder", "joseph")
    assert FLEET_INSURANCE in payload
    assert "fuel.requests.create" in payload


def test_approvals_act_implies_view() -> None:
    """Granting approve permission auto-expands to view approvals."""
    explicit = normalize_permission_selection(["approvals.act"])
    assert "approvals.act" in explicit
    user = {"role": "encoder", "permissions": '["approvals.act"]'}
    effective = effective_permissions(user)
    assert "approvals.view" in effective
    assert "approvals.act" in effective


def test_baseline_always_present() -> None:
    """Every user receives baseline portal permissions at runtime."""
    user = {"role": "encoder", "permissions": "[]"}
    effective = effective_permissions(user)
    assert "fuel.prices.view" in effective
    assert "fleet.registrations.update" in effective


def test_build_public_user_includes_effective_permissions() -> None:
    """Public user payload exposes effective permission list for the SPA."""
    user = {
        "id": 1,
        "username": "joseph",
        "role": "encoder",
        "permissions": permissions_for_backfill("encoder", "joseph"),
        "is_active": 1,
    }
    public = build_public_user(user)
    assert public["permissions"]
    assert user_has_permission(public, FLEET_INSURANCE)


def test_approver_template_includes_sign_po() -> None:
    """Approver role template grants PO signatory eligibility (legacy behavior)."""
    codes = set(permissions_for_role("approver"))
    assert PURCHASING_SIGN_PO in codes


def test_purchaser_template_excludes_sign_po() -> None:
    """Purchasers generate POs but do not appear as signatories themselves."""
    codes = set(permissions_for_role("purchaser"))
    assert PURCHASING_SIGN_PO not in codes


def test_purchaser_template_includes_create_requests() -> None:
    """Purchaser role template grants fuel request submission."""
    codes = set(permissions_for_role("purchaser"))
    assert "fuel.requests.create" in codes
    assert "fuel.requests.edit_own" in codes
    assert "purchasing.admin_edit" in codes


def test_superuser_manage_users() -> None:
    """Superuser template includes manage users permission."""
    codes = set(permissions_for_role("superuser"))
    assert ADMIN_MANAGE_USERS in codes
