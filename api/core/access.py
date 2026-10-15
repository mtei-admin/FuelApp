"""Shared FastAPI access dependencies (permission-based)."""
from typing import Annotated

from fastapi import Depends

from api.core.dependencies import get_current_user, require_permission
from src.permissions import (
    ADMIN_MANAGE_USERS,
    APPROVALS_ACT,
    APPROVALS_VIEW,
    AUDIT_ACTIVE_USERS,
    AUDIT_VIEW,
    BILLING_ACCESS,
    DASHBOARD_VIEW,
    FLEET_MASTER_DATA,
    FLEET_PMS,
    FLEET_REGISTRATIONS_UPDATE,
    FLEET_REGISTRATIONS_VIEW,
    FUEL_ENCODE_CC_FILL,
    FUEL_ENCODE_RECEIPT,
    FUEL_PRICES_EDIT,
    FUEL_REQUESTS_CREATE,
    PURCHASING_ACCESS,
    PURCHASING_ADMIN_EDIT,
    PURCHASING_UNDO_RELEASE,
    REPORTS_VIEW,
)

CurrentUser = Annotated[dict, Depends(get_current_user)]

ManageUsersUser = Annotated[dict, Depends(require_permission(ADMIN_MANAGE_USERS))]
MasterDataUser = Annotated[dict, Depends(require_permission(FLEET_MASTER_DATA))]
ViewApprovalsUser = Annotated[dict, Depends(require_permission(APPROVALS_VIEW))]
ApproveUser = Annotated[dict, Depends(require_permission(APPROVALS_ACT))]
PurchasingUser = Annotated[dict, Depends(require_permission(PURCHASING_ACCESS))]
PurchasingAdminUser = Annotated[dict, Depends(require_permission(PURCHASING_ADMIN_EDIT))]
UndoReleaseUser = Annotated[dict, Depends(require_permission(PURCHASING_UNDO_RELEASE))]
BillingUser = Annotated[dict, Depends(require_permission(BILLING_ACCESS))]
ReportsUser = Annotated[dict, Depends(require_permission(REPORTS_VIEW))]
DashboardUser = Annotated[dict, Depends(require_permission(DASHBOARD_VIEW))]
AuditUser = Annotated[dict, Depends(require_permission(AUDIT_VIEW))]
ActiveUsersUser = Annotated[dict, Depends(require_permission(AUDIT_ACTIVE_USERS))]
EncoderUser = Annotated[
    dict,
    Depends(require_permission(FUEL_ENCODE_RECEIPT, FUEL_ENCODE_CC_FILL)),
]
EncodeReceiptUser = Annotated[dict, Depends(require_permission(FUEL_ENCODE_RECEIPT))]
EncodeCcFillUser = Annotated[dict, Depends(require_permission(FUEL_ENCODE_CC_FILL))]
FuelRequestUser = Annotated[dict, Depends(require_permission(FUEL_REQUESTS_CREATE))]
FuelPriceEditUser = Annotated[dict, Depends(require_permission(FUEL_PRICES_EDIT))]
RegistrationsViewUser = Annotated[
    dict,
    Depends(require_permission(FLEET_REGISTRATIONS_VIEW)),
]
RegistrationsUpdateUser = Annotated[
    dict,
    Depends(require_permission(FLEET_REGISTRATIONS_UPDATE)),
]
PmsUser = Annotated[dict, Depends(require_permission(FLEET_PMS))]
