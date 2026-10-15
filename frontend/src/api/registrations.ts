import { apiFetch } from "./client";
import type {
  RegistrationSummary,
  RegistrationUpdateRequest,
  VehicleRegistration,
} from "../types/registration";

export async function listRegistrations(): Promise<VehicleRegistration[]> {
  return apiFetch<VehicleRegistration[]>("/api/registrations");
}

export async function getRegistrationSummary(): Promise<RegistrationSummary> {
  return apiFetch<RegistrationSummary>("/api/registrations/summary");
}

export async function updateRegistration(
  vehicleId: number,
  payload: RegistrationUpdateRequest,
): Promise<VehicleRegistration> {
  return apiFetch<VehicleRegistration>(`/api/registrations/${vehicleId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
