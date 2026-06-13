export type FuelType = "Diesel" | "Unleaded Gasoline" | "Premium Gasoline";
export type CompanyName = "MTEI" | "DSRDC" | "DIC" | "GCEIC" | "MTEI Trucking";

export interface Vehicle {
  id: number;
  plate_number: string;
  model: string;
  vendor_id?: number | null;
  vendor_name?: string | null;
  fuel_type?: FuelType | string | null;
  company?: CompanyName | string | null;
  driver_name?: string | null;
  is_active: boolean;
  created_at?: string | null;
}

export interface VehicleCreateRequest {
  plate_number: string;
  model: string;
  fuel_type: FuelType;
  company: CompanyName;
  vendor_id?: number | null;
  driver_name?: string | null;
}

export interface VehicleUpdateRequest extends VehicleCreateRequest {}

export interface VehicleOptions {
  fuel_types: FuelType[];
  companies: CompanyName[];
}
