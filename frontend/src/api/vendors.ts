import { apiFetch } from "./client";
import type {
  Vendor,
  VendorCreateRequest,
  VendorUpdateRequest,
} from "../types/vendor";

export async function listVendors(): Promise<Vendor[]> {
  return apiFetch<Vendor[]>("/api/vendors");
}

export async function createVendor(payload: VendorCreateRequest): Promise<Vendor> {
  return apiFetch<Vendor>("/api/vendors", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateVendor(
  id: number,
  payload: VendorUpdateRequest,
): Promise<Vendor> {
  return apiFetch<Vendor>(`/api/vendors/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deactivateVendor(id: number): Promise<void> {
  await apiFetch<{ message: string }>(`/api/vendors/${id}/deactivate`, {
    method: "POST",
  });
}
