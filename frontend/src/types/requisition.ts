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
}

export interface PendingRequisition extends Requisition {
  requester_name?: string | null;
  display_total?: number | null;
  can_approve: boolean;
}

export interface RequestFormContext {
  default_requestor_name: string;
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
}

export interface RequisitionUpdateRequest {
  vehicle_id: number;
  vendor_id: number;
  fuel_type: string;
  quantity_mode: QuantityMode;
  quantity: number;
  notes?: string;
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
