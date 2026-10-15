/** All requisition workflow statuses (superuser admin edit). */
export const REQUISITION_STATUSES = [
  "pending",
  "approved",
  "po_generated",
  "released",
  "received",
  "billed",
  "paid_cc",
  "cancelled",
  "rejected",
] as const;

export type RequisitionStatus = (typeof REQUISITION_STATUSES)[number];

/** Superuser admin-cancel is allowed from Request through PO Generated. */
export const ADMIN_CANCEL_STATUSES: readonly RequisitionStatus[] = [
  "pending",
  "approved",
  "po_generated",
  "released",
  "received",
];

export function canAdminCancelStatus(status: string | null | undefined): boolean {
  const normalized = (status || "").toLowerCase();
  return (ADMIN_CANCEL_STATUSES as readonly string[]).includes(normalized);
}

export function formatStatusLabel(status: string): string {
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
