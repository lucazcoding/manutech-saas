import { FormEvent, useMemo, useState } from "react";
import { Check, Edit, FileDown, FileSpreadsheet, Info, Plus, RefreshCw, Send, X } from "lucide-react";
import { Modal } from "../components/Modal";
import { Pagination } from "../components/Pagination";
import { StatCard } from "../components/StatCard";
import { Table } from "../components/Table";
import { api } from "../services/api";
import type {
  Budget,
  BudgetItem,
  BudgetStatus,
  Cost,
  CostType,
  CreateBudgetPayload,
  CreateCostPayload,
  FinancialReport,
  ServiceOrder
} from "../types";
import { usePagination } from "../hooks/usePagination";
import { badgeClass, can, costTypeLabel, formatCurrency, formatDate, formatDateTime, numeric, roleLabel, budgetStatusLabel } from "../utils";

interface FinancePageProps {
  report: FinancialReport | null;
  costs: Cost[];
  budgets: Budget[];
  orders: ServiceOrder[];
  currentRole: import("../types").Role;
  onReload: (message: string) => Promise<void>;
  onToast: (message: string) => void;
}

const blankCost: CreateCostPayload = {
  service_order_id: 0,
  description: "",
  amount: 0,
  cost_type: "other"
};

interface BudgetForm {
  client_name: string;
  description: string;
  service_order_id: string;
  valid_until: string;
  items: Array<{ description: string; quantity: number; unit_price: number }>;
}

function blankBudget(): BudgetForm {
  return {
    client_name: "",
    description: "",
    service_order_id: "",
    valid_until: "",
    items: [{ description: "", quantity: 1, unit_price: 0 }]
  };
}

const BUDGET_NEXT_STATUS: Record<BudgetStatus, BudgetStatus[]> = {
  draft: ["sent", "expired"],
  sent: ["approved", "rejected"],
  approved: [],
  rejected: [],
  expired: []
};

type FinanceTab = "costs" | "budgets";

