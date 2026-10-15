import type { FuelPriceRow } from "../api/purchasing";

/**
 * Current board ₱/liter for a vendor and fuel type, or null if unset.
 */
export function lookupVendorFuelPrice(
  rows: FuelPriceRow[],
  vendorId: number | "" | null | undefined,
  fuelType: string | null | undefined,
): number | null {
  if (vendorId === "" || vendorId == null || !fuelType) {
    return null;
  }
  const row = rows.find((item) => item.vendor_id === Number(vendorId));
  if (!row) {
    return null;
  }
  const ft = fuelType.trim().toLowerCase();
  let raw: number | null | undefined;
  if (ft.includes("diesel")) {
    raw = row.diesel_price;
  } else if (ft.includes("unleaded")) {
    raw = row.unleaded_price;
  } else if (ft.includes("premium")) {
    raw = row.premium_price;
  } else {
    return null;
  }
  if (raw == null || Number(raw) <= 0) {
    return null;
  }
  return Number(raw);
}
