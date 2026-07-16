export type FuelType = "Diesel" | "Unleaded Gasoline" | "Premium Gasoline";

export interface Vehicle {
  id: number;
  plate_number: string;
  model: string;
  vendor_id?: number | null;
  vendor_name?: string | null;
  fuel_type?: FuelType | string | null;
  company?: string | null;
  assigned_to?: string | null;
  is_active: boolean;
  created_at?: string | null;
}

export interface VehicleCreateRequest {
  plate_number: string;
  model: string;
  fuel_type: FuelType;
  company: string;
  vendor_id?: number | null;
  assigned_to: string;
}

export interface VehicleUpdateRequest extends VehicleCreateRequest {}

export interface VehicleOptions {
  fuel_types: FuelType[];
  companies: string[];
}
