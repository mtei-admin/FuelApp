export type QuantityMode = "numeric" | "fulltank";

export interface Requisition {
  id: number;
  serial_number?: string | null;
  quantity: number;
  unit: string;
  unit_price?: number | null;
  total_price?: number | null;
  status: string;
  notes?: string | null;
  fuel_type?: string | null;
  requestor_name?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  is_edited: boolean;
  edited_by?: string | null;
  requester_id?: number | null;
  vehicle_id?: number | null;
  vendor_id?: number | null;
  plate_number?: string | null;
  model?: string | null;
  vendor_name?: string | null;
  can_edit: boolean;
  edit_error?: string | null;
  settlement_type?: string;
}

export interface PendingRequisition extends Requisition {
  requester_name?: string | null;
  display_total?: number | null;
  can_approve: boolean;
  approved_by?: string | null;
}

export interface RequestFormContext {
  vehicles: FormVehicle[];
  vendors: FormVendor[];
}

export interface FormVehicle {
  id: number;
  plate_number: string;
  model: string;
  vendor_id?: number | null;
  vendor_name?: string | null;
  fuel_type?: string | null;
  company?: string | null;
  assigned_to?: string | null;
}

export interface FormVendor {
  id: number;
  name: string;
  address?: string | null;
}

export interface RequisitionCreateRequest {
  vehicle_id: number;
  vendor_id: number;
  fuel_type: string;
  quantity_mode: QuantityMode;
  quantity: number;
  notes?: string;
  requestor_name: string;
  settlement_type?: SettlementType;
}

export type SettlementType = "vendor_invoice" | "credit_card";

export interface RequisitionUpdateRequest {
  vehicle_id: number;
  vendor_id: number;
  fuel_type: string;
  quantity_mode: QuantityMode;
  quantity: number;
  notes?: string;
  settlement_type?: SettlementType;
}

export interface ApprovalQuantityUpdateRequest {
  quantity_mode: QuantityMode;
  quantity: number;
  notes?: string;
}

export interface PriorApproved {
  vehicle_id: number;
  requests: Array<Record<string, unknown>>;
}

export interface VehicleHistoryItem {
  id: number;
  serial_number?: string | null;
  quantity: number;
  unit: string;
  status: string;
  fuel_type?: string | null;
  total_price?: number | null;
  created_at?: string | null;
  requestor_name?: string | null;
  vendor_name?: string | null;
}

export interface VehicleHistoryResponse {
  vehicle_id: number;
  limit: number;
  requests: VehicleHistoryItem[];
}
