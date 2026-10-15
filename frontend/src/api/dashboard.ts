import { apiFetch } from "./client";

export interface ActiveUserRow {
  user_id: number;
  username: string;
  full_name?: string | null;
  role: string;
  device_count: number;
  is_online: boolean;
  login_at: string;
  last_seen_at: string;
  ip_address?: string;
}

export interface ActiveUsersData {
  idle_minutes: number;
  online_count: number;
  users: ActiveUserRow[];
}

export type DashboardScope = "all" | "used" | "cancelled";

export interface DashboardFilterOptions {
  companies: string[];
  vendors: { id: number; name: string }[];
  fuel_types: string[];
}

export interface DashboardSummary {
  vehicles: number;
  vendors: number;
  companies: number;
  all_requests: number;
  used_requests: number;
  cancelled_requests: number;
  all_pos: number;
  used_pos: number;
  cancelled_pos: number;
  filters: DashboardFilterOptions;
}

export interface DashboardListQuery {
  plate?: string;
  vendorId?: number;
  company?: string;
  fuelType?: string;
  dateFrom?: string;
  dateTo?: string;
  cancelledFrom?: string;
  cancelledTo?: string;
}

export interface DashboardVehicleRow {
  id: number;
  plate_number: string;
  model: string;
  company?: string | null;
  fuel_type?: string | null;
  assigned_to?: string | null;
  vendor_id?: number | null;
  vendor_name?: string | null;
  total_quantity?: number | null;
  total_price?: number | null;
}

export interface DashboardVendorRow {
  id: number;
  name: string;
  address?: string | null;
  total_quantity?: number | null;
  total_price?: number | null;
}

export interface DashboardCompanyRow {
  id: number;
  code: string;
  name: string;
  total_quantity?: number | null;
  total_price?: number | null;
}

export interface DashboardPriceTrendRow {
  year: number;
  month: number;
  fuel_type: string;
  avg_price: number;
  transaction_count: number;
}

export interface DashboardPriceStats {
  latest: number;
  min: number;
  max: number;
}

export interface DashboardTopVehicle {
  plate_number: string;
  model?: string | null;
  total_quantity: number;
  request_count: number;
}

export interface DashboardTopCompany {
  company: string;
  vehicles: DashboardTopVehicle[];
}

export interface DashboardAnalytics {
  year: number;
  month: number;
  price_trend: DashboardPriceTrendRow[];
  price_stats: Record<string, DashboardPriceStats>;
  top_consumers: DashboardTopCompany[];
}

export interface DashboardRequisitionRow {
  id: number;
  serial_number: string;
  po_reference?: string | null;
  quantity: number;
  unit: string;
  total_price?: number | null;
  status: string;
  fuel_type?: string | null;
  created_at?: string | null;
  po_created_at?: string | null;
  updated_at?: string | null;
  cancel_reason?: string | null;
  cancelled_by?: string | null;
  plate_number: string;
  model?: string | null;
  company?: string | null;
  vendor_name?: string | null;
}

function appendQuery(params: URLSearchParams, query?: DashboardListQuery): void {
  if (!query) {
    return;
  }
  if (query.plate) {
    params.set("plate", query.plate);
  }
  if (query.vendorId != null) {
    params.set("vendor_id", String(query.vendorId));
  }
  if (query.company) {
    params.set("company", query.company);
  }
  if (query.fuelType) {
    params.set("fuel_type", query.fuelType);
  }
  if (query.dateFrom) {
    params.set("date_from", query.dateFrom);
  }
  if (query.dateTo) {
    params.set("date_to", query.dateTo);
  }
  if (query.cancelledFrom) {
    params.set("cancelled_from", query.cancelledFrom);
  }
  if (query.cancelledTo) {
    params.set("cancelled_to", query.cancelledTo);
  }
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return apiFetch<DashboardSummary>("/api/dashboard/summary");
}

export async function listDashboardVehicles(
  query?: DashboardListQuery,
): Promise<DashboardVehicleRow[]> {
  const params = new URLSearchParams();
  appendQuery(params, query);
  const suffix = params.toString();
  return apiFetch<DashboardVehicleRow[]>(
    `/api/dashboard/vehicles${suffix ? `?${suffix}` : ""}`,
  );
}

export async function listDashboardVendors(): Promise<DashboardVendorRow[]> {
  return apiFetch<DashboardVendorRow[]>("/api/dashboard/vendors");
}

export async function listDashboardCompanies(): Promise<DashboardCompanyRow[]> {
  return apiFetch<DashboardCompanyRow[]>("/api/dashboard/companies");
}

export async function listDashboardRequests(
  scope: DashboardScope,
  query?: DashboardListQuery,
): Promise<DashboardRequisitionRow[]> {
  const params = new URLSearchParams({ scope });
  appendQuery(params, query);
  return apiFetch<DashboardRequisitionRow[]>(`/api/dashboard/requests?${params}`);
}

export async function listDashboardPos(
  scope: DashboardScope,
  query?: DashboardListQuery,
): Promise<DashboardRequisitionRow[]> {
  const params = new URLSearchParams({ scope });
  appendQuery(params, query);
  return apiFetch<DashboardRequisitionRow[]>(`/api/dashboard/pos?${params}`);
}

export async function getDashboardAnalytics(
  year: number,
  month: number,
  vendorId?: number,
): Promise<DashboardAnalytics> {
  const params = new URLSearchParams({
    year: String(year),
    month: String(month),
  });
  if (vendorId != null) {
    params.set("vendor_id", String(vendorId));
  }
  return apiFetch<DashboardAnalytics>(`/api/dashboard/analytics?${params}`);
}

export async function getActiveUsers(): Promise<ActiveUsersData> {
  return apiFetch<ActiveUsersData>("/api/dashboard/active-users");
}
