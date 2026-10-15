"""User permission codes, role templates, and access helpers."""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Set

# ---------------------------------------------------------------------------
# Permission codes (stable identifiers — do not rename without a migration)
# ---------------------------------------------------------------------------

# Fleet portal modules
FLEET_REGISTRATIONS_VIEW = "fleet.registrations.view"
FLEET_REGISTRATIONS_UPDATE = "fleet.registrations.update"
FLEET_INSURANCE = "fleet.insurance"
FLEET_PMS = "fleet.pms"
FLEET_REPAIRS = "fleet.repairs"
FLEET_MASTER_DATA = "fleet.master_data"

# Baseline: granted to every active authenticated user (not stored per user).
BASELINE_PERMISSIONS: frozenset[str] = frozenset(
    {
        "fuel.prices.view",
        FLEET_REGISTRATIONS_VIEW,
        FLEET_REGISTRATIONS_UPDATE,
    }
)

# Fuel workflow
FUEL_REQUESTS_CREATE = "fuel.requests.create"
FUEL_REQUESTS_EDIT_OWN = "fuel.requests.edit_own"
FUEL_REQUESTS_EDIT_ANY = "fuel.requests.edit_any"
FUEL_ENCODE_RECEIPT = "fuel.encode.receipt"
FUEL_ENCODE_CC_FILL = "fuel.encode.cc_fill"
FUEL_PRICES_EDIT = "fuel.prices.edit"

# Approvals
APPROVALS_VIEW = "approvals.view"
APPROVALS_ACT = "approvals.act"

# Purchasing
PURCHASING_ACCESS = "purchasing.access"
PURCHASING_SIGN_PO = "purchasing.sign_po"
PURCHASING_UNDO_RELEASE = "purchasing.undo_release"
PURCHASING_ADMIN_EDIT = "purchasing.admin_edit"

# Billing & reporting
BILLING_ACCESS = "billing.access"
BILLING_CORRECT = "billing.correct"
REPORTS_VIEW = "reports.view"
DASHBOARD_VIEW = "dashboard.view"

# Audit & admin
AUDIT_VIEW = "audit.view"
AUDIT_ACTIVE_USERS = "audit.active_users"
ADMIN_MANAGE_USERS = "admin.manage_users"

ALL_PERMISSION_CODES: frozenset[str] = BASELINE_PERMISSIONS | frozenset(
    {
        FLEET_INSURANCE,
        FLEET_PMS,
        FLEET_REPAIRS,
        FLEET_MASTER_DATA,
        FUEL_REQUESTS_CREATE,
        FUEL_REQUESTS_EDIT_OWN,
        FUEL_REQUESTS_EDIT_ANY,
        FUEL_ENCODE_RECEIPT,
        FUEL_ENCODE_CC_FILL,
        FUEL_PRICES_EDIT,
        APPROVALS_VIEW,
        APPROVALS_ACT,
        PURCHASING_ACCESS,
        PURCHASING_SIGN_PO,
        PURCHASING_UNDO_RELEASE,
        PURCHASING_ADMIN_EDIT,
        BILLING_ACCESS,
        BILLING_CORRECT,
        REPORTS_VIEW,
        DASHBOARD_VIEW,
        AUDIT_VIEW,
        AUDIT_ACTIVE_USERS,
        ADMIN_MANAGE_USERS,
    }
)

# Permissions that require users.company (data scope for encode queues).
COMPANY_SCOPED_PERMISSIONS: frozenset[str] = frozenset(
    {
        FUEL_ENCODE_RECEIPT,
        FUEL_ENCODE_CC_FILL,
    }
)

# Auto-enable implied permissions when a parent is granted.
IMPLIED_PERMISSIONS: Dict[str, frozenset[str]] = {
    APPROVALS_ACT: frozenset({APPROVALS_VIEW}),
    PURCHASING_SIGN_PO: frozenset({APPROVALS_VIEW}),
    PURCHASING_UNDO_RELEASE: frozenset({PURCHASING_ACCESS}),
    PURCHASING_ADMIN_EDIT: frozenset({PURCHASING_ACCESS}),
    BILLING_CORRECT: frozenset({BILLING_ACCESS}),
    FUEL_PRICES_EDIT: frozenset({"fuel.prices.view"}),
    FUEL_REQUESTS_EDIT_ANY: frozenset({FUEL_REQUESTS_CREATE}),
    FUEL_REQUESTS_EDIT_OWN: frozenset({FUEL_REQUESTS_CREATE}),
    FUEL_ENCODE_CC_FILL: frozenset({FUEL_ENCODE_RECEIPT}),
    AUDIT_ACTIVE_USERS: frozenset({AUDIT_VIEW}),
    ADMIN_MANAGE_USERS: frozenset({FLEET_MASTER_DATA}),
}

