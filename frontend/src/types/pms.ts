export type PmsAlertStatus = "missing" | "overdue" | "due_soon" | "current";

export type PmsWorkOrderStatus = "open" | "completed" | "cancelled";

export type PmsRepairType = "preventive_maintenance" | "change_oil" | "inspection";

export type PmsTerms = "cash" | "15_days" | "30_days";

export type PmsLineType = "parts" | "lubricants" | "services" | "others";

export type PmsLineUnit = "pcs" | "liters" | "lot" | "job";

export interface PmsVehicle {
  id: number;
  plate_number: string;
  model: string;
  company?: string | null;
  assigned_to?: string | null;
  interval_months?: number | null;
  next_due_date?: string | null;
  interval_km?: number | null;
  last_odometer_km?: number | null;
  last_service_date?: string | null;
  alert_status: PmsAlertStatus;
  days_until_due?: number | null;
  open_work_order_id?: number | null;
  open_work_order_description?: string | null;
  previous_odometer?: number | null;
}

export interface PmsSummary {
  total: number;
  overdue: number;
  due_soon: number;
  missing: number;
  current: number;
  open_jobs: number;
  due_soon_days: number;
}

export interface PmsScheduleUpdate {
  interval_months?: number | null;
  next_due_date?: string | null;
  interval_km?: number | null;
  last_odometer_km?: number | null;
}

export interface PmsWorkOrderLine {
  id?: number;
  work_order_id?: number;
  line_no?: number;
  part_code?: string | null;
  line_type: PmsLineType;
  description: string;
  unit: PmsLineUnit;
  quantity: number;
  unit_price: number;
  discount: number;
  total_amount?: number;
}

export interface PmsWorkOrderWrite {
  vehicle_id: number;
  transaction_no?: string | null;
  doc_date?: string | null;
  repair_type?: PmsRepairType | null;
  service_advisor?: string | null;
  technician?: string | null;
  terms?: PmsTerms | null;
  shop_name?: string | null;
  remarks?: string | null;
  current_odometer?: number | null;
  lines: PmsWorkOrderLine[];
}

export interface PmsWorkOrder {
  id: number;
  vehicle_id: number;
  job_type: string;
  status: PmsWorkOrderStatus;
  description?: string | null;
  shop_name?: string | null;
  cost?: number | null;
  notes?: string | null;
  remarks?: string | null;
  opened_at: string;
  service_date?: string | null;
  doc_date?: string | null;
  transaction_no?: string | null;
  repair_type?: string | null;
  service_advisor?: string | null;
  technician?: string | null;
  terms?: string | null;
  previous_odometer?: number | null;
  current_odometer?: number | null;
  completed_at?: string | null;
  completed_by_user_id?: number | null;
  completed_by_name?: string | null;
  plate_number?: string | null;
  model?: string | null;
  company?: string | null;
  assigned_to?: string | null;
  lines: PmsWorkOrderLine[];
}
