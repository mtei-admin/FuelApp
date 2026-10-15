/** Parse digits-only input into a non-negative integer (liters). */
export function parsePositiveInteger(raw: string): number {
  const digits = raw.replace(/\D/g, "");
  if (!digits) {
    return 0;
  }
  return parseInt(digits, 10);
}

/** Format quantity for display. */
export function formatQuantity(quantity: number, unit: string): string {
  if (unit && unit.toUpperCase() === "FULLTANK") {
    return "Full Tank";
  }
  return `${quantity} liters`;
}

/** Format peso currency. */
export function formatPeso(amount: number | null | undefined): string {
  if (amount == null) {
    return "—";
  }
  return `₱${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** Format SQLite/API timestamps as a short local date for tables. */
export function formatAppDate(value?: string | null): string {
  if (!value) {
    return "—";
  }
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) {
    return value.slice(0, 10);
  }
  return parsed.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Derive fuel type dropdown options from vehicle fuel type (matches Streamlit logic). */
export function getFuelTypeOptions(
  vehicleFuelType: string | null | undefined,
): { options: string[]; disabled: boolean; defaultValue: string | null } {
  if (vehicleFuelType === "Diesel") {
    return { options: ["Diesel"], disabled: true, defaultValue: "Diesel" };
  }
  if (vehicleFuelType === "Unleaded Gasoline") {
    return {
      options: ["Unleaded Gasoline", "Premium Gasoline"],
      disabled: false,
      defaultValue: "Unleaded Gasoline",
    };
  }
  if (vehicleFuelType === "Premium Gasoline") {
    return {
      options: ["Premium Gasoline", "Unleaded Gasoline"],
      disabled: false,
      defaultValue: "Premium Gasoline",
    };
  }
  return {
    options: ["Diesel", "Unleaded Gasoline", "Premium Gasoline"],
    disabled: false,
    defaultValue: null,
  };
}

export function unitToQuantityMode(unit: string): "numeric" | "fulltank" {
  return unit && unit.toUpperCase() === "FULLTANK" ? "fulltank" : "numeric";
}

/** Avatar initials from full name or username. */
export function userInitials(
  fullName?: string | null,
  username?: string | null,
): string {
  const name = fullName?.trim();
  if (name) {
    const parts = name.split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
      return `${parts[0][0] ?? ""}${parts[parts.length - 1][0] ?? ""}`.toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }
  return (username ?? "?").slice(0, 2).toUpperCase();
}

/** Human-readable role label for UI. */
export function formatRoleLabel(role?: string | null): string {
  const value = (role ?? "").toLowerCase();
  if (!value) {
    return "Encoder";
  }
  if (value === "encoder" || value === "user") {
    return "Encoder";
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

/** Relative last-seen label for active users. */
export function formatLastSeen(timestamp?: string | null): string {
  if (!timestamp) {
    return "—";
  }
  const seen = new Date(timestamp.replace(" ", "T"));
  if (Number.isNaN(seen.getTime())) {
    return timestamp;
  }
  const diffMs = Date.now() - seen.getTime();
  const diffMin = Math.max(0, Math.floor(diffMs / 60000));
  if (diffMin < 1) {
    return "just now";
  }
  if (diffMin < 60) {
    return `${diffMin} min ago`;
  }
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) {
    return `${diffHours} hr ago`;
  }
  return seen.toLocaleString();
}