ROLE_TEMPLATES: Dict[str, frozenset[str]] = {
    "encoder": frozenset(
        {
            FUEL_REQUESTS_CREATE,
            FUEL_REQUESTS_EDIT_OWN,
            FUEL_ENCODE_RECEIPT,
            FUEL_ENCODE_CC_FILL,
        }
    ),
    "approver": frozenset(
        {
            APPROVALS_VIEW,
            APPROVALS_ACT,
            PURCHASING_SIGN_PO,
            FLEET_MASTER_DATA,
            FLEET_INSURANCE,
        }
    ),
    "purchaser": frozenset(
        {
            FUEL_REQUESTS_CREATE,
            FUEL_REQUESTS_EDIT_OWN,
            APPROVALS_VIEW,
            PURCHASING_ACCESS,
            PURCHASING_ADMIN_EDIT,
            FUEL_PRICES_EDIT,
            BILLING_ACCESS,
            REPORTS_VIEW,
            FLEET_MASTER_DATA,
            FLEET_INSURANCE,
        }
    ),
    "accounting": frozenset(
        {
            APPROVALS_VIEW,
            APPROVALS_ACT,
            PURCHASING_ACCESS,
            PURCHASING_SIGN_PO,
            FUEL_PRICES_EDIT,
            BILLING_ACCESS,
            BILLING_CORRECT,
            REPORTS_VIEW,
            DASHBOARD_VIEW,
            AUDIT_VIEW,
            FLEET_MASTER_DATA,
            FLEET_INSURANCE,
        }
    ),
    "superuser": ALL_PERMISSION_CODES - BASELINE_PERMISSIONS,
}

# UI grouping metadata (mirrored in frontend/src/types/permissions.ts).
PERMISSION_GROUPS: List[Dict[str, Any]] = [
    {
        "id": "fleet",
        "label": "Fleet portal",
        "permissions": [
            {"code": "fleet.registrations.view", "label": "Registrations — view", "baseline": True},
            {"code": "fleet.registrations.update", "label": "Registrations — update", "baseline": True},
            {"code": FLEET_INSURANCE, "label": "Insurance"},
            {"code": FLEET_PMS, "label": "PMS"},
            {"code": FLEET_REPAIRS, "label": "Repairs (future)"},
            {"code": FLEET_MASTER_DATA, "label": "Admin / Master Data (vendors, companies, service centers, vehicles)"},
        ],
    },
    {
        "id": "fuel",
        "label": "Fuel requests",
        "permissions": [
            {"code": FUEL_REQUESTS_CREATE, "label": "Create requests"},
            {"code": FUEL_REQUESTS_EDIT_OWN, "label": "Edit own pending requests"},
            {"code": FUEL_REQUESTS_EDIT_ANY, "label": "Edit any request (override)"},
            {"code": FUEL_ENCODE_RECEIPT, "label": "Encode — record PO receipt"},
            {"code": FUEL_ENCODE_CC_FILL, "label": "Encode — record CC fill"},
            {"code": "fuel.prices.view", "label": "View fuel prices", "baseline": True},
            {"code": FUEL_PRICES_EDIT, "label": "Edit fuel prices"},
        ],
    },
    {
        "id": "workflow",
        "label": "Workflow",
        "permissions": [
            {"code": APPROVALS_VIEW, "label": "View approvals"},
            {"code": APPROVALS_ACT, "label": "Approve / reject / cancel"},
            {"code": PURCHASING_ACCESS, "label": "Purchasing"},
            {"code": PURCHASING_SIGN_PO, "label": "Sign PO (appears in signatory list)"},
            {"code": PURCHASING_UNDO_RELEASE, "label": "Undo PO release"},
            {"code": PURCHASING_ADMIN_EDIT, "label": "Purchasing admin full edit"},
            {"code": BILLING_ACCESS, "label": "Billing"},
            {"code": BILLING_CORRECT, "label": "Billing corrections / unbill"},
            {"code": REPORTS_VIEW, "label": "Reports"},
            {"code": DASHBOARD_VIEW, "label": "Dashboard"},
        ],
    },
    {
        "id": "audit",
        "label": "Audit & admin",
        "permissions": [
            {"code": AUDIT_VIEW, "label": "Transaction logs"},
            {"code": AUDIT_ACTIVE_USERS, "label": "Active users"},
            {"code": ADMIN_MANAGE_USERS, "label": "Manage users (enrollment)"},
        ],
    },
]

