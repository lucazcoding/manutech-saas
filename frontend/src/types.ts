export type Role = "admin" | "supervisor" | "technician" | "attendant";
export type EntityStatus = "active" | "inactive";
export type OrderStatus = "open" | "in_progress" | "completed" | "cancelled";
export type OrderPriority = "low" | "medium" | "high" | "urgent";
export type MovementType = "in" | "out";
export type CostType = "material" | "labor" | "service" | "other";
export type BudgetStatus = "draft" | "sent" | "approved" | "rejected" | "expired";

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface User {
  id: number;
  name: string;
  login: string;
  email?: string;
  role: Role;
  status: EntityStatus;
  created_at?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Asset {
  id: number;
  name: string;
  model?: string | null;
  manufacturer?: string | null;
  serial_number?: string | null;
  location?: string | null;
  status: EntityStatus;
  created_at: string;
  updated_at: string;
}

export interface OrderAssetSummary {
  id: number;
  name: string;
  serial_number?: string | null;
}

export interface TechnicianSummary {
  id: number;
  name: string;
}

export interface ServiceOrder {
  id: number;
  order_number: number;
  client_name: string;
  location: string;
  description?: string | null;
  status: OrderStatus;
  priority: OrderPriority;
  total_cost: string | number;
  start_date?: string | null;
  asset?: OrderAssetSummary | null;
  assigned_technician?: TechnicianSummary | null;
  created_at: string;
  updated_at: string;
}

export interface OrderStats {
  total: number;
  by_status: Record<OrderStatus | string, number>;
  by_priority: Record<OrderPriority | string, number>;
}

export interface AuditLogEntry {
  id: number | string;
  action: string;
  module?: string;
  target?: string;
  delta?: unknown;
  changed_by?: number | null;
  created_at: string;
}

export interface Attachment {
  id: number;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  file_path: string;
  created_at: string;
}

export interface Material {
  id: number;
  name: string;
  sku: string;
  unit_price: string | number;
  quantity_in_stock: string | number;
  min_quantity: string | number;
  status: EntityStatus;
  created_at: string;
  updated_at: string;
}

export interface StockReportItem extends Material {
  is_low_stock: boolean;
}

export interface Movement {
  id: number;
  material_id: number;
  service_order_id?: number | null;
  movement_type: MovementType;
  quantity: string | number;
  notes?: string | null;
  created_at: string;
}

export interface Cost {
  id: number;
  service_order_id: number;
  description: string;
  amount: string | number;
  cost_type: CostType;
  created_at: string;
}

export interface BudgetItem {
  id: number;
  description: string;
  quantity: string | number;
  unit_price: string | number;
  created_at: string;
}

export interface Budget {
  id: number;
  budget_number: number;
  service_order_id?: number | null;
  client_name: string;
  description?: string | null;
  total_amount: string | number;
  status: string;
  valid_until?: string | null;
  created_by?: number | null;
  items: BudgetItem[];
  created_at: string;
  updated_at: string;
}

export interface FinancialReport {
  total_costs: string | number;
  costs_by_type: Record<string, string | number>;
  orders_count: number;
  avg_cost_per_order: string | number;
}

export interface NotificationItem {
  id: number;
  user_id: number;
  type: string;
  title: string;
  message: string;
  read: boolean;
  related_id?: number | null;
  created_at: string;
}

export interface CreateUserPayload {
  name: string;
  login: string;
  email: string;
  password: string;
  role: Role;
}

export interface CreateAssetPayload {
  name: string;
  model?: string | null;
  manufacturer?: string | null;
  serial_number?: string | null;
  location?: string | null;
}

export interface CreateOrderPayload {
  client_name: string;
  location: string;
  description?: string | null;
  priority?: OrderPriority;
  start_date?: string | null;
  asset_id?: number | null;
}

export interface CreateMaterialPayload {
  name: string;
  sku: string;
  unit_price: number;
  quantity_in_stock?: number;
  min_quantity?: number;
}

export interface CreateCostPayload {
  service_order_id: number;
  description: string;
  amount: number;
  cost_type?: CostType;
}

export interface CreateMovementPayload {
  material_id: number;
  service_order_id?: number | null;
  movement_type: MovementType;
  quantity: number;
  notes?: string | null;
}

export interface CreateBudgetItemPayload {
  description: string;
  quantity: number;
  unit_price: number;
}

export interface CreateBudgetPayload {
  service_order_id?: number | null;
  client_name: string;
  description?: string | null;
  valid_until?: string | null;
  items: CreateBudgetItemPayload[];
}

export interface UpdateBudgetPayload {
  client_name?: string;
  description?: string | null;
  valid_until?: string | null;
  items?: CreateBudgetItemPayload[];
}
