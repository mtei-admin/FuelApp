export interface ServiceCenter {
  id: number;
  name: string;
  address: string;
  contact_no: string;
  is_active: boolean;
  created_at?: string | null;
}

export interface ServiceCenterWriteRequest {
  name: string;
  address: string;
  contact_no: string;
}
