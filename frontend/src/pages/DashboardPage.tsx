import { AlertTriangle, Clock3, History, Info } from "lucide-react";
import { StatCard } from "../components/StatCard";
import { Table } from "../components/Table";
import type { Asset, Material, NotificationItem, OrderStats, Role, ServiceOrder, User } from "../types";
import { badgeClass, formatDateTime, numeric, orderStatusLabel, priorityLabel, roleLabel } from "../utils";

interface DashboardPageProps {
  user: User;
  stats: OrderStats | null;
  orders: ServiceOrder[];
  assets: Asset[];
  materials: Material[];
  notifications: NotificationItem[];
}

const roleHint: Record<Role, { title: string; description: string }> = {
  admin: {
    title: "Visão global do sistema",
    description: "Você gerencia usuários, operações, finanças e auditoria. Use esta tela para acompanhar os indicadores críticos da operação."
  },
  supervisor: {
    title: "Coordenação operacional",
    description: "Crie e atribua ordens, gerencie materiais, acompanhe custos e auditoria. Você é quem dispara a maior parte do fluxo de execução."
  },
  technician: {
    title: "Suas ordens atribuídas aparecem aqui",
    description: "Você vê apenas as OS que estão com você. Use o botão Iniciar/Concluir em cada ordem para avançar o status. Acompanhe também as notificações no sino para novas atribuições."
  },
  attendant: {
    title: "Atendimento de chamados",
    description: "Registre novas ordens de serviço a partir das solicitações dos clientes. Você tem acesso à consulta de equipamentos e materiais para apoiar o atendimento."
  }
};

export function DashboardPage({ user, stats, orders, assets, materials, notifications }: DashboardPageProps) {
  const open = stats?.by_status.open ?? orders.filter((item) => item.status === "open").length;
  const progress = stats?.by_status.in_progress ?? orders.filter((item) => item.status === "in_progress").length;
  const done = stats?.by_status.completed ?? orders.filter((item) => item.status === "completed").length;
  const lowStock = materials.filter((item) => numeric(item.quantity_in_stock) <= numeric(item.min_quantity)).length;
  const myAssigned = user.role === "technician" ? orders.filter((item) => item.assigned_technician?.id === user.id) : [];
  const myOpen = myAssigned.filter((item) => item.status === "open" || item.status === "in_progress").length;
  const criticalOrders = orders
    .filter((item) => item.priority === "urgent" || item.priority === "high" || item.status === "open")
    .slice(0, 6);
  const inactiveAssets = assets.filter((item) => item.status === "inactive").length;

  const hint = roleHint[user.role];

  return (
    <section className="page-stack">
      <div className="role-banner">
        <Info size={20} />
        <div>
          <strong>
            Olá, {user.name} — {roleLabel[user.role]}
          </strong>
          <p>{hint.title}: {hint.description}</p>
        </div>
      </div>

      {user.role === "technician" ? (
        <div className="stats-grid">
          <StatCard label="OS atribuídas a mim" value={myAssigned.length} />
          <StatCard label="Em aberto / em andamento" value={myOpen} tone="amber" />
          <StatCard label="Concluídas por mim" value={myAssigned.filter((item) => item.status === "completed").length} tone="green" />
          <StatCard label="Sem técnico atribuído" value={orders.filter((item) => !item.assigned_technician && item.status === "open").length} tone="red" />
        </div>
      ) : (
        <div className="stats-grid">
          <StatCard label="Ordens de serviço abertas" value={open} />
          <StatCard label="Em diagnóstico / execução" value={progress} tone="amber" />
          <StatCard label="Concluídas" value={done} tone="green" />
          <StatCard label="Alertas de estoque baixo" value={lowStock} tone="red" />
        </div>
      )}

      <div className="dashboard-grid">
        <section>
          <div className="section-heading">
            <div>
              <h2>{user.role === "technician" ? "Minhas ordens prioritárias" : "Próximas manutenções críticas"}</h2>
              <p>
                {user.role === "technician"
                  ? "Suas OS com prioridade alta/urgente ou ainda em aberto."
                  : "Prioridade e estado das ordens mais sensíveis."}
              </p>
            </div>
            <Clock3 size={20} />
          </div>
          <Table columns={["OS", "Cliente", "Equipamento", "Prioridade", "Status"]} empty={!criticalOrders.length}>
            {criticalOrders.map((order) => (
              <tr key={order.id}>
                <td>
                  OS-{String(order.order_number).padStart(3, "0")}
                  {user.role === "technician" && order.assigned_technician?.id === user.id ? (
                    <small className="muted">você</small>
                  ) : null}
                </td>
                <td>{order.client_name}</td>
                <td>{order.asset?.name ?? "-"}</td>
                <td>
                  <span className={badgeClass(order.priority)}>{priorityLabel[order.priority]}</span>
                </td>
                <td>
                  <span className={badgeClass(order.status)}>{orderStatusLabel[order.status]}</span>
                </td>
              </tr>
            ))}
          </Table>
        </section>

        <section>
          <div className="section-heading">
            <div>
              <h2>Atividade recente</h2>
              <p>Notificações e sinais do sistema.</p>
            </div>
            <History size={20} />
          </div>
          <div className="activity-list">
            {user.role !== "technician" && inactiveAssets ? (
              <div className="activity-item">
                <AlertTriangle size={16} />
                <span>{inactiveAssets} equipamento(s) inativo(s).</span>
              </div>
            ) : null}
            {notifications.slice(0, 6).map((item) => (
              <div className="activity-item" key={item.id}>
                <span className={item.read ? "dot dot-muted" : "dot"} />
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.message}</p>
                  <small>{formatDateTime(item.created_at)}</small>
                </div>
              </div>
            ))}
            {!notifications.length ? (
              <div className="empty-state">
                {user.role === "technician"
                  ? "Você não tem notificações. Novas atribuições aparecerão aqui assim que o supervisor lhe designar uma OS."
                  : "Sem atividade recente."}
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </section>
  );
}
