import { apiFetch } from "./client";
import type {
  Vehicle,
  VehicleCreateRequest,
  VehicleOptions,
  VehicleUpdateRequest,
} from "../types/vehicle";

export async function listVehicles(): Promise<Vehicle[]> {
  return apiFetch<Vehicle[]>("/api/vehicles");
}

export async function getVehicleOptions(): Promise<VehicleOptions> {
  return apiFetch<VehicleOptions>("/api/vehicles/options");
}

export async function createVehicle(payload: VehicleCreateRequest): Promise<Vehicle> {
  return apiFetch<Vehicle>("/api/vehicles", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateVehicle(
  id: number,
  payload: VehicleUpdateRequest,
): Promise<Vehicle> {
  return apiFetch<Vehicle>(`/api/vehicles/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deactivateVehicle(id: number): Promise<void> {
  await apiFetch<{ message: string }>(`/api/vehicles/${id}/deactivate`, {
    method: "POST",
  });
}
