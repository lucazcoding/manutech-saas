import { FormEvent, useMemo, useState } from "react";
import { Edit, FileUp, Plus, RefreshCw, Search, Trash2 } from "lucide-react";
import { Modal } from "../components/Modal";
import { Table } from "../components/Table";
import { api } from "../services/api";
import type { Asset, AuditLogEntry, CreateOrderPayload, OrderPriority, OrderStatus, Role, ServiceOrder, User } from "../types";
import { badgeClass, can, formatCurrency, formatDate, orderStatusLabel, priorityLabel, todayISO } from "../utils";

interface OrdersPageProps {
  orders: ServiceOrder[];
  assets: Asset[];
  users: User[];
  currentRole: Role;
  onChanged: (message: string, entry?: AuditLogEntry) => Promise<void>;
  onToast: (message: string) => void;
}

interface OrderForm extends CreateOrderPayload {
  status: OrderStatus;
  technician_id: string;
}

const blankOrder: OrderForm = {
  client_name: "",
  location: "",
  description: "",
  priority: "medium",
  start_date: todayISO(),
  asset_id: null,
  status: "open",
  technician_id: ""
};

export function OrdersPage({ orders, assets, users, currentRole, onChanged, onToast }: OrdersPageProps) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ServiceOrder | null>(null);
  const [form, setForm] = useState<OrderForm>(blankOrder);
  const [history, setHistory] = useState<AuditLogEntry[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);

  const technicians = users.filter((item) => item.role === "technician" && item.status === "active");
  const canCreate = can(currentRole, ["supervisor", "attendant"]);
  const canEdit = can(currentRole, ["supervisor"]);
  const canChangeStatus = can(currentRole, ["supervisor", "technician"]);
  const canDelete = can(currentRole, ["admin", "supervisor"]);

  const filteredOrders = useMemo(() => {
    const term = search.trim().toLowerCase();
    return orders.filter((order) => {
      const matchesStatus = !status || order.status === status;
      const haystack = [
        String(order.order_number),
        order.client_name,
        order.location,
        order.asset?.name,
        order.assigned_technician?.name,
        order.description
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return matchesStatus && (!term || haystack.includes(term));
    });
  }, [orders, search, status]);

  async function openEdit(order: ServiceOrder) {
    setEditing(order);
    setForm({
      client_name: order.client_name,
      location: order.location,
      description: order.description ?? "",
      priority: order.priority,
      start_date: order.start_date ?? todayISO(),
      asset_id: order.asset?.id ?? null,
      status: order.status,
      technician_id: order.assigned_technician?.id ? String(order.assigned_technician.id) : ""
    });
    setHistory([]);
    setFile(null);
    setModalOpen(true);
    try {
      setHistory(await api.orders.history(order.id));
    } catch {
      setHistory([]);
    }
  }

  function openCreate() {
    setEditing(null);
    setForm(blankOrder);
    setHistory([]);
    setFile(null);
    setModalOpen(true);
  }

  async function saveOrder(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const payload: CreateOrderPayload = {
        client_name: form.client_name,
        location: form.location,
        description: form.description || null,
        priority: form.priority,
        start_date: form.start_date || null,
        asset_id: form.asset_id ? Number(form.asset_id) : null
      };

      let order = editing ? await api.orders.update(editing.id, payload) : await api.orders.create(payload);

      if (editing && order.status !== form.status && canChangeStatus) {
        order = await api.orders.setStatus(order.id, form.status, "Atualização feita pelo frontend MANUTECH");
      }

      if (editing && form.technician_id && Number(form.technician_id) !== order.assigned_technician?.id && canEdit) {
        order = await api.orders.assign(order.id, Number(form.technician_id));
      }

      if (file && editing) {
        await api.orders.uploadAttachment(editing.id, file);
      }

      setModalOpen(false);
      await onChanged(editing ? "Ordem de serviço atualizada." : "Ordem de serviço criada.", {
        id: `${Date.now()}`,
        action: editing ? "Atualização de OS" : "Criação de OS",
        module: "Ordens",
        target: `OS #${order.order_number}`,
        delta: payload,
        created_at: new Date().toISOString()
      });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível guardar a OS.");
    } finally {
      setSaving(false);
    }
  }

  async function removeOrder(order: ServiceOrder) {
    if (!window.confirm(`Remover a OS #${order.order_number}?`)) return;
    try {
      await api.orders.remove(order.id);
      await onChanged("Ordem de serviço removida.", {
        id: `${Date.now()}`,
        action: "Remoção de OS",
        module: "Ordens",
        target: `OS #${order.order_number}`,
        created_at: new Date().toISOString()
      });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível remover a OS.");
    }
  }

  return (
    <section className="page-stack">
      <div className="toolbar">
        <div className="toolbar-filters">
          <label className="search-box">
            <Search size={17} />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Filtrar por OS, cliente, equipamento..." />
          </label>
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Status: todos</option>
            <option value="open">Aberta</option>
            <option value="in_progress">Em andamento</option>
            <option value="completed">Concluída</option>
            <option value="cancelled">Cancelada</option>
          </select>
        </div>
        {canCreate ? (
          <button className="button button-primary" type="button" onClick={openCreate}>
            <Plus size={17} />
            Nova Ordem
          </button>
        ) : null}
      </div>

      <Table columns={["ID", "Cliente", "Equipamento", "Prioridade", "Responsável", "Status", "Custo", "Ações"]} empty={!filteredOrders.length}>
        {filteredOrders.map((order) => (
          <tr key={order.id}>
            <td>#{order.order_number}</td>
            <td>
              <strong>{order.client_name}</strong>
              <small>{order.location}</small>
            </td>
            <td>{order.asset?.name ?? "-"}</td>
            <td>
              <span className={badgeClass(order.priority)}>{priorityLabel[order.priority]}</span>
            </td>
            <td>{order.assigned_technician?.name ?? "-"}</td>
            <td>
              <span className={badgeClass(order.status)}>{orderStatusLabel[order.status]}</span>
            </td>
            <td>{formatCurrency(order.total_cost)}</td>
            <td>
              <div className="table-actions">
                <button className="icon-button" type="button" onClick={() => openEdit(order)} aria-label="Editar">
                  <Edit size={16} />
                </button>
                {canDelete ? (
                  <button className="icon-button danger" type="button" onClick={() => removeOrder(order)} aria-label="Remover">
                    <Trash2 size={16} />
                  </button>
                ) : null}
              </div>
            </td>
          </tr>
        ))}
      </Table>

      <Modal title={editing ? `Editar OS #${editing.order_number}` : "Nova Ordem de Serviço"} open={modalOpen} onClose={() => setModalOpen(false)} width="lg">
        <form className="form-grid" onSubmit={saveOrder}>
          <label className="field">
            <span>Cliente</span>
            <input value={form.client_name} onChange={(event) => setForm({ ...form, client_name: event.target.value })} required />
          </label>
          <label className="field">
            <span>Localização</span>
            <input value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} required />
          </label>
          <label className="field">
            <span>Equipamento</span>
            <select value={form.asset_id ?? ""} onChange={(event) => setForm({ ...form, asset_id: event.target.value ? Number(event.target.value) : null })}>
              <option value="">Sem equipamento associado</option>
              {assets.map((asset) => (
                <option key={asset.id} value={asset.id}>
                  {asset.name} {asset.serial_number ? `- ${asset.serial_number}` : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Prioridade</span>
            <select value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value as OrderPriority })}>
              <option value="low">Baixa</option>
              <option value="medium">Média</option>
              <option value="high">Alta</option>
              <option value="urgent">Urgente</option>
            </select>
          </label>
          <label className="field">
            <span>Data prevista</span>
            <input type="date" value={form.start_date ?? ""} onChange={(event) => setForm({ ...form, start_date: event.target.value })} />
          </label>
          <label className="field">
            <span>Status</span>
            <select
              value={form.status}
              disabled={!editing || !canChangeStatus}
              onChange={(event) => setForm({ ...form, status: event.target.value as OrderStatus })}
            >
              <option value="open">Aberta</option>
              <option value="in_progress">Em andamento</option>
              <option value="completed">Concluída</option>
              <option value="cancelled">Cancelada</option>
            </select>
          </label>
          <label className="field">
            <span>Técnico responsável</span>
            <select
              value={form.technician_id}
              disabled={!editing || !canEdit}
              onChange={(event) => setForm({ ...form, technician_id: event.target.value })}
            >
              <option value="">Não atribuído</option>
              {technicians.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field field-wide">
            <span>Descrição / diagnóstico</span>
            <textarea value={form.description ?? ""} onChange={(event) => setForm({ ...form, description: event.target.value })} rows={4} />
          </label>
          {editing ? (
            <label className="field field-wide file-field">
              <span>Anexo técnico</span>
              <input type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
              <FileUp size={18} />
            </label>
          ) : null}
          {history.length ? (
            <div className="history-panel field-wide">
              <h3>Histórico da OS</h3>
              {history.slice(0, 4).map((item) => (
                <p key={item.id}>
                  <strong>{item.action}</strong> - {formatDate(item.created_at)}
                </p>
              ))}
            </div>
          ) : null}
          <div className="modal-actions field-wide">
            <button className="button button-outline" type="button" onClick={() => setModalOpen(false)}>
              Cancelar
            </button>
            <button className="button button-primary" type="submit" disabled={saving}>
              <RefreshCw className={saving ? "spin" : ""} size={17} />
              Guardar
            </button>
          </div>
        </form>
      </Modal>
    </section>
  );
}
