/** Role helpers mirroring Streamlit sidebar access rules. */

const MASTER_DATA_ROLES = new Set(["approver", "accounting", "superuser"]);
const APPROVALS_VIEW_ROLES = new Set([
  "approver",
  "purchaser",
  "accounting",
  "superuser",
]);
const APPROVALS_ACTION_ROLES = new Set(["approver", "accounting", "superuser"]);
const PURCHASING_ROLES = new Set(["purchaser", "accounting", "superuser"]);
const BILLING_ROLES = new Set(["purchaser", "accounting", "superuser"]);
const REPORTS_ROLES = new Set(["accounting", "superuser"]);
const DASHBOARD_ROLES = new Set(["accounting", "superuser"]);

export function canAccessMasterData(role: string | undefined): boolean {
  return MASTER_DATA_ROLES.has((role ?? "").toLowerCase());
}

export function canAccessApprovals(role: string | undefined): boolean {
  return APPROVALS_VIEW_ROLES.has((role ?? "").toLowerCase());
}

export function canApproveRequests(role: string | undefined): boolean {
  return APPROVALS_ACTION_ROLES.has((role ?? "").toLowerCase());
}

export function canAccessPurchasing(role: string | undefined): boolean {
  return PURCHASING_ROLES.has((role ?? "").toLowerCase());
}

export function canAccessBilling(role: string | undefined): boolean {
  return BILLING_ROLES.has((role ?? "").toLowerCase());
}

export function canAccessReports(role: string | undefined): boolean {
  return REPORTS_ROLES.has((role ?? "").toLowerCase());
}

export function canAccessDashboard(role: string | undefined): boolean {
  return DASHBOARD_ROLES.has((role ?? "").toLowerCase());
}

export function normalizeRole(role: string | undefined): string {
  return (role ?? "").toLowerCase();
}
