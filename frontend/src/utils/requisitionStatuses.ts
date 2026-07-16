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

export function formatStatusLabel(status: string): string {
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
