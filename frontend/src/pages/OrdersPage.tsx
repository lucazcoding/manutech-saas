import { FormEvent, useMemo, useState } from "react";
import { Edit, FileUp, Plus, RefreshCw, Search } from "lucide-react";
import { Modal } from "../components/Modal";
import { Table } from "../components/Table";
import { api } from "../services/api";
import type { Asset, AuditLogEntry, CreateOrderPayload, OrderPriority, OrderStatus, Role, ServiceOrder, User } from "../types";
import { badgeClass, can, formatDate, orderStatusLabel, priorityLabel, todayISO } from "../utils";

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
  const canCreate = can(currentRole, ["admin", "supervisor", "attendant"]);
  const canEdit = can(currentRole, ["supervisor"]);
  const canChangeStatus = can(currentRole, ["supervisor", "technician"]);

  const filteredOrders = useMemo(() => {
    const term = search.trim().toLowerCase();
    return orders.filter((order) => {
      const matchesStatus = !status || order.status === status;
      const haystack = [
        String(order.order_number),
        `OS-${String(order.order_number).padStart(3, "0")}`,
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

  function orderType(order: ServiceOrder): string {
    if (order.priority === "urgent") return "Corretiva";
    if (order.priority === "high") return "Preditiva";
    return "Preventiva";
  }

  function orderCode(order: ServiceOrder): string {
    return `OS-${String(order.order_number).padStart(3, "0")}`;
  }

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
        order = await api.orders.setStatus(order.id, form.status, "Atualizacao feita pelo frontend MANUTECH");
      }

      if (editing && form.technician_id && Number(form.technician_id) !== order.assigned_technician?.id && canEdit) {
        order = await api.orders.assign(order.id, Number(form.technician_id));
      }

      if (file && editing) {
        await api.orders.uploadAttachment(editing.id, file);
      }

      setModalOpen(false);
      await onChanged(editing ? "Ordem de servico atualizada." : "Ordem de servico criada.", {
        id: `${Date.now()}`,
        action: editing ? "Atualizacao de OS" : "Criacao de OS",
        module: "Ordens",
        target: orderCode(order),
        delta: payload,
        created_at: new Date().toISOString()
      });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Nao foi possivel guardar a OS.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="page-stack">
      <div className="toolbar prototype-toolbar">
        <div className="toolbar-filters">
          <label className="search-box">
            <Search size={17} />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Filtrar OS (ID, Equipamento, Tecnico...)" />
          </label>
          <select className="status-filter" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Status: Todos</option>
            <option value="open">Aberta</option>
            <option value="in_progress">Em andamento</option>
            <option value="completed">Concluida</option>
            <option value="cancelled">Cancelada</option>
          </select>
        </div>
        {canCreate ? (
          <button className="button button-primary" type="button" onClick={openCreate}>
            <Plus size={18} />
            Nova Ordem de Servico
          </button>
        ) : null}
      </div>

      <Table columns={["ID", "Equipamento", "Tipo", "Prioridade", "Responsavel", "Status", "Acoes"]} empty={!filteredOrders.length}>
        {filteredOrders.map((order) => (
          <tr key={order.id}>
            <td>
              <strong>{orderCode(order)}</strong>
            </td>
            <td>{order.asset?.name ?? order.client_name}</td>
            <td>{orderType(order)}</td>
            <td>
              <span className={badgeClass(order.priority)}>{priorityLabel[order.priority]}</span>
            </td>
            <td>{order.assigned_technician?.name ?? "-"}</td>
            <td>
              <span className={badgeClass(order.status)}>{orderStatusLabel[order.status]}</span>
            </td>
            <td>
              <button className="icon-button" type="button" onClick={() => openEdit(order)} aria-label="Editar">
                <Edit size={16} />
              </button>
            </td>
          </tr>
        ))}
      </Table>

      <Modal title={editing ? `Editar ${editing ? orderCode(editing) : ""}` : "Nova Ordem de Servico"} open={modalOpen} onClose={() => setModalOpen(false)} width="lg">
        <form className="form-grid" onSubmit={saveOrder}>
          <label className="field">
            <span>Cliente</span>
            <input value={form.client_name} onChange={(event) => setForm({ ...form, client_name: event.target.value })} required />
          </label>
          <label className="field">
            <span>Localizacao</span>
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
              <option value="medium">Media</option>
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
              <option value="completed">Concluida</option>
              <option value="cancelled">Cancelada</option>
            </select>
          </label>
          <label className="field">
            <span>Tecnico responsavel</span>
            <select
              value={form.technician_id}
              disabled={!editing || !canEdit}
              onChange={(event) => setForm({ ...form, technician_id: event.target.value })}
            >
              <option value="">Nao atribuido</option>
              {technicians.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field field-wide">
            <span>Descricao / diagnostico</span>
            <textarea value={form.description ?? ""} onChange={(event) => setForm({ ...form, description: event.target.value })} rows={4} />
          </label>
          {editing ? (
            <label className="field field-wide file-field">
              <span>Anexo tecnico</span>
              <input type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
              <FileUp size={18} />
            </label>
          ) : null}
          {history.length ? (
            <div className="history-panel field-wide">
              <h3>Historico da OS</h3>
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
