export interface Vendor {
  id: number;
  name: string;
  address?: string | null;
  is_active: boolean;
  created_at?: string | null;
}

export interface VendorCreateRequest {
  name: string;
  address?: string;
}

export interface VendorUpdateRequest {
  name: string;
  address?: string;
}
