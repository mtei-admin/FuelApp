export type SettlementType = "vendor_invoice" | "credit_card";

export function formatSettlementLabel(value?: string | null): string {
  if (value === "credit_card") {
    return "Credit card";
  }
  return "Vendor account";
}

export function isCreditCardSettlement(value?: string | null): boolean {
  return (value || "").toLowerCase() === "credit_card";
}
