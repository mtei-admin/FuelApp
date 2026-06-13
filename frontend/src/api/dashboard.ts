import { apiFetch } from "./client";

export interface DashboardData {
  year: number;
  month: number;
  vendors: { id: number; name: string }[];
  price_trend: Array<Record<string, unknown>>;
  price_stats: Record<string, { latest: number; min: number; max: number }>;
  usage_by_vehicle: Array<Record<string, unknown>>;
  usage_by_company: Array<Record<string, unknown>>;
  top_vehicles_by_company: Record<string, Array<Record<string, unknown>>>;
  fulltank_requests: Array<Record<string, unknown>>;
}

export async function getDashboard(
  year: number,
  month: number,
  vendorId?: number,
): Promise<DashboardData> {
  const params = new URLSearchParams({
    year: String(year),
    month: String(month),
  });
  if (vendorId) {
    params.set("vendor_id", String(vendorId));
  }
  return apiFetch<DashboardData>(`/api/dashboard?${params.toString()}`);
}
