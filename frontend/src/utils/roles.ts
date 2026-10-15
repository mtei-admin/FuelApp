/** Access helpers — prefer user.permissions; fall back to legacy role bundles. */

import type { User } from "../types/auth";
import { hasAnyPermission, hasPermission } from "./permissions";

export type AccessSubject =
  | string
  | Pick<User, "role" | "username" | "permissions">
  | null
  | undefined;

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
const FLEET_CORE_ROLES = new Set([
  "approver",
  "purchaser",
  "accounting",
  "superuser",
]);

function roleOf(subject: AccessSubject): string {
  if (typeof subject === "string") {
    return subject.toLowerCase();
  }
  return (subject?.role ?? "").toLowerCase();
}

function usesPermissions(subject: AccessSubject): boolean {
  return Boolean(
    subject && typeof subject === "object" && subject.permissions && subject.permissions.length > 0,
  );
}

function check(
  subject: AccessSubject,
  code: string,
  roleFallback: boolean,
): boolean {
  if (usesPermissions(subject)) {
    return hasPermission(subject, code);
  }
  return roleFallback;
}

export function canAccessEncode(subject: AccessSubject): boolean {
  const role = roleOf(subject);
  return check(
    subject,
    "fuel.encode.receipt",
    ENCODE_ROLES.has(role) || role === "user",
  );
}

/** True when the Fuel Requests card should open /encode (encoder-only), not /fuel hub. */
export function prefersEncoderFuelPortal(subject: AccessSubject): boolean {
  if (!canAccessEncode(subject)) {
    return false;
  }
  // Users with workflow modules use the full fuel app at /fuel even if they also have encode perms.
  return (
    !canAccessApprovals(subject) &&
    !canAccessPurchasing(subject) &&
    !canAccessBilling(subject) &&
    !canAccessReports(subject) &&
    !canAccessDashboard(subject)
  );
}

export function canAccessMasterData(subject: AccessSubject): boolean {
  return check(subject, "fleet.master_data", MASTER_DATA_ROLES.has(roleOf(subject)));
}

export function canAccessFleetVehicles(subject: AccessSubject): boolean {
  return canAccessMasterData(subject);
}

export function canAccessRegistrations(subject: AccessSubject): boolean {
  if (usesPermissions(subject)) {
    return hasAnyPermission(
      subject,
      "fleet.registrations.view",
      "fleet.registrations.update",
    );
  }
  return true;
}

export function canSeeComingSoonFleetModules(subject: AccessSubject): boolean {
  return canAccessFleetVehicles(subject);
}

export function canAccessInsurancePortal(subject: AccessSubject): boolean {
  return check(subject, "fleet.insurance", FLEET_CORE_ROLES.has(roleOf(subject)));
}

export function canAccessPms(subject: AccessSubject): boolean {
  return check(subject, "fleet.pms", roleOf(subject) === "superuser");
}

export function canManageUsers(subject: AccessSubject): boolean {
  return check(subject, "admin.manage_users", roleOf(subject) === "superuser");
}

export function canViewActiveUsers(subject: AccessSubject): boolean {
  return check(subject, "audit.active_users", roleOf(subject) === "superuser");
}

export function canAccessApprovals(subject: AccessSubject): boolean {
  return check(subject, "approvals.view", APPROVALS_VIEW_ROLES.has(roleOf(subject)));
}

export function canApproveRequests(subject: AccessSubject): boolean {
  return check(subject, "approvals.act", APPROVALS_ACTION_ROLES.has(roleOf(subject)));
}

export function canAccessPurchasing(subject: AccessSubject): boolean {
  return check(subject, "purchasing.access", PURCHASING_ROLES.has(roleOf(subject)));
}

export function canPurchasingAdminEdit(subject: AccessSubject): boolean {
  return (
    check(subject, "purchasing.admin_edit", roleOf(subject) === "superuser") ||
    canManageUsers(subject)
  );
}

export function canAccessBilling(subject: AccessSubject): boolean {
  return check(subject, "billing.access", BILLING_ROLES.has(roleOf(subject)));
}

export function canAccessReports(subject: AccessSubject): boolean {
  return check(subject, "reports.view", REPORTS_ROLES.has(roleOf(subject)));
}

export function canAccessDashboard(subject: AccessSubject): boolean {
  return check(subject, "dashboard.view", DASHBOARD_ROLES.has(roleOf(subject)));
}

export function canCorrectBilling(subject: AccessSubject): boolean {
  return check(subject, "billing.correct", BILLING_ROLES.has(roleOf(subject)));
}

export function canViewAuditTrail(subject: AccessSubject): boolean {
  return check(subject, "audit.view", AUDIT_ROLES.has(roleOf(subject)));
}

export function canAccessAudit(subject: AccessSubject): boolean {
  return canViewAuditTrail(subject) || canViewActiveUsers(subject);
}

export function canCreateFuelRequests(subject: AccessSubject): boolean {
  return check(
    subject,
    "fuel.requests.create",
    ENCODE_ROLES.has(roleOf(subject)) || roleOf(subject) === "user",
  );
}

export function canEditAnyFuelRequest(subject: AccessSubject): boolean {
  return check(subject, "fuel.requests.edit_any", roleOf(subject) === "superuser");
}

export function normalizeRole(role: string | undefined): string {
  return (role ?? "").toLowerCase();
}
