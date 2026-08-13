import { apiFetch } from "./client";

export interface BillingItem {
  id: number;
  serial_number?: string;
  status?: string;
  fuel_type?: string;
  plate_number?: string;
  vendor_name?: string;
  vehicle_id?: number;
  vendor_id?: number;
  quantity: number;
  unit: string;
  unit_price?: number;
  total_price?: number;
  po_reference?: string;
  actual_quantity?: number | null;
  actual_unit_price?: number | null;
  receipt_number?: string | null;
  received_date?: string | null;
  requestor_name?: string | null;
  cc_card_reference?: string | null;
  cc_statement_reference?: string | null;
  cc_reconcile_report_no?: string | null;
  cc_reconciled_at?: string | null;
  cc_reconciled_by?: string | null;
  invoice_number?: string | null;
  settlement_type?: string;
}

export interface BilledSummary {
  invoice_number: string;
  billing_date: string;
  items: BillingItem[];
}

export interface BillingQueueCounts {
  received: number;
  cc_unreconciled: number;
}

export interface CcReconcileSummary {
  report_number: string;
  statement_reference: string;
  reconciled_date: string;
  items: BillingItem[];
}

export async function getBillingCounts(): Promise<BillingQueueCounts> {
  return apiFetch<BillingQueueCounts>("/api/billing/counts");
}

export async function listReceived(): Promise<BillingItem[]> {
  return apiFetch<BillingItem[]>("/api/billing/received");
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

export async function listBilled(): Promise<BillingItem[]> {
  return apiFetch<BillingItem[]>("/api/billing/billed");
}

export async function updateBillingReference(
  requisitionIds: number[],
  invoiceNumber: string,
): Promise<void> {
  await apiFetch("/api/billing/update-billing-reference", {
    method: "POST",
    body: JSON.stringify({
      requisition_ids: requisitionIds,
      invoice_number: invoiceNumber,
    }),
  });
}

export async function unbillItems(requisitionIds: number[]): Promise<void> {
  await apiFetch("/api/billing/unbill", {
    method: "POST",
    body: JSON.stringify({ requisition_ids: requisitionIds }),
  });
}

export async function listCcUnreconciled(): Promise<BillingItem[]> {
  return apiFetch<BillingItem[]>("/api/billing/cc-unreconciled");
}

export async function reconcileCc(
  requisitionIds: number[],
  statementReference: string,
): Promise<CcReconcileSummary> {
  return apiFetch<CcReconcileSummary>("/api/billing/reconcile-cc", {
    method: "POST",
    body: JSON.stringify({
      requisition_ids: requisitionIds,
      statement_reference: statementReference,
    }),
  });
}
