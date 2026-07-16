import { apiFetch } from "./client";
import type {
  ApprovalQuantityUpdateRequest,
  PendingRequisition,
  VehicleHistoryResponse,
} from "../types/requisition";

export async function getPendingCount(): Promise<number> {
  const data = await apiFetch<{ count: number }>("/api/approvals/pending/count");
  return data.count;
}

export async function listPendingApprovals(): Promise<PendingRequisition[]> {
  return apiFetch<PendingRequisition[]>("/api/approvals/pending");
}

export async function listApprovedAwaitingPo(): Promise<PendingRequisition[]> {
  return apiFetch<PendingRequisition[]>("/api/approvals/approved-awaiting-po");
}

export async function getVehicleHistory(
  vehicleId: number,
  limit = 10,
): Promise<VehicleHistoryResponse> {
  return apiFetch<VehicleHistoryResponse>(
    `/api/approvals/vehicle-history/${vehicleId}?limit=${limit}`,
  );
}

export async function approveRequisition(id: number): Promise<void> {
  await apiFetch<{ message: string }>(`/api/approvals/${id}/approve`, {
    method: "POST",
  });
}

export async function rejectRequisition(id: number): Promise<void> {
  await apiFetch<{ message: string }>(`/api/approvals/${id}/reject`, {
    method: "POST",
  });
}

export async function cancelApprovedRequisition(
  id: number,
  reason: string,
): Promise<void> {
  await apiFetch<{ message: string }>(`/api/approvals/${id}/cancel`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function updateApprovalQuantity(
  id: number,
  payload: ApprovalQuantityUpdateRequest,
): Promise<void> {
  await apiFetch<{ message: string }>(`/api/approvals/${id}/quantity`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
