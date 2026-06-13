import { apiFetch } from "./client";
import type {
  ApprovalQuantityUpdateRequest,
  PendingRequisition,
} from "../types/requisition";

export async function getPendingCount(): Promise<number> {
  const data = await apiFetch<{ count: number }>("/api/approvals/pending/count");
  return data.count;
}

export async function listPendingApprovals(): Promise<PendingRequisition[]> {
  return apiFetch<PendingRequisition[]>("/api/approvals/pending");
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

export async function updateApprovalQuantity(
  id: number,
  payload: ApprovalQuantityUpdateRequest,
): Promise<void> {
  await apiFetch<{ message: string }>(`/api/approvals/${id}/quantity`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
