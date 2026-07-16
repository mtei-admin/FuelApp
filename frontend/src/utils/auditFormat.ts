import type { AuditLogEntry } from "../api/audit";

const ENTITY_TYPE_LABELS: Record<string, string> = {
  requisition: "Request",
  vehicle: "Vehicle",
  vendor: "Vendor",
  user: "User",
  fuel_price: "Fuel price",
};

/** Human-readable entity cell for transaction logs. */
export function formatAuditEntity(entry: AuditLogEntry): string {
  const label = entry.entity_label?.trim();
  const type = entry.entity_type || "";

  if (!label) {
    const typeLabel = ENTITY_TYPE_LABELS[type] || type;
    return `${typeLabel} #${entry.entity_id}`;
  }

  switch (type) {
    case "user":
      return label;
    case "requisition":
      return `Req ${label}`;
    case "vehicle":
    case "vendor":
      return label;
    case "fuel_price":
      return `${label} (prices)`;
    default:
      return `${ENTITY_TYPE_LABELS[type] || type}: ${label}`;
  }
}
