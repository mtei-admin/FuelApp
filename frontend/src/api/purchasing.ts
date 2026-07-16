import { apiFetch } from "./client";

export interface FuelPriceRow {
  vendor_id: number;
  vendor_name: string;
  diesel_price?: number | null;
  unleaded_price?: number | null;
  premium_price?: number | null;
  updated_at?: string | null;
}

export interface PurchasingRequisition {
  id: number;
  serial_number?: string;
  plate_number?: string;
  model?: string;
  vehicle_id?: number;
  vendor_id?: number;
  vendor_name?: string;
  quantity: number;
  unit: string;
  fuel_type?: string;
  requester_name?: string;
  requestor_name?: string | null;
  unit_price?: number;
  total_price?: number;
  po_reference?: string;
  notes?: string | null;
  default_unit_price?: number | null;
  actual_quantity?: number | null;
  actual_unit_price?: number | null;
  receipt_number?: string | null;
  received_date?: string | null;
  released_date?: string | null;
  released_by?: string | null;
  release_remarks?: string | null;
  receiving_remarks?: string | null;
  created_at?: string | null;
  status?: string;
  settlement_type?: string;
  approved_by?: string | null;
  po_signatory?: string | null;
  cc_card_reference?: string | null;
  cc_statement_reference?: string | null;
  cc_reconciled_at?: string | null;
  cc_reconciled_by?: string | null;
  invoice_number?: string | null;
  prepared_by?: string | null;
  cancel_reason?: string | null;
  cancelled_by?: string | null;
}

export interface ReleasePayload {
  released_date: string;
  remarks?: string;
}

export interface ReceivePayload {
  received_date: string;
  actual_unit_price: number;
  actual_quantity: number;
  receipt_number: string;
  remarks?: string;
}

export interface CcFillPayload {
  fill_date: string;
  actual_unit_price: number;
  actual_quantity: number;
  receipt_number: string;
  cc_card_reference?: string;
  settlement_type?: "vendor_invoice" | "credit_card";
}

export async function listCcFills(): Promise<PurchasingRequisition[]> {
  return apiFetch<PurchasingRequisition[]>("/api/purchasing/cc-fills");
}

export async function listFuelPrices(): Promise<FuelPriceRow[]> {
  return apiFetch<FuelPriceRow[]>("/api/purchasing/fuel-prices");
}

export interface PurchasingQueueCounts {
  approved: number;
  cc_fills: number;
  po_generated: number;
  released: number;
  received: number;
}

export async function getQueueCounts(): Promise<PurchasingQueueCounts> {
  return apiFetch<PurchasingQueueCounts>("/api/purchasing/counts");
}

export async function updateFuelPrices(
  vendorId: number,
  prices: {
    diesel_price?: number;
    unleaded_price?: number;
    premium_price?: number;
  },
): Promise<void> {
  await apiFetch<{ message: string }>(`/api/purchasing/fuel-prices/${vendorId}`, {
    method: "PUT",
    body: JSON.stringify(prices),
  });
}

export async function listApproved(): Promise<PurchasingRequisition[]> {
  return apiFetch<PurchasingRequisition[]>("/api/purchasing/approved");
}

export async function listPoGenerated(): Promise<PurchasingRequisition[]> {
  return apiFetch<PurchasingRequisition[]>("/api/purchasing/po-generated");
}

export async function listReleased(): Promise<PurchasingRequisition[]> {
  return apiFetch<PurchasingRequisition[]>("/api/purchasing/released");
}

export async function listReceivedPurchasing(): Promise<PurchasingRequisition[]> {
  return apiFetch<PurchasingRequisition[]>("/api/purchasing/received");
}

export interface PoSignatory {
  id: number;
  full_name: string;
  username?: string | null;
  role?: string | null;
}

export async function listSignatories(): Promise<PoSignatory[]> {
  return apiFetch<PoSignatory[]>("/api/purchasing/signatories");
}

export async function generatePo(
  id: number,
  unitPrice: number,
  poReference: string,
  signatoryUserId: number,
): Promise<void> {
  await apiFetch<{ message: string }>(`/api/purchasing/${id}/generate-po`, {
    method: "POST",
    body: JSON.stringify({
      unit_price: unitPrice,
      po_reference: poReference,
      signatory_user_id: signatoryUserId,
    }),
  });
}

export async function releasePo(id: number, payload: ReleasePayload): Promise<void> {
  await apiFetch<{ message: string }>(`/api/purchasing/${id}/release`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function undoRelease(id: number): Promise<void> {
  await apiFetch<{ message: string }>(`/api/purchasing/${id}/undo-release`, {
    method: "POST",
  });
}

export async function markReceived(id: number, payload: ReceivePayload): Promise<void> {
  await apiFetch<{ message: string }>(`/api/purchasing/${id}/received`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateReceiving(id: number, payload: ReceivePayload): Promise<void> {
  await apiFetch<{ message: string }>(`/api/purchasing/${id}/receiving`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export interface AdminEditPayload {
  status?: string;
  vehicle_id?: number;
  vendor_id?: number;
  quantity?: number;
  unit?: string;
  fuel_type?: string;
  unit_price?: number;
  po_reference?: string;
  notes?: string;
  requestor_name?: string;
  actual_unit_price?: number;
  actual_quantity?: number;
  receipt_number?: string;
  received_date?: string;
  released_date?: string;
  released_by?: string;
  release_remarks?: string;
  invoice_number?: string;
  approved_by?: string;
  prepared_by?: string;
  po_signatory?: string;
  settlement_type?: string;
  cc_card_reference?: string;
  cc_statement_reference?: string;
  cc_reconciled_at?: string;
  cc_reconciled_by?: string;
  cancel_reason?: string;
  cancelled_by?: string;
}

export async function adminEdit(id: number, payload: AdminEditPayload): Promise<void> {
  await apiFetch<{ message: string }>(`/api/purchasing/${id}/admin-edit`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function updateSettlementType(
  id: number,
  settlementType: "vendor_invoice" | "credit_card",
): Promise<void> {
  await apiFetch<{ message: string }>(`/api/purchasing/${id}/settlement-type`, {
    method: "PATCH",
    body: JSON.stringify({ settlement_type: settlementType }),
  });
}

export async function recordCcFill(id: number, payload: CcFillPayload): Promise<void> {
  await apiFetch<{ message: string }>(`/api/purchasing/${id}/record-cc-fill`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
