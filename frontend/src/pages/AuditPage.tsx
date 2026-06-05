import { Table } from "../components/Table";
import type { AuditLogEntry } from "../types";
import { formatDateTime } from "../utils";

export function AuditPage({ auditEntries }: { auditEntries: AuditLogEntry[] }) {
  return (
    <section className="page-stack">
      <div className="section-heading">
        <div>
          <h2>Histórico de Alterações do Sistema</h2>
          <p>Eventos recolhidos durante a sessão atual e histórico de OS quando consultado.</p>
        </div>
      </div>
      <Table columns={["Data", "Módulo", "Ação", "Alvo", "Detalhes"]} empty={!auditEntries.length} emptyLabel="Sem eventos nesta sessão.">
        {auditEntries.map((entry) => (
          <tr key={entry.id}>
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
    </section>
  );
}
