export type RegistrationAlertStatus =
  | "missing"
  | "expired"
  | "due_soon"
  | "current";

export interface VehicleRegistration {
  id: number;
  plate_number: string;
  model: string;
  company?: string | null;
  assigned_to?: string | null;
  registration_date?: string | null;
  lto_expiry?: string | null;
  expiration_date?: string | null;
  or_number?: string | null;
  cr_number?: string | null;
  mv_file_no?: string | null;
  registration_remarks?: string | null;
  is_company_owned?: boolean;
  alert_status: RegistrationAlertStatus;
  days_until_expiry?: number | null;
}

export interface RegistrationUpdateRequest {
  registration_date?: string | null;
  lto_expiry?: string | null;
  or_number?: string | null;
  cr_number?: string | null;
  mv_file_no?: string | null;
  registration_remarks?: string | null;
}

export interface RegistrationSummary {
  total: number;
  expired: number;
  due_soon: number;
  missing: number;
  current: number;
  due_soon_days: number;
}
