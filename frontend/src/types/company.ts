export interface Company {
  id: number;
  code: string;
  name: string;
  is_active: boolean;
  created_at?: string | null;
}

export interface CompanyCreateRequest {
  code: string;
  name: string;
}

export interface CompanyUpdateRequest {
  name: string;
}

export interface ActiveCompanyCodes {
  companies: string[];
}
