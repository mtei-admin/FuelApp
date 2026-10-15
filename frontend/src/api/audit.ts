import { apiFetch } from "./client";

export interface AuditLogEntry {
  id: number;
  entity_type: string;
  entity_id: number;
  action: string;
  actor_user_id?: number | null;
  actor_username?: string | null;
  actor_role?: string | null;
  actor_name?: string | null;
  old_values: Record<string, unknown>;
  new_values: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at?: string | null;
  entity_label?: string | null;
}

export async function listAuditLog(params?: {
  entity_type?: string;
  entity_id?: number;
  q?: string;
  limit?: number;
}): Promise<AuditLogEntry[]> {
  const search = new URLSearchParams();
  if (params?.entity_type) search.set("entity_type", params.entity_type);
  if (params?.entity_id != null) search.set("entity_id", String(params.entity_id));
  if (params?.q) search.set("q", params.q);
  if (params?.limit != null) search.set("limit", String(params.limit));
  const qs = search.toString();
  return apiFetch<AuditLogEntry[]>(`/api/audit${qs ? `?${qs}` : ""}`);
}
