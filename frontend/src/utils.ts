import type { EntityStatus, OrderPriority, OrderStatus, Role } from "./types";

export const roleLabel: Record<Role, string> = {
  admin: "Admin",
  supervisor: "Supervisor",
  technician: "Técnico",
  attendant: "Atendente"
};

export const statusLabel: Record<EntityStatus, string> = {
  active: "Ativo",
  inactive: "Inativo"
};

export const orderStatusLabel: Record<OrderStatus, string> = {
  open: "Aberta",
  in_progress: "Em andamento",
  completed: "Concluída",
  cancelled: "Cancelada"
};

export const priorityLabel: Record<OrderPriority, string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  urgent: "Urgente"
};

export function formatCurrency(value: string | number | null | undefined): string {
  return new Intl.NumberFormat("pt-PT", {
    style: "currency",
    currency: "EUR"
  }).format(Number(value ?? 0));
}

export function formatDate(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("pt-PT");
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("pt-PT");
}

export function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "MT";
}

export function numeric(value: string | number | null | undefined): number {
  return Number(value ?? 0);
}

export function badgeClass(value: string): string {
  if (value === "urgent" || value === "cancelled" || value === "inactive") return "badge badge-danger";
  if (value === "high" || value === "medium" || value === "in_progress") return "badge badge-warning";
  if (value === "completed" || value === "active" || value === "open") return "badge badge-success";
  return "badge badge-muted";
}

export function can(role: Role | undefined, allowed: Role[]): boolean {
  return Boolean(role && allowed.includes(role));
}
