import { apiFetch } from "./client";

export interface BillingItem {
  id: number;
  serial_number?: string;
  plate_number?: string;
  vendor_name?: string;
  quantity: number;
  unit: string;
  total_price?: number;
  po_reference?: string;
  actual_quantity?: number | null;
}

export interface BilledSummary {
  invoice_number: string;
  billing_date: string;
  items: BillingItem[];
}

export async function listReceived(): Promise<BillingItem[]> {
  return apiFetch<BillingItem[]>("/api/billing/received");
}

export async function updateActualQuantity(
  id: number,
  actualQuantity: number,
): Promise<void> {
  await apiFetch<{ message: string }>(`/api/billing/${id}/actual-quantity`, {
    method: "PATCH",
    body: JSON.stringify({ actual_quantity: actualQuantity }),
  });
}

export async function markBilled(
  requisitionIds: number[],
  invoiceNumber: string,
): Promise<BilledSummary> {
  return apiFetch<BilledSummary>("/api/billing/mark-billed", {
    method: "POST",
    body: JSON.stringify({
      requisition_ids: requisitionIds,
      invoice_number: invoiceNumber,
    }),
  });
}
