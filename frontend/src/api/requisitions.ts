import { apiFetch } from "./client";
import type {
  ApprovalQuantityUpdateRequest,
  PendingRequisition,
  PriorApproved,
  Requisition,
  RequisitionCreateRequest,
  RequisitionUpdateRequest,
  RequestFormContext,
} from "../types/requisition";

export async function getRequestFormContext(): Promise<RequestFormContext> {
  return apiFetch<RequestFormContext>("/api/requisitions/form-context");
}

export async function getPriorApproved(vehicleId: number): Promise<PriorApproved> {
  return apiFetch<PriorApproved>(`/api/requisitions/prior-approved/${vehicleId}`);
}

export async function listMyRequisitions(): Promise<Requisition[]> {
  return apiFetch<Requisition[]>("/api/requisitions");
}

export async function createRequisition(
  payload: RequisitionCreateRequest,
): Promise<Requisition> {
  return apiFetch<Requisition>("/api/requisitions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateRequisition(
  id: number,
  payload: RequisitionUpdateRequest,
): Promise<Requisition> {
  return apiFetch<Requisition>(`/api/requisitions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
