import { apiFetch } from "./client";
import type {
  PmsScheduleUpdate,
  PmsSummary,
  PmsVehicle,
  PmsWorkOrder,
  PmsWorkOrderWrite,
} from "../types/pms";

export async function listPmsVehicles(): Promise<PmsVehicle[]> {
  return apiFetch<PmsVehicle[]>("/api/pms");
}

export async function getPmsSummary(): Promise<PmsSummary> {
  return apiFetch<PmsSummary>("/api/pms/summary");
}

export async function updatePmsSchedule(
  vehicleId: number,
  payload: PmsScheduleUpdate,
): Promise<PmsVehicle> {
  return apiFetch<PmsVehicle>(`/api/pms/schedules/${vehicleId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function getPmsWorkOrder(workOrderId: number): Promise<PmsWorkOrder> {
  return apiFetch<PmsWorkOrder>(`/api/pms/work-orders/${workOrderId}`);
}

export async function openPmsWorkOrder(payload: PmsWorkOrderWrite): Promise<PmsWorkOrder> {
  return apiFetch<PmsWorkOrder>("/api/pms/work-orders", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function savePmsWorkOrder(
  workOrderId: number,
  payload: PmsWorkOrderWrite,
): Promise<PmsWorkOrder> {
  return apiFetch<PmsWorkOrder>(`/api/pms/work-orders/${workOrderId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function completePmsWorkOrder(
  workOrderId: number,
  payload: PmsWorkOrderWrite,
): Promise<PmsWorkOrder> {
  return apiFetch<PmsWorkOrder>(`/api/pms/work-orders/${workOrderId}/complete`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function cancelPmsWorkOrder(workOrderId: number): Promise<PmsWorkOrder> {
  return apiFetch<PmsWorkOrder>(`/api/pms/work-orders/${workOrderId}/cancel`, {
    method: "POST",
  });
}

export async function listPmsHistory(vehicleId: number): Promise<PmsWorkOrder[]> {
  return apiFetch<PmsWorkOrder[]>(`/api/pms/vehicles/${vehicleId}/history`);
}
