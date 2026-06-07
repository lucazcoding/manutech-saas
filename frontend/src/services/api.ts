import type {
  Asset,
  Attachment,
  AuditLogEntry,
  Budget,
  BudgetStatus,
  Cost,
  CreateAssetPayload,
  CreateBudgetPayload,
  CreateCostPayload,
  CreateMaterialPayload,
  CreateMovementPayload,
  CreateOrderPayload,
  CreateUserPayload,
  EntityStatus,
  FinancialReport,
  Material,
  Movement,
  MovementType,
  NotificationItem,
  OrderStats,
  OrderStatus,
  PaginatedResponse,
  ServiceOrder,
  TokenResponse,
  UpdateBudgetPayload,
  User
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || "";
const TOKEN_KEY = "manutech.accessToken";
const REFRESH_KEY = "manutech.refreshToken";

type QueryValue = string | number | boolean | null | undefined;
type RequestOptions = Omit<RequestInit, "body"> & { body?: unknown; retry?: boolean };

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function saveTokens(accessToken: string, refreshToken?: string): void {
  localStorage.setItem(TOKEN_KEY, accessToken);
  if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const base = API_BASE_URL.replace(/\/$/, "");
  const url = new URL(`${base}${path}`, window.location.origin);

  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });

  return url.toString();
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) return null;

  const response = await fetch(buildUrl("/auth/refresh"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken })
  });

  if (!response.ok) {
    clearTokens();
    return null;
  }

  const data = (await response.json()) as { access_token: string };
  saveTokens(data.access_token);
  return data.access_token;
}

