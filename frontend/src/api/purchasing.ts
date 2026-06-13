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
  vendor_name?: string;
  quantity: number;
  unit: string;
  fuel_type?: string;
  requester_name?: string;
  unit_price?: number;
  total_price?: number;
  po_reference?: string;
  default_unit_price?: number | null;
  actual_quantity?: number | null;
}

export async function listFuelPrices(): Promise<FuelPriceRow[]> {
  return apiFetch<FuelPriceRow[]>("/api/purchasing/fuel-prices");
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

export async function generatePo(
  id: number,
  unitPrice: number,
  poReference: string,
): Promise<void> {
  await apiFetch<{ message: string }>(`/api/purchasing/${id}/generate-po`, {
    method: "POST",
    body: JSON.stringify({ unit_price: unitPrice, po_reference: poReference }),
  });
}

export async function markReceived(id: number): Promise<void> {
  await apiFetch<{ message: string }>(`/api/purchasing/${id}/received`, {
    method: "POST",
  });
}
