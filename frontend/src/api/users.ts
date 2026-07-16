import { apiFetch } from "./client";
import type {
  AdminUser,
  UserCreateRequest,
  UserUpdateRequest,
} from "../types/userAdmin";

export async function listUsers(): Promise<AdminUser[]> {
  return apiFetch<AdminUser[]>("/api/users");
}

export async function createUser(payload: UserCreateRequest): Promise<AdminUser> {
  return apiFetch<AdminUser>("/api/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateUser(
  id: number,
  payload: UserUpdateRequest,
): Promise<AdminUser> {
  return apiFetch<AdminUser>(`/api/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deactivateUser(id: number): Promise<void> {
  await apiFetch<{ message: string }>(`/api/users/${id}/deactivate`, {
    method: "POST",
  });
}

export async function reactivateUser(id: number): Promise<void> {
  await apiFetch<{ message: string }>(`/api/users/${id}/reactivate`, {
    method: "POST",
  });
}