async function request<T>(path: string, options: RequestOptions = {}, query?: Record<string, QueryValue>): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(options.headers);

  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(buildUrl(path, query), {
    ...options,
    headers,
    body: options.body instanceof FormData ? options.body : options.body ? JSON.stringify(options.body) : undefined
  });

  if (response.status === 401 && options.retry !== false) {
    const refreshedToken = await refreshAccessToken();
    if (refreshedToken) return request<T>(path, { ...options, retry: false }, query);
  }

  if (!response.ok) {
    let message = `Erro ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: string | { msg?: string }[] };
      if (typeof data.detail === "string") message = data.detail;
      if (Array.isArray(data.detail)) message = data.detail.map((item) => item.msg).join("; ");
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const token = getAccessToken();
  const response = await fetch(buildUrl(path), {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined
  });
  if (!response.ok) throw new Error(`Erro ${response.status}`);

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;

  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/i);
  a.download = match?.[1] ?? fallbackName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export const api = {
  auth: {
    async login(login: string, password: string) {
      const data = await request<TokenResponse>("/auth/login", {
        method: "POST",
        body: { login, password },
        retry: false
      });
      saveTokens(data.access_token, data.refresh_token);
      return data;
    },
    me: () => request<User>("/auth/me"),
    logout: async () => {
      const refreshToken = localStorage.getItem(REFRESH_KEY);
      if (refreshToken) {
        await request<void>("/auth/logout", { method: "POST", body: { refresh_token: refreshToken } });
      }
      clearTokens();
    }
  },
  users: {
    list: (query?: Record<string, QueryValue>) => request<PaginatedResponse<User>>("/users", {}, query),
    create: (body: CreateUserPayload) => request<User>("/users", { method: "POST", body }),
    update: (id: number, body: Partial<Pick<User, "name" | "email" | "role">>) =>
      request<User>(`/users/${id}`, { method: "PUT", body }),
    setStatus: (id: number, status: EntityStatus) =>
      request<{ id: number; status: EntityStatus; updated_at: string }>(`/users/${id}/status`, {
        method: "PATCH",
        body: { status }
      })
  },
  assets: {
    list: (query?: Record<string, QueryValue>) => request<PaginatedResponse<Asset>>("/assets", {}, query),
    create: (body: CreateAssetPayload) => request<Asset>("/assets", { method: "POST", body }),
    update: (id: number, body: Partial<CreateAssetPayload>) => request<Asset>(`/assets/${id}`, { method: "PUT", body }),
    setStatus: (id: number, status: EntityStatus) =>
      request<{ id: number; status: EntityStatus; updated_at: string }>(`/assets/${id}/status`, {
        method: "PATCH",
        body: { status }
      }),
    orders: (id: number, query?: Record<string, QueryValue>) =>
      request<PaginatedResponse<ServiceOrder>>(`/assets/${id}/orders`, {}, query)
  },
  orders: {
    stats: () => request<OrderStats>("/orders/stats"),
    list: (query?: Record<string, QueryValue>) => request<PaginatedResponse<ServiceOrder>>("/orders", {}, query),
    get: (id: number) => request<ServiceOrder>(`/orders/${id}`),
    create: (body: CreateOrderPayload) => request<ServiceOrder>("/orders", { method: "POST", body }),
    update: (id: number, body: Partial<CreateOrderPayload>) =>
      request<ServiceOrder>(`/orders/${id}`, { method: "PUT", body }),
    remove: (id: number) => request<void>(`/orders/${id}`, { method: "DELETE" }),
    setStatus: (id: number, status: OrderStatus, reason?: string) =>
      request<ServiceOrder>(`/orders/${id}/status`, { method: "PATCH", body: { status, reason } }),
    assign: (id: number, technicianId: number) =>
      request<ServiceOrder>(`/orders/${id}/assign`, { method: "PATCH", body: { technician_id: technicianId } }),
    requestCompletion: (id: number) =>
      request<ServiceOrder>(`/orders/${id}/request-completion`, { method: "POST" }),
    history: (id: number) => request<AuditLogEntry[]>(`/orders/${id}/history`),
    attachments: (id: number) => request<Attachment[]>(`/orders/${id}/attachments`),
    uploadAttachment: (id: number, file: File) => {
      const data = new FormData();
      data.append("file", file);
      return request<Attachment>(`/orders/${id}/attachments`, { method: "POST", body: data });
    },
    downloadAttachment: (id: number, attachmentId: number) =>
      downloadFile(`/orders/${id}/attachments/${attachmentId}/download`, `anexo-${attachmentId}`)
  },
  inventory: {
    materials: (query?: Record<string, QueryValue>) => request<PaginatedResponse<Material>>("/materials", {}, query),
    stockReport: () => request<Material[]>("/stock/report"),
    createMaterial: (body: CreateMaterialPayload) => request<Material>("/materials", { method: "POST", body }),
    updateMaterial: (id: number, body: Partial<Omit<CreateMaterialPayload, "quantity_in_stock">>) =>
      request<Material>(`/materials/${id}`, { method: "PUT", body }),
    setMaterialStatus: (id: number, status: EntityStatus) =>
      request<{ id: number; status: EntityStatus; updated_at: string }>(`/materials/${id}/status`, {
        method: "PATCH",
        body: { status }
      }),
    movements: (query?: Record<string, QueryValue>) => request<PaginatedResponse<Movement>>("/movements", {}, query),
    createMovement: (body: CreateMovementPayload) => request<Movement>("/movements", { method: "POST", body })
  },
  finance: {
    report: () => request<FinancialReport>("/reports/financial"),
    exportReport: (format: "excel" | "pdf") =>
      downloadFile(`/reports/financial/export?format=${format}`, `relatorio.${format === "excel" ? "csv" : "txt"}`),
    costs: (query?: Record<string, QueryValue>) => request<PaginatedResponse<Cost>>("/costs", {}, query),
    createCost: (body: CreateCostPayload) => request<Cost>("/costs", { method: "POST", body }),
    updateCost: (id: number, body: Partial<{ description: string; amount: number; cost_type: string }>) =>
      request<Cost>(`/costs/${id}`, { method: "PUT", body }),
    removeCost: (id: number) => request<void>(`/costs/${id}`, { method: "DELETE" }),
    budgets: (query?: Record<string, QueryValue>) => request<PaginatedResponse<Budget>>("/budgets", {}, query),
    getBudget: (id: number) => request<Budget>(`/budgets/${id}`),
    createBudget: (body: CreateBudgetPayload) => request<Budget>("/budgets", { method: "POST", body }),
    updateBudget: (id: number, body: UpdateBudgetPayload) =>
      request<Budget>(`/budgets/${id}`, { method: "PUT", body }),
    setBudgetStatus: (id: number, status: BudgetStatus) =>
      request<Budget>(`/budgets/${id}/status`, { method: "PATCH", body: { status } }),
    orderBudget: (orderId: number) => request<Budget>(`/orders/${orderId}/budget`)
  },
  notifications: {
    list: (query?: Record<string, QueryValue>) => request<PaginatedResponse<NotificationItem>>("/notifications", {}, query),
    markRead: (id: number) => request<{ id: number; read: boolean }>(`/notifications/${id}/read`, { method: "PATCH" }),
    wsUrl: () => {
      const token = getAccessToken();
      if (!token) return null;
      const explicit = WS_BASE_URL.replace(/\/$/, "");
      if (explicit) return `${explicit}/notifications/ws?token=${encodeURIComponent(token)}`;
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      return `${protocol}://${window.location.host}${API_BASE_URL}/notifications/ws?token=${encodeURIComponent(token)}`;
    }
  }
};