TEMPLATE_LABELS: Dict[str, str] = {
    "encoder": "Encoder",
    "approver": "Approver",
    "purchaser": "Purchaser",
    "accounting": "Accounting",
    "superuser": "Superuser (all permissions)",
}


def permissions_for_role(role: str) -> List[str]:
    """
    Return the explicit permission codes for a legacy role template.

    Args:
        role: Legacy role name (encoder, approver, etc.).

    Returns:
        Sorted list of permission codes excluding baseline entries.
    """
    role_lower = (role or "encoder").lower()
    if role_lower == "user":
        role_lower = "encoder"
    template = ROLE_TEMPLATES.get(role_lower, ROLE_TEMPLATES["encoder"])
    return sorted(template)


def parse_stored_permissions(raw: Optional[str]) -> Optional[List[str]]:
    """
    Parse permissions JSON from the database.

    Args:
        raw: JSON array string or None/empty.

    Returns:
        List of permission codes, or None when unset (use role fallback).
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    return [str(item).strip() for item in parsed if str(item).strip()]


def expand_implied_permissions(codes: Iterable[str]) -> Set[str]:
    """
    Add implied parent permissions for the given explicit codes.

    Args:
        codes: Explicit permission codes.

    Returns:
        Expanded set including implied codes.
    """
    expanded: Set[str] = set()
    for code in codes:
        normalized = code.strip()
        if normalized in ALL_PERMISSION_CODES:
            expanded.add(normalized)
        queue = [normalized]
        while queue:
            current = queue.pop()
            for implied in IMPLIED_PERMISSIONS.get(current, frozenset()):
                if implied not in expanded:
                    expanded.add(implied)
                    queue.append(implied)
    return expanded


def normalize_permission_selection(codes: Iterable[str]) -> List[str]:
    """
    Validate, expand implied permissions, and return sorted explicit storage list.

    Baseline permissions are not stored (always applied at runtime).

    Args:
        codes: Raw permission codes from admin UI/API.

    Returns:
        Sorted unique explicit permission codes safe to persist.

    Raises:
        ValueError: If an unknown permission code is present.
    """
    explicit = expand_implied_permissions(codes) - BASELINE_PERMISSIONS
    unknown = explicit - ALL_PERMISSION_CODES
    if unknown:
        unknown_list = ", ".join(sorted(unknown))
        raise ValueError(f"Unknown permission(s): {unknown_list}")
    return sorted(explicit)


def effective_permissions(user: Dict[str, Any]) -> Set[str]:
    """
    Resolve the full permission set for a user (baseline + stored or role template).

    Args:
        user: User dict with optional permissions JSON and role.

    Returns:
        Set of all active permission codes for access checks.
    """
    stored = parse_stored_permissions(user.get("permissions"))
    if stored is not None:
        explicit = expand_implied_permissions(stored)
    else:
        explicit = expand_implied_permissions(permissions_for_role(user.get("role", "encoder")))
    return BASELINE_PERMISSIONS | explicit


def user_has_permission(user: Dict[str, Any], code: str) -> bool:
    """
    Return True when the user holds a permission code.

    Args:
        user: User dict from session/database.
        code: Permission code to check.

    Returns:
        True if allowed.
    """
    perms = user.get("permissions")
    if isinstance(perms, list):
        return code in perms
    return code in effective_permissions(user)


def user_has_any_permission(user: Dict[str, Any], *codes: str) -> bool:
    """Return True when the user holds any of the given permission codes."""
    return any(user_has_permission(user, code) for code in codes)


def user_can_edit_any_requisition(user: Dict[str, Any]) -> bool:
    """Return True when the user may override requisition edit rules."""
    return user_has_permission(user, FUEL_REQUESTS_EDIT_ANY)


def user_can_edit_own_requests(user: Dict[str, Any]) -> bool:
    """Return True when the user may edit their own pending requests."""
    return user_has_permission(user, FUEL_REQUESTS_EDIT_OWN)


def user_is_purchasing_admin(user: Dict[str, Any]) -> bool:
    """Return True for purchasing admin override actions (full edit, skip release)."""
    return user_has_permission(user, PURCHASING_ADMIN_EDIT)


def user_is_encode_receipt_only(user: Dict[str, Any]) -> bool:
    """Return True for encode receipt users without purchasing access."""
    return user_has_permission(user, FUEL_ENCODE_RECEIPT) and not user_has_permission(
        user, PURCHASING_ACCESS
    )


def permissions_require_company(codes: Iterable[str]) -> bool:
    """Return True when any selected permission requires a company scope."""
    expanded = expand_implied_permissions(codes)
    return bool(expanded & COMPANY_SCOPED_PERMISSIONS)


def serialize_permissions(codes: Iterable[str]) -> str:
    """
    Serialize explicit permission codes for SQLite storage.

    Args:
        codes: Validated permission codes (baseline excluded).

    Returns:
        JSON array string.
    """
    normalized = normalize_permission_selection(codes)
    return json.dumps(normalized)


def permissions_for_backfill(role: str, username: str = "") -> str:
    """
    Build initial permissions JSON when migrating from legacy roles.

    Args:
        role: Current users.role value.
        username: Username for one-off grants (e.g. joseph + insurance).

    Returns:
        JSON string of explicit permissions.
    """
    codes = list(permissions_for_role(role))
    if (username or "").lower() == "joseph" and FLEET_INSURANCE not in codes:
        codes.append(FLEET_INSURANCE)
    return serialize_permissions(codes)


def permission_summary(codes: Iterable[str], max_items: int = 3) -> str:
    """
    Build a short human-readable summary for admin lists.

    Args:
        codes: Effective or explicit permission codes.
        max_items: Maximum labels before trailing ellipsis.

    Returns:
        Summary string such as "Fuel · Registrations · Insurance".
    """
    explicit = sorted(set(codes) - BASELINE_PERMISSIONS)
    if not explicit:
        return "Baseline only"
    labels: List[str] = []
    for group in PERMISSION_GROUPS:
        for perm in group["permissions"]:
            if perm["code"] in explicit:
                label = str(perm["label"]).split("—")[0].split("(")[0].strip()
                if label not in labels:
                    labels.append(label)
    if not labels:
        return "Custom"
    if len(labels) <= max_items:
        return " · ".join(labels)
    head = " · ".join(labels[:max_items])
    return f"{head} · +{len(labels) - max_items} more"


def detect_template(codes: Iterable[str]) -> Optional[str]:
    """
    Return a matching role template name when permissions exactly match a template.

    Args:
        codes: Explicit stored permission codes.

    Returns:
        Template key or None for custom mixes.
    """
    explicit = set(normalize_permission_selection(codes))
    for template_name, template_codes in ROLE_TEMPLATES.items():
        if explicit == set(template_codes):
            return template_name
    return None


def stored_permissions_list(user: Dict[str, Any]) -> List[str]:
    """
    Return explicit stored permissions for admin editing.

    Args:
        user: User row including permissions JSON column.

    Returns:
        Sorted explicit permission codes.
    """
    stored = parse_stored_permissions(user.get("permissions"))
    if stored is not None:
        return normalize_permission_selection(stored)
    return permissions_for_role(user.get("role", "encoder"))


def build_public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strip sensitive fields and attach effective permissions for API responses.

    Args:
        user: Raw user row from the database.

    Returns:
        Public user dict safe for session/API responses.
    """
    effective = sorted(effective_permissions(user))
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user.get("role") or "encoder",
        "full_name": user.get("full_name"),
        "email": user.get("email"),
        "company": user.get("company"),
        "is_active": bool(user.get("is_active")),
        "permissions": effective,
    }
