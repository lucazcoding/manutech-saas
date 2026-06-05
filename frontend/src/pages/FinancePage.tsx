import { FormEvent, useState } from "react";
import { Plus, RefreshCw } from "lucide-react";
import { Modal } from "../components/Modal";
import { StatCard } from "../components/StatCard";
import { Table } from "../components/Table";
import { api } from "../services/api";
import type { Budget, Cost, CostType, CreateCostPayload, FinancialReport, ServiceOrder } from "../types";
import { formatCurrency, formatDate } from "../utils";

interface FinancePageProps {
  report: FinancialReport | null;
  costs: Cost[];
  budgets: Budget[];
  orders: ServiceOrder[];
  onReload: (message: string) => Promise<void>;
  onToast: (message: string) => void;
}

const blankCost: CreateCostPayload = {
  service_order_id: 0,
  description: "",
  amount: 0,
  cost_type: "other"
};

export function FinancePage({ report, costs, budgets, orders, onReload, onToast }: FinancePageProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<CreateCostPayload>(blankCost);
  const materialCost = report?.costs_by_type.material ?? 0;
  const laborCost = report?.costs_by_type.labor ?? 0;

  async function createCost(event: FormEvent) {
    event.preventDefault();
    try {
      await api.finance.createCost(form);
      setModalOpen(false);
      setForm(blankCost);
      await onReload("Custo registado.");
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível registar o custo.");
    }
  }

  return (
    <section className="page-stack">
      <div className="toolbar">
        <button className="button button-outline" type="button" onClick={() => onReload("Relatório financeiro atualizado.")}>
          <RefreshCw size={17} />
          Atualizar relatório
        </button>
        <button className="button button-primary" type="button" onClick={() => setModalOpen(true)}>
          <Plus size={17} />
          Registar Custo
        </button>
      </div>

      <div className="stats-grid">
        <StatCard label="Custo Total" value={formatCurrency(report?.total_costs ?? 0)} />
        <StatCard label="Materiais" value={formatCurrency(materialCost)} tone="amber" />
        <StatCard label="Mão de Obra" value={formatCurrency(laborCost)} tone="green" />
        <StatCard label="Custo Médio / OS" value={formatCurrency(report?.avg_cost_per_order ?? 0)} tone="red" />
      </div>

      <div className="two-column">
        <section>
          <div className="section-heading">
            <div>
              <h2>Custos registados</h2>
              <p>{report?.orders_count ?? 0} ordem(ns) consideradas no relatório.</p>
            </div>
          </div>
          <Table columns={["OS", "Descrição", "Tipo", "Valor", "Data"]} empty={!costs.length}>
            {costs.map((cost) => (
              <tr key={cost.id}>
                <td>#{cost.service_order_id}</td>
                <td>{cost.description}</td>
                <td>{cost.cost_type}</td>
                <td>{formatCurrency(cost.amount)}</td>
                <td>{formatDate(cost.created_at)}</td>
              </tr>
            ))}
          </Table>
        </section>
        <section>
          <div className="section-heading">
            <div>
              <h2>Orçamentos</h2>
              <p>Lista vinda do serviço financeiro.</p>
            </div>
          </div>
          <Table columns={["Nº", "Cliente", "Status", "Valor", "Validade"]} empty={!budgets.length}>
            {budgets.map((budget) => (
              <tr key={budget.id}>
                <td>#{budget.budget_number}</td>
                <td>{budget.client_name}</td>
                <td>
                  <span className="badge badge-muted">{budget.status}</span>
                </td>
                <td>{formatCurrency(budget.total_amount)}</td>
                <td>{formatDate(budget.valid_until)}</td>
              </tr>
            ))}
          </Table>
        </section>
      </div>

      <Modal title="Registar custo" open={modalOpen} onClose={() => setModalOpen(false)} width="sm">
        <form className="form-grid" onSubmit={createCost}>
          <label className="field field-wide">
            <span>Ordem de Serviço</span>
            <select value={form.service_order_id || ""} onChange={(event) => setForm({ ...form, service_order_id: Number(event.target.value) })} required>
              <option value="">Selecione uma OS</option>
              {orders.map((order) => (
                <option key={order.id} value={order.id}>
                  #{order.order_number} - {order.client_name}
                </option>
              ))}
            </select>
          </label>
          <label className="field field-wide">
            <span>Descrição</span>
            <input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} required />
          </label>
          <label className="field">
            <span>Tipo</span>
            <select value={form.cost_type} onChange={(event) => setForm({ ...form, cost_type: event.target.value as CostType })}>
              <option value="material">Material</option>
              <option value="labor">Mão de obra</option>
              <option value="service">Serviço</option>
              <option value="other">Outro</option>
            </select>
          </label>
          <label className="field">
            <span>Valor</span>
            <input type="number" step="0.01" value={form.amount} onChange={(event) => setForm({ ...form, amount: Number(event.target.value) })} required />
          </label>
          <div className="modal-actions field-wide">
            <button className="button button-outline" type="button" onClick={() => setModalOpen(false)}>
              Cancelar
            </button>
            <button className="button button-primary" type="submit">
              Guardar
            </button>
          </div>
        </form>
      </Modal>
    </section>
  );
}
