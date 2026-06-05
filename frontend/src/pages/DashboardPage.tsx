import { AlertTriangle, Clock3, History } from "lucide-react";
import { StatCard } from "../components/StatCard";
import { Table } from "../components/Table";
import type { Asset, Material, NotificationItem, OrderStats, ServiceOrder } from "../types";
import { badgeClass, formatDateTime, numeric, orderStatusLabel, priorityLabel } from "../utils";

interface DashboardPageProps {
  stats: OrderStats | null;
  orders: ServiceOrder[];
  assets: Asset[];
  materials: Material[];
  notifications: NotificationItem[];
}

export function DashboardPage({ stats, orders, assets, materials, notifications }: DashboardPageProps) {
  const open = stats?.by_status.open ?? orders.filter((item) => item.status === "open").length;
  const progress = stats?.by_status.in_progress ?? orders.filter((item) => item.status === "in_progress").length;
  const done = stats?.by_status.completed ?? orders.filter((item) => item.status === "completed").length;
  const lowStock = materials.filter((item) => numeric(item.quantity_in_stock) <= numeric(item.min_quantity)).length;
  const criticalOrders = orders
    .filter((item) => item.priority === "urgent" || item.priority === "high" || item.status === "open")
    .slice(0, 6);
  const inactiveAssets = assets.filter((item) => item.status === "inactive").length;

  return (
    <section className="page-stack">
      <div className="stats-grid">
        <StatCard label="Ordens de Serviço Abertas" value={open} />
        <StatCard label="Em Diagnóstico/Execução" value={progress} tone="amber" />
        <StatCard label="Concluídas" value={done} tone="green" />
        <StatCard label="Alertas de Stock Baixo" value={lowStock} tone="red" />
      </div>

      <div className="dashboard-grid">
        <section>
          <div className="section-heading">
            <div>
              <h2>Próximas Manutenções Críticas</h2>
              <p>Prioridade e estado das ordens mais sensíveis.</p>
            </div>
            <Clock3 size={20} />
          </div>
          <Table columns={["OS", "Cliente", "Equipamento", "Prioridade", "Status"]} empty={!criticalOrders.length}>
            {criticalOrders.map((order) => (
              <tr key={order.id}>
                <td>#{order.order_number}</td>
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
              <h2>Atividade Recente</h2>
              <p>Notificações e sinais do sistema.</p>
            </div>
            <History size={20} />
          </div>
          <div className="activity-list">
            {inactiveAssets ? (
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
            {!notifications.length && !inactiveAssets ? <div className="empty-state">Sem atividade recente.</div> : null}
          </div>
        </section>
      </div>
    </section>
  );
}
