import { apiFetch } from "./client";
import type { ServiceCenter, ServiceCenterWriteRequest } from "../types/serviceCenter";

export async function listServiceCenters(): Promise<ServiceCenter[]> {
  return apiFetch<ServiceCenter[]>("/api/service-centers");
}

export async function createServiceCenter(
  payload: ServiceCenterWriteRequest,
): Promise<ServiceCenter> {
  return apiFetch<ServiceCenter>("/api/service-centers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateServiceCenter(
  id: number,
  payload: ServiceCenterWriteRequest,
): Promise<ServiceCenter> {
  return apiFetch<ServiceCenter>(`/api/service-centers/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deactivateServiceCenter(id: number): Promise<void> {
  await apiFetch<{ message: string }>(`/api/service-centers/${id}/deactivate`, {
    method: "POST",
  });
}

export async function reactivateServiceCenter(id: number): Promise<void> {
  await apiFetch<{ message: string }>(`/api/service-centers/${id}/reactivate`, {
    method: "POST",
  });
}
