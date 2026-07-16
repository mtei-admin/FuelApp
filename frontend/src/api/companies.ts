import { apiFetch } from "./client";
import type {
  ActiveCompanyCodes,
  Company,
  CompanyCreateRequest,
  CompanyUpdateRequest,
} from "../types/company";

export async function listCompanies(): Promise<Company[]> {
  return apiFetch<Company[]>("/api/companies");
}

export async function listActiveCompanyCodes(): Promise<ActiveCompanyCodes> {
  return apiFetch<ActiveCompanyCodes>("/api/companies/active-codes");
}

export async function createCompany(payload: CompanyCreateRequest): Promise<Company> {
  return apiFetch<Company>("/api/companies", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateCompany(
  id: number,
  payload: CompanyUpdateRequest,
): Promise<Company> {
  return apiFetch<Company>(`/api/companies/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deactivateCompany(id: number): Promise<void> {
  await apiFetch<{ message: string }>(`/api/companies/${id}/deactivate`, {
    method: "POST",
  });
}

export async function reactivateCompany(id: number): Promise<void> {
  await apiFetch<{ message: string }>(`/api/companies/${id}/reactivate`, {
    method: "POST",
  });
}
