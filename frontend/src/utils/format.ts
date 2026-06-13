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
