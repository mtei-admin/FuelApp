import { apiFetch } from "./client";
import type { LoginRequest, User } from "../types/auth";

export async function login(payload: LoginRequest): Promise<User> {
  return apiFetch<User>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function logout(): Promise<void> {
  await apiFetch<{ message: string }>("/api/auth/logout", {
    method: "POST",
  });
}

export async function getCurrentUser(): Promise<User> {
  return apiFetch<User>("/api/auth/me");
}