export function FinancePage({ report, costs, budgets, orders, currentRole, onReload, onToast }: FinancePageProps) {
  const [activeTab, setActiveTab] = useState<FinanceTab>("costs");
  const [costModal, setCostModal] = useState(false);
  const [costForm, setCostForm] = useState<CreateCostPayload>(blankCost);
  const [budgetModal, setBudgetModal] = useState(false);
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null);
  const [budgetForm, setBudgetForm] = useState<BudgetForm>(blankBudget());
  const [savingBudget, setSavingBudget] = useState(false);

  const canManageFinance = can(currentRole, ["admin", "supervisor"]);
  const canExport = can(currentRole, ["admin", "supervisor"]);
  const canManageBudgets = can(currentRole, ["admin", "supervisor"]);

  const materialCost = report?.costs_by_type.material ?? 0;
  const laborCost = report?.costs_by_type.labor ?? 0;

  const totalBudgetAmount = useMemo(
    () => budgets.reduce((acc, b) => acc + numeric(b.total_amount), 0),
    [budgets]
  );

  const pendingBudgets = useMemo(
    () => budgets.filter((b) => b.status === "sent").length,
    [budgets]
  );

  async function createCost(event: FormEvent) {
    event.preventDefault();
    try {
      await api.finance.createCost(costForm);
      setCostModal(false);
      setCostForm(blankCost);
      await onReload("Custo registrado.");
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível registrar o custo.");
    }
  }

  async function removeCost(cost: Cost) {
    if (!window.confirm("Remover este lançamento de custo?")) return;
    try {
      await api.finance.removeCost(cost.id);
      await onReload("Custo removido.");
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível remover o custo.");
    }
  }

  function openCreateBudget() {
    setEditingBudget(null);
    setBudgetForm(blankBudget());
    setBudgetModal(true);
  }

  function openEditBudget(budget: Budget) {
    setEditingBudget(budget);
    setBudgetForm({
      client_name: budget.client_name,
      description: budget.description ?? "",
      service_order_id: budget.service_order_id ? String(budget.service_order_id) : "",
      valid_until: budget.valid_until ?? "",
      items: budget.items.length
        ? budget.items.map((i: BudgetItem) => ({ description: i.description, quantity: numeric(i.quantity), unit_price: numeric(i.unit_price) }))
        : [{ description: "", quantity: 1, unit_price: 0 }]
    });
    setBudgetModal(true);
  }

  async function saveBudget(event: FormEvent) {
    event.preventDefault();
    if (!budgetForm.client_name.trim()) {
      onToast("Informe o nome do cliente.");
      return;
    }
    const validItems = budgetForm.items.filter((i) => i.description.trim() && i.quantity > 0);
    if (!validItems.length) {
      onToast("Adicione ao menos um item válido ao orçamento.");
      return;
    }
    setSavingBudget(true);
    try {
      const payload: CreateBudgetPayload = {
        client_name: budgetForm.client_name.trim(),
        description: budgetForm.description || null,
        service_order_id: budgetForm.service_order_id ? Number(budgetForm.service_order_id) : null,
        valid_until: budgetForm.valid_until || null,
        items: validItems.map((i) => ({ description: i.description.trim(), quantity: i.quantity, unit_price: i.unit_price }))
      };
      if (editingBudget) {
        await api.finance.updateBudget(editingBudget.id, payload);
      } else {
        await api.finance.createBudget(payload);
      }
      setBudgetModal(false);
      await onReload(editingBudget ? "Orçamento atualizado." : "Orçamento criado.");
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível salvar o orçamento.");
    } finally {
      setSavingBudget(false);
    }
  }

  async function changeBudgetStatus(budget: Budget, status: BudgetStatus) {
    try {
      await api.finance.setBudgetStatus(budget.id, status);
      await onReload(`Orçamento #${budget.budget_number} → ${budgetStatusLabel[status]}.`);
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível alterar o status do orçamento.");
    }
  }

  async function exportReport(format: "excel" | "pdf") {
    try {
      await api.finance.exportReport(format);
      onToast(`Relatório exportado em ${format.toUpperCase()}.`);
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível exportar o relatório.");
    }
  }

  function addBudgetItem() {
    setBudgetForm((current) => ({ ...current, items: [...current.items, { description: "", quantity: 1, unit_price: 0 }] }));
  }

  function removeBudgetItem(index: number) {
    setBudgetForm((current) => ({ ...current, items: current.items.filter((_, i) => i !== index) }));
  }

  function updateBudgetItem(index: number, patch: Partial<BudgetForm["items"][number]>) {
    setBudgetForm((current) => ({
      ...current,
      items: current.items.map((item, i) => (i === index ? { ...item, ...patch } : item))
    }));
  }

  const budgetTotal = budgetForm.items.reduce((acc, i) => acc + i.quantity * i.unit_price, 0);

  const costsPag = usePagination(costs);
  const budgetsPag = usePagination(budgets);

  return (
    <section className="page-stack">
      {/* Toolbar */}
      <div className="toolbar">
        <button className="button button-outline" type="button" onClick={() => onReload("Relatório financeiro atualizado.")}>
          <RefreshCw size={17} />
          Atualizar
        </button>
        {canExport ? (
          <>
            <button className="button button-outline" type="button" onClick={() => exportReport("excel")}>
              <FileSpreadsheet size={17} />
              Excel
            </button>
            <button className="button button-outline" type="button" onClick={() => exportReport("pdf")}>
              <FileDown size={17} />
              PDF
            </button>
          </>
        ) : null}
      </div>

      {/* KPI Cards */}
      <div className="stats-grid">
        <StatCard label="Custo total" value={formatCurrency(report?.total_costs ?? 0)} />
        <StatCard label="Materiais" value={formatCurrency(materialCost)} tone="amber" />
        <StatCard label="Mão de obra" value={formatCurrency(laborCost)} tone="green" />
        <StatCard label="Custo médio / OS" value={formatCurrency(report?.avg_cost_per_order ?? 0)} tone="red" />
      </div>

      {/* Tabs */}
      <div className="finance-tabs">
        <button
          className={`finance-tab ${activeTab === "costs" ? "active" : ""}`}
          type="button"
          onClick={() => setActiveTab("costs")}
        >
          Custos registrados
          <span className="tab-count">{costs.length}</span>
        </button>
        <button
          className={`finance-tab ${activeTab === "budgets" ? "active" : ""}`}
          type="button"
          onClick={() => setActiveTab("budgets")}
        >
          Orçamentos
          <span className="tab-count">{budgets.length}</span>
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "costs" && (
        <div className="finance-tab-content">
          <div className="section-heading">
            <div>
              <h2>Custos registrados</h2>
              <p>{report?.orders_count ?? 0} ordem(ns) considerada(s) no relatório.</p>
            </div>
            {canManageFinance ? (
              <button className="button button-primary" type="button" onClick={() => setCostModal(true)}>
                <Plus size={17} />
                Lançar custo
              </button>
            ) : null}
          </div>

          <Table columns={["OS", "Descrição", "Tipo", "Valor", "Data", "Ações"]} empty={!costsPag.visible.length}>
            {costsPag.visible.map((cost) => (
              <tr key={cost.id}>
                <td>#{cost.service_order_id}</td>
                <td>{cost.description}</td>
                <td>{costTypeLabel[cost.cost_type] ?? cost.cost_type}</td>
                <td>{formatCurrency(cost.amount)}</td>
                <td>{formatDate(cost.created_at)}</td>
                <td>
                  {canManageFinance ? (
                    <button className="icon-button danger" type="button" onClick={() => removeCost(cost)} aria-label="Remover">
                      <X size={16} />
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </Table>
          <Pagination page={costsPag.page} pages={costsPag.pages} total={costsPag.total} pageSize={costsPag.pageSize} onPageChange={costsPag.setPage} />

          {/* Business Rules */}
          <div className="info-panel">
            <Info size={16} />
            <div>
              <strong>Regras de negócio</strong>
              <ul>
                <li>Custos são categorizados em: <strong>Material</strong>, <strong>Mão de obra</strong>, <strong>Serviço</strong> e <strong>Outros</strong>.</li>
                <li>O <strong>total da OS</strong> é recalculado automaticamente a cada lançamento/remoção.</li>
                <li>Apenas <strong>supervisor e admin</strong> podem registrar e remover custos.</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {activeTab === "budgets" && (
        <div className="finance-tab-content">
          <div className="section-heading">
            <div>
              <h2>Orçamentos</h2>
              <p>Total contratado: {formatCurrency(totalBudgetAmount)} · Pendentes: {pendingBudgets}</p>
            </div>
            {canManageBudgets ? (
              <button className="button button-primary" type="button" onClick={openCreateBudget}>
                <Plus size={17} />
                Novo orçamento
              </button>
            ) : null}
          </div>

          <Table columns={["Nº", "Cliente", "Status", "Validade", "Valor", "Ações"]} empty={!budgetsPag.visible.length}>
            {budgetsPag.visible.map((budget) => (
              <tr key={budget.id}>
                <td>#{budget.budget_number}</td>
                <td>{budget.client_name}</td>
                <td>
                  <span className={badgeClass(budget.status)}>{budgetStatusLabel[budget.status] ?? budget.status}</span>
                </td>
                <td>{budget.valid_until ? formatDate(budget.valid_until) : "—"}</td>
                <td>{formatCurrency(budget.total_amount)}</td>
                <td>
                  <div className="table-actions">
                    {canManageBudgets && budget.status === "draft" ? (
                      <button className="icon-button" type="button" onClick={() => openEditBudget(budget)} aria-label="Editar">
                        <Edit size={16} />
                      </button>
                    ) : null}
                    {canManageBudgets
                      ? BUDGET_NEXT_STATUS[budget.status as BudgetStatus]?.map((next) => (
                          <button
                            key={next}
                            className={`icon-button ${next === "approved" ? "success" : next === "rejected" ? "danger" : ""}`}
                            type="button"
                            onClick={() => changeBudgetStatus(budget, next)}
                            aria-label={`Mudar para ${budgetStatusLabel[next]}`}
                            title={budgetStatusLabel[next]}
                          >
                            {next === "sent" ? <Send size={16} /> : next === "approved" ? <Check size={16} /> : next === "rejected" ? <X size={16} /> : <RefreshCw size={16} />}
                          </button>
                        ))
                      : null}
                  </div>
                </td>
              </tr>
            ))}
          </Table>
          <Pagination page={budgetsPag.page} pages={budgetsPag.pages} total={budgetsPag.total} pageSize={budgetsPag.pageSize} onPageChange={budgetsPag.setPage} />

          {/* Business Rules */}
          <div className="info-panel">
            <Info size={16} />
            <div>
              <strong>Regras de negócio</strong>
              <ul>
                <li>Ciclo de vida: <strong>Rascunho → Enviado → Aprovado/Rejeitado</strong>.</li>
                <li>Rascunho pode ser editado; após envio, apenas status pode ser alterado.</li>
                <li>O <strong>total do orçamento</strong> é recalculado automaticamente a partir dos itens.</li>
                <li>Orçamentos podem ser vinculados a uma OS (opcional).</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Lançar custo */}
      <Modal title="Lançar custo" open={costModal} onClose={() => setCostModal(false)} width="sm">
        <form className="form-grid" onSubmit={createCost}>
          <label className="field field-wide">
            <span>Ordem de serviço</span>
            <select value={costForm.service_order_id || ""} onChange={(event) => setCostForm({ ...costForm, service_order_id: Number(event.target.value) })} required>
              <option value="">Selecione uma OS</option>
              {orders.map((order) => (
                <option key={order.id} value={order.id}>
                  OS-{String(order.order_number).padStart(3, "0")} — {order.client_name}
                </option>
              ))}
            </select>
          </label>
          <label className="field field-wide">
            <span>Descrição</span>
            <input value={costForm.description} onChange={(event) => setCostForm({ ...costForm, description: event.target.value })} required />
          </label>
          <label className="field">
            <span>Tipo</span>
            <select value={costForm.cost_type} onChange={(event) => setCostForm({ ...costForm, cost_type: event.target.value as CostType })}>
              <option value="material">Material</option>
              <option value="labor">Mão de obra</option>
              <option value="service">Serviço</option>
              <option value="other">Outro</option>
            </select>
          </label>
          <label className="field">
            <span>Valor (R$)</span>
            <input type="number" step="0.01" min={0} value={costForm.amount} onChange={(event) => setCostForm({ ...costForm, amount: Number(event.target.value) })} required />
          </label>
          <div className="modal-actions field-wide">
            <button className="button button-outline" type="button" onClick={() => setCostModal(false)}>
              Cancelar
            </button>
            <button className="button button-primary" type="submit">
              Salvar
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Orçamento */}
      <Modal title={editingBudget ? `Editar orçamento #${editingBudget.budget_number}` : "Novo orçamento"} open={budgetModal} onClose={() => setBudgetModal(false)} width="lg">
        <form className="form-grid" onSubmit={saveBudget}>
          <label className="field">
            <span>Cliente</span>
            <input value={budgetForm.client_name} onChange={(event) => setBudgetForm({ ...budgetForm, client_name: event.target.value })} required />
          </label>
          <label className="field">
            <span>Validade</span>
            <input type="date" value={budgetForm.valid_until} onChange={(event) => setBudgetForm({ ...budgetForm, valid_until: event.target.value })} />
          </label>
          <label className="field field-wide">
            <span>Ordem de serviço vinculada (opcional)</span>
            <select value={budgetForm.service_order_id} onChange={(event) => setBudgetForm({ ...budgetForm, service_order_id: event.target.value })}>
              <option value="">Sem OS vinculada</option>
              {orders.map((order) => (
                <option key={order.id} value={order.id}>
                  OS-{String(order.order_number).padStart(3, "0")} — {order.client_name}
                </option>
              ))}
            </select>
          </label>
          <label className="field field-wide">
            <span>Descrição</span>
            <textarea rows={2} value={budgetForm.description} onChange={(event) => setBudgetForm({ ...budgetForm, description: event.target.value })} />
          </label>
          <div className="field field-wide">
            <div className="section-heading compact">
              <div>
                <h3>Itens do orçamento</h3>
                <p>Total atual: {formatCurrency(budgetTotal)}</p>
              </div>
              <button className="button button-outline" type="button" onClick={addBudgetItem}>
                <Plus size={15} /> Adicionar item
              </button>
            </div>
            {budgetForm.items.map((item, index) => (
              <div className="budget-item-row" key={index}>
                <input
                  className="grow"
                  placeholder="Descrição do item"
                  value={item.description}
                  onChange={(event) => updateBudgetItem(index, { description: event.target.value })}
                />
                <input
                  type="number"
                  min={1}
                  step="1"
                  value={item.quantity}
                  onChange={(event) => updateBudgetItem(index, { quantity: Number(event.target.value) })}
                  title="Quantidade"
                />
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={item.unit_price}
                  onChange={(event) => updateBudgetItem(index, { unit_price: Number(event.target.value) })}
                  title="Preço unitário (R$)"
                />
                <span className="budget-item-total">{formatCurrency(item.quantity * item.unit_price)}</span>
                <button
                  className="icon-button danger"
                  type="button"
                  onClick={() => removeBudgetItem(index)}
                  disabled={budgetForm.items.length === 1}
                  aria-label="Remover item"
                >
                  <X size={15} />
                </button>
              </div>
            ))}
          </div>
          <div className="modal-actions field-wide">
            <button className="button button-outline" type="button" onClick={() => setBudgetModal(false)}>
              Cancelar
            </button>
            <button className="button button-primary" type="submit" disabled={savingBudget}>
              {editingBudget ? "Salvar alterações" : "Criar orçamento"}
            </button>
          </div>
        </form>
      </Modal>
    </section>
  );
}
