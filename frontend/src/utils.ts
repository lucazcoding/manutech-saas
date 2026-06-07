import type { EntityStatus, OrderPriority, OrderStatus, Role } from "./types";

export const roleLabel: Record<Role, string> = {
  admin: "Administrador",
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

export const costTypeLabel: Record<string, string> = {
  material: "Material",
  labor: "Mão de obra",
  service: "Serviço",
  other: "Outro"
};

export const budgetStatusLabel: Record<string, string> = {
  draft: "Rascunho",
  sent: "Enviado",
  approved: "Aprovado",
  rejected: "Rejeitado",
  expired: "Expirado"
};

export function formatCurrency(value: string | number | null | undefined): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL"
  }).format(Number(value ?? 0));
}

export function formatDate(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("pt-BR");
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("pt-BR");
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
  if (value === "urgent" || value === "cancelled" || value === "inactive" || value === "rejected" || value === "expired") {
    return "badge badge-danger";
  }
  if (value === "high") return "badge badge-warning";
  if (value === "medium" || value === "in_progress" || value === "sent") return "badge badge-info";
  if (value === "completed" || value === "active" || value === "open" || value === "approved" || value === "draft") {
    return "badge badge-success";
  }
  return "badge badge-muted";
}

export function can(role: Role | undefined, allowed: Role[]): boolean {
  return Boolean(role && allowed.includes(role));
}
