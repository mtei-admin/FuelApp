/** Role helpers mirroring Streamlit sidebar access rules. */

const MASTER_DATA_ROLES = new Set(["approver", "purchaser", "accounting", "superuser"]);
const ENCODE_ROLES = new Set(["encoder"]);
const APPROVALS_VIEW_ROLES = new Set([
  "approver",
  "purchaser",
  "accounting",
  "superuser",
]);
const APPROVALS_ACTION_ROLES = new Set(["approver", "accounting", "superuser"]);
const PURCHASING_ROLES = new Set(["purchaser", "accounting", "superuser"]);
const BILLING_ROLES = new Set(["purchaser", "accounting", "superuser"]);
const REPORTS_ROLES = new Set(["purchaser", "accounting", "superuser"]);
const AUDIT_ROLES = new Set(["accounting", "superuser"]);
const DASHBOARD_ROLES = new Set(["accounting", "superuser"]);
/** Vehicles module + coming-soon fleet cards (ops / admin roles). */
const FLEET_CORE_ROLES = new Set([
  "approver",
  "purchaser",
  "accounting",
  "superuser",
]);

export function canAccessEncode(role: string | undefined): boolean {
  const normalized = (role ?? "").toLowerCase();
  return ENCODE_ROLES.has(normalized) || normalized === "user";
}

export function canAccessMasterData(role: string | undefined): boolean {
  return MASTER_DATA_ROLES.has((role ?? "").toLowerCase());
}

/** Fleet Vehicles module (same roles as Master Data vehicles API). */
export function canAccessFleetVehicles(role: string | undefined): boolean {
  return FLEET_CORE_ROLES.has((role ?? "").toLowerCase());
}

/** Show Registrations / PMS / Repairs / Insurance portal cards. */
export function canSeeComingSoonFleetModules(role: string | undefined): boolean {
  return canAccessFleetVehicles(role);
}

/** Superuser (admin) — user enrollment on Master Data > Users tab. */
export function canManageUsers(role: string | undefined): boolean {
  return (role ?? "").toLowerCase() === "superuser";
}

/** Superuser — active session list (sidebar Active Users page). */
export function canViewActiveUsers(role: string | undefined): boolean {
  return (role ?? "").toLowerCase() === "superuser";
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

/** Purchaser/accounting/superuser — edit billing ref or unbill mistaken items. */
export function canCorrectBilling(role: string | undefined): boolean {
  return BILLING_ROLES.has((role ?? "").toLowerCase());
}

/** Accounting/superuser — transaction logs under Audit menu. */
export function canViewAuditTrail(role: string | undefined): boolean {
  return AUDIT_ROLES.has((role ?? "").toLowerCase());
}

export function canAccessAudit(role: string | undefined): boolean {
  return canViewAuditTrail(role) || canViewActiveUsers(role);
}

export function normalizeRole(role: string | undefined): string {
  return (role ?? "").toLowerCase();
}
