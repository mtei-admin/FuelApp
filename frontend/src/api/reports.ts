import { apiFetch } from "./client";

export interface ReportFilters {
  plate?: string;
  vendor?: string;
  from?: string;
  to?: string;
}

export interface ReportGroup {
  label: string;
  count: number;
  total: number;
  rows: Record<string, unknown>[];
}

export interface ReportSummary {
  groups: ReportGroup[];
  rows: Record<string, unknown>[];
  grand_total: number;
  vendors: { id: number; name: string }[];
}

function queryString(filters: ReportFilters): string {
  const params = new URLSearchParams();
  if (filters.plate) params.set("plate", filters.plate);
  if (filters.vendor) params.set("vendor", filters.vendor);
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export async function getReportSummary(
  filters: ReportFilters,
): Promise<ReportSummary> {
  return apiFetch<ReportSummary>(`/api/reports/summary${queryString(filters)}`);
}

export function reportCsvUrl(filters: ReportFilters): string {
  return `/api/reports/export/csv${queryString(filters)}`;
}

export function reportPdfUrl(filters: ReportFilters): string {
  return `/api/reports/export/pdf${queryString(filters)}`;
}
