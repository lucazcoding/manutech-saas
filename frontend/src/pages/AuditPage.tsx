import { FormEvent, useEffect, useState } from "react";
import { Search } from "lucide-react";
import { Table } from "../components/Table";
import { api } from "../services/api";
import type { AuditLogEntry, ServiceOrder } from "../types";
import { formatDateTime } from "../utils";

interface AuditPageProps {
  auditEntries: AuditLogEntry[];
  orders: ServiceOrder[];
  onToast: (message: string) => void;
}

export function AuditPage({ auditEntries, orders, onToast }: AuditPageProps) {
  const [selectedOrderId, setSelectedOrderId] = useState<string>(orders[0] ? String(orders[0].id) : "");
  const [history, setHistory] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedOrderId) {
      setHistory([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    api.orders
      .history(Number(selectedOrderId))
      .then((data) => {
        if (!cancelled) setHistory(data);
      })
      .catch((err) => {
        if (!cancelled) onToast(err instanceof Error ? err.message : "Falha ao carregar histórico.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedOrderId, onToast]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
  }

  return (
    <section className="page-stack">
      <div className="section-heading">
        <div>
          <h2>Histórico de alterações do sistema</h2>
          <p>Eventos da sessão atual e auditoria persistida por ordem de serviço.</p>
        </div>
      </div>

      <form className="toolbar" onSubmit={handleSubmit}>
        <label className="search-box grow">
          <Search size={17} />
          <select value={selectedOrderId} onChange={(event) => setSelectedOrderId(event.target.value)}>
            <option value="">Selecione uma OS…</option>
            {orders.map((order) => (
              <option key={order.id} value={order.id}>
                OS-{String(order.order_number).padStart(3, "0")} — {order.client_name}
              </option>
            ))}
          </select>
        </label>
      </form>

      <div>
        <h3 className="subsection-title">Auditoria persistida (por OS)</h3>
        {loading ? (
          <div className="loading-state">Carregando histórico…</div>
        ) : (
          <Table columns={["Data", "Ação", "Módulo", "Alvo", "Detalhes"]} empty={!history.length} emptyLabel="Nenhum evento registrado para esta OS.">
            {history.map((entry) => (
              <tr key={String(entry.id)}>
                <td>{formatDateTime(entry.created_at)}</td>
                <td>{entry.action}</td>
                <td>{entry.module ?? "-"}</td>
                <td>{entry.target ?? "-"}</td>
                <td>
                  <code>{entry.delta ? JSON.stringify(entry.delta).slice(0, 120) : "-"}</code>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </div>

      <div>
        <h3 className="subsection-title">Eventos da sessão atual</h3>
        <Table columns={["Data", "Módulo", "Ação", "Alvo", "Detalhes"]} empty={!auditEntries.length} emptyLabel="Sem eventos nesta sessão.">
          {auditEntries.map((entry) => (
            <tr key={String(entry.id)}>
              <td>{formatDateTime(entry.created_at)}</td>
              <td>{entry.module ?? "-"}</td>
              <td>{entry.action}</td>
              <td>{entry.target ?? "-"}</td>
              <td>
                <code>{entry.delta ? JSON.stringify(entry.delta).slice(0, 120) : "-"}</code>
              </td>
            </tr>
          ))}
        </Table>
      </div>
    </section>
  );
}
