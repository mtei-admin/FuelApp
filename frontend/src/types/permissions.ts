/** Permission codes — keep in sync with src/permissions.py */

export const BASELINE_PERMISSIONS = [
  "fuel.prices.view",
  "fleet.registrations.view",
  "fleet.registrations.update",
] as const;

export type PermissionCode = string;

export interface PermissionDefinition {
  code: PermissionCode;
  label: string;
  baseline?: boolean;
}

export interface PermissionGroup {
  id: string;
  label: string;
  permissions: PermissionDefinition[];
}

export const PERMISSION_GROUPS: PermissionGroup[] = [
  {
    id: "fleet",
    label: "Fleet portal",
    permissions: [
      { code: "fleet.registrations.view", label: "Registrations — view", baseline: true },
      { code: "fleet.registrations.update", label: "Registrations — update", baseline: true },
      { code: "fleet.insurance", label: "Insurance" },
      { code: "fleet.pms", label: "PMS" },
      { code: "fleet.repairs", label: "Repairs (future)" },
      {
        code: "fleet.master_data",
        label: "Admin / Master Data (vendors, companies, service centers, vehicles)",
      },
    ],
  },
  {
    id: "fuel",
    label: "Fuel requests",
    permissions: [
      { code: "fuel.requests.create", label: "Create requests" },
      { code: "fuel.requests.edit_own", label: "Edit own pending requests" },
      { code: "fuel.requests.edit_any", label: "Edit any request (override)" },
      { code: "fuel.encode.receipt", label: "Encode — record PO receipt" },
      { code: "fuel.encode.cc_fill", label: "Encode — record CC fill" },
      { code: "fuel.prices.view", label: "View fuel prices", baseline: true },
      { code: "fuel.prices.edit", label: "Edit fuel prices" },
    ],
  },
  {
    id: "workflow",
    label: "Workflow",
    permissions: [
      { code: "approvals.view", label: "View approvals" },
      { code: "approvals.act", label: "Approve / reject / cancel" },
      { code: "purchasing.access", label: "Purchasing" },
      { code: "purchasing.sign_po", label: "Sign PO (signatory list)" },
      { code: "purchasing.undo_release", label: "Undo PO release" },
      { code: "purchasing.admin_edit", label: "Purchasing admin full edit" },
      { code: "billing.access", label: "Billing" },
      { code: "billing.correct", label: "Billing corrections / unbill" },
      { code: "reports.view", label: "Reports" },
      { code: "dashboard.view", label: "Dashboard" },
    ],
  },
  {
    id: "audit",
    label: "Audit & admin",
    permissions: [
      { code: "audit.view", label: "Transaction logs" },
      { code: "audit.active_users", label: "Active users" },
      { code: "admin.manage_users", label: "Manage users (enrollment)" },
    ],
  },
];

export const ROLE_TEMPLATE_OPTIONS = [
  { id: "encoder", label: "Encoder" },
  { id: "approver", label: "Approver" },
  { id: "purchaser", label: "Purchaser" },
  { id: "accounting", label: "Accounting" },
  { id: "superuser", label: "Superuser (all permissions)" },
] as const;

/** Explicit permissions per legacy role template (excludes baseline). */
export const ROLE_TEMPLATE_PERMISSIONS: Record<string, string[]> = {
  encoder: [
    "fuel.requests.create",
    "fuel.requests.edit_own",
    "fuel.encode.receipt",
    "fuel.encode.cc_fill",
  ],
  approver: ["approvals.view", "approvals.act", "purchasing.sign_po", "fleet.master_data", "fleet.insurance"],
  purchaser: [
    "fuel.requests.create",
    "fuel.requests.edit_own",
    "approvals.view",
    "purchasing.access",
    "purchasing.admin_edit",
    "fuel.prices.edit",
    "billing.access",
    "reports.view",
    "fleet.master_data",
    "fleet.insurance",
  ],
  accounting: [
    "approvals.view",
    "approvals.act",
    "purchasing.access",
    "purchasing.sign_po",
    "fuel.prices.edit",
    "billing.access",
    "billing.correct",
    "reports.view",
    "dashboard.view",
    "audit.view",
    "fleet.master_data",
    "fleet.insurance",
  ],
  superuser: PERMISSION_GROUPS.flatMap((group) =>
    group.permissions.filter((perm) => !perm.baseline).map((perm) => perm.code),
  ),
};

export const COMPANY_SCOPED_PERMISSIONS = new Set([
  "fuel.encode.receipt",
  "fuel.encode.cc_fill",
]);
