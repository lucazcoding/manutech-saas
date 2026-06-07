import { FormEvent, useMemo, useState } from "react";
import { Ban, BellRing, Check, Download, Edit, Eye, FileUp, Play, Plus, Search, Trash2 } from "lucide-react";
import { Modal } from "../components/Modal";
import { Pagination } from "../components/Pagination";
import { Table } from "../components/Table";
import { api } from "../services/api";
import type {
  Asset,
  Attachment,
  AuditLogEntry,
  CreateOrderPayload,
  OrderPriority,
  OrderStatus,
  Role,
  ServiceOrder,
  User
} from "../types";
import { usePagination } from "../hooks/usePagination";
import { badgeClass, can, formatDate, formatDateTime, orderStatusLabel, priorityLabel, todayISO } from "../utils";

interface OrdersPageProps {
  orders: ServiceOrder[];
  assets: Asset[];
  users: User[];
  currentUserId: number;
  currentRole: Role;
  onChanged: (message: string, entry?: AuditLogEntry) => Promise<void>;
  onToast: (message: string) => void;
}

interface OrderForm extends CreateOrderPayload {
  status: OrderStatus;
  technician_id: string;
  cancellation_reason: string;
}

const blankOrder: OrderForm = {
  client_name: "",
  location: "",
  description: "",
  priority: "medium",
  start_date: todayISO(),
  asset_id: null,
  status: "open",
  technician_id: "",
  cancellation_reason: ""
};

export function OrdersPage({ orders, assets, users, currentUserId, currentRole, onChanged, onToast }: OrdersPageProps) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [onlyMine, setOnlyMine] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [cancelModal, setCancelModal] = useState<{ open: boolean; order: ServiceOrder | null; reason: string; saving: boolean }>({
    open: false,
    order: null,
    reason: "",
    saving: false
  });
  const [editing, setEditing] = useState<ServiceOrder | null>(null);
  const [form, setForm] = useState<OrderForm>(blankOrder);
  const [history, setHistory] = useState<AuditLogEntry[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);

  const technicians = users.filter((item) => item.role === "technician" && item.status === "active");
  const canCreate = can(currentRole, ["admin", "supervisor", "attendant"]);
  const canEdit = can(currentRole, ["admin", "supervisor"]);
  const canAssign = can(currentRole, ["admin", "supervisor"]);
  const canCancel = can(currentRole, ["admin", "supervisor"]);
  const canChangeStatus = can(currentRole, ["admin", "supervisor", "technician"]);
  const isTechnician = currentRole === "technician";
  const isAttendant = currentRole === "attendant";
  const isReadOnly = isTechnician || isAttendant;
  const forceOnlyMine = isTechnician;

  const filteredOrders = useMemo(() => {
    const term = search.trim().toLowerCase();
    return orders.filter((order) => {
      const matchesStatus = !status || order.status === status;
      const matchesMine = !onlyMine && !forceOnlyMine
        ? true
        : order.assigned_technician?.id === currentUserId;
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
      return matchesStatus && matchesMine && (!term || haystack.includes(term));
    });
  }, [orders, search, status, onlyMine, forceOnlyMine, currentUserId]);

  const { page, setPage, pages, pageSize, total, visible: visibleOrders } = usePagination(filteredOrders);

  function nextStatus(order: ServiceOrder): OrderStatus | null {
    if (order.status === "open") return "in_progress";
    if (order.status === "in_progress" && !isTechnician) return "completed";
    return null;
  }

  function nextStatusLabel(target: OrderStatus | null): string {
    if (target === "in_progress") return "Iniciar";
    if (target === "completed") return "Concluir";
    return "";
  }

  async function advanceStatus(order: ServiceOrder) {
    const target = nextStatus(order);
    if (!target) return;
    if (target === "in_progress" && !order.assigned_technician?.id) {
      onToast("Atribua um técnico antes de iniciar a OS.");
      return;
    }
    try {
      await api.orders.setStatus(order.id, target);
      await onChanged(`OS ${orderCode(order)} → ${orderStatusLabel[target]}.`, {
        id: `${Date.now()}`,
        action: `Status → ${orderStatusLabel[target]}`,
        module: "Ordens",
        target: orderCode(order),
        created_at: new Date().toISOString()
      });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível avançar o status.");
    }
  }

  async function requestCompletion(order: ServiceOrder) {
    if (order.assigned_technician?.id !== currentUserId) {
      onToast("Apenas o técnico atribuído pode solicitar a conclusão.");
      return;
    }
    try {
      await api.orders.requestCompletion(order.id);
      await onChanged(`Solicitação de conclusão enviada para ${orderCode(order)}.`, {
        id: `${Date.now()}`,
        action: "Solicitação de conclusão",
        module: "Ordens",
        target: orderCode(order),
        created_at: new Date().toISOString()
      });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível enviar a solicitação.");
    }
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
      technician_id: order.assigned_technician?.id ? String(order.assigned_technician.id) : "",
      cancellation_reason: ""
    });
    setHistory([]);
    setAttachments([]);
    setFile(null);
    setModalOpen(true);
    try {
      const [historyData, attachmentsData] = await Promise.all([
        api.orders.history(order.id).catch(() => []),
        api.orders.attachments(order.id).catch(() => [])
      ]);
      setHistory(historyData);
      setAttachments(attachmentsData);
    } catch {
      setHistory([]);
      setAttachments([]);
    }
  }

  function openCreate() {
    setEditing(null);
    setForm(blankOrder);
    setHistory([]);
    setAttachments([]);
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
        const reason = form.status === "cancelled" ? form.cancellation_reason.trim() || undefined : undefined;
        order = await api.orders.setStatus(order.id, form.status, reason);
      }

      if (editing && form.technician_id && Number(form.technician_id) !== order.assigned_technician?.id && canAssign) {
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
        target: orderCode(order),
        delta: payload,
        created_at: new Date().toISOString()
      });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível salvar a OS.");
    } finally {
      setSaving(false);
    }
  }

  async function confirmCancel() {
    if (!cancelModal.order) return;
    const reason = cancelModal.reason.trim();
    if (!reason) {
      onToast("Informe o motivo do cancelamento.");
      return;
    }
    setCancelModal((current) => ({ ...current, saving: true }));
    try {
      await api.orders.setStatus(cancelModal.order.id, "cancelled", reason);
      const target = cancelModal.order;
      setCancelModal({ open: false, order: null, reason: "", saving: false });
      await onChanged(`OS ${orderCode(target)} cancelada.`, {
        id: `${Date.now()}`,
        action: "Cancelamento de OS",
        module: "Ordens",
        target: orderCode(target),
        delta: { reason },
        created_at: new Date().toISOString()
      });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível cancelar a OS.");
      setCancelModal((current) => ({ ...current, saving: false }));
    }
  }

  async function deleteOrderSoft(order: ServiceOrder) {
    if (!window.confirm(`Tem certeza que deseja remover a ${orderCode(order)}?`)) return;
    try {
      await api.orders.remove(order.id);
      await onChanged(`OS ${orderCode(order)} removida.`, {
        id: `${Date.now()}`,
        action: "Remoção de OS",
        module: "Ordens",
        target: orderCode(order),
        created_at: new Date().toISOString()
      });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível remover a OS.");
    }
  }

  async function downloadAttachment(attachment: Attachment) {
    if (!editing) return;
    try {
      await api.orders.downloadAttachment(editing.id, attachment.id);
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Falha ao baixar anexo.");
    }
  }

  return (
    <section className="page-stack">
      <div className="toolbar prototype-toolbar">
        <div className="toolbar-filters">
          <label className="search-box">
            <Search size={17} />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Filtrar OS (ID, equipamento, técnico...)" />
          </label>
          <select className="status-filter" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Status: Todos</option>
            <option value="open">Aberta</option>
            <option value="in_progress">Em andamento</option>
            <option value="completed">Concluída</option>
            <option value="cancelled">Cancelada</option>
          </select>
          {isTechnician && !forceOnlyMine ? (
            <button
              className={onlyMine ? "button button-primary" : "button button-outline"}
              type="button"
              onClick={() => setOnlyMine((current) => !current)}
              title="Mostrar apenas ordens atribuídas a mim"
            >
              {onlyMine ? "✓ Apenas minhas OS" : "Apenas minhas OS"}
            </button>
          ) : null}
        </div>
        {canCreate && !isReadOnly ? (
          <button className="button button-primary" type="button" onClick={openCreate}>
            <Plus size={18} />
            Nova ordem de serviço
          </button>
        ) : null}
      </div>

      <Table columns={["ID", "Equipamento", "Prioridade", "Responsável", "Status", "Ações"]} empty={!visibleOrders.length}>
        {visibleOrders.map((order) => {
          const target = nextStatus(order);
          const assignedToMe = order.assigned_technician?.id === currentUserId;
          const canTechnicianRequest = isTechnician
            && order.status === "in_progress"
            && assignedToMe;
          const canTechnicianStart = isTechnician
            && order.status === "open"
            && assignedToMe;
          return (
            <tr key={order.id}>
              <td>
                <strong>{orderCode(order)}</strong>
                {assignedToMe ? <small className="muted">atribuída a você</small> : null}
              </td>
              <td>
                <div>
                  <strong>{order.asset?.name ?? "Sem equipamento"}</strong>
                  <small>{order.client_name}</small>
                </div>
              </td>
              <td>
                <span className={badgeClass(order.priority)}>{priorityLabel[order.priority]}</span>
              </td>
              <td>{order.assigned_technician?.name ?? "-"}</td>
              <td>
                <span className={badgeClass(order.status)}>{orderStatusLabel[order.status]}</span>
              </td>
              <td>
                <div className="table-actions">
                  {isTechnician ? (
                    <>
                      {canTechnicianStart ? (
                        <button
                          className="icon-button success"
                          type="button"
                          onClick={() => advanceStatus(order)}
                          aria-label="Iniciar OS"
                          title="Iniciar OS: mudar status para Em andamento"
                        >
                          <Play size={16} />
                        </button>
                      ) : null}
                      {canTechnicianRequest ? (
                        <button
                          className="icon-button"
                          type="button"
                          onClick={() => requestCompletion(order)}
                          aria-label="Solicitar conclusão"
                          title="Notificar supervisor que a OS está pronta para concluir"
                          style={{ color: "var(--accent)" }}
                        >
                          <BellRing size={16} />
                        </button>
                      ) : null}
                      <button className="icon-button" type="button" onClick={() => openEdit(order)} aria-label="Ver detalhes" title="Ver detalhes">
                        <Eye size={16} />
                      </button>
                    </>
                  ) : (
                    <>
                      {canChangeStatus && target ? (
                        <button
                          className="icon-button success"
                          type="button"
                          onClick={() => advanceStatus(order)}
                          aria-label={nextStatusLabel(target)}
                          title={`${nextStatusLabel(target)}: mudar status para ${orderStatusLabel[target]}`}
                          disabled={target === "in_progress" && !order.assigned_technician?.id}
                        >
                          {target === "in_progress" ? <Play size={16} /> : <Check size={16} />}
                        </button>
                      ) : null}
                      <button className="icon-button" type="button" onClick={() => openEdit(order)} aria-label="Editar">
                        <Edit size={16} />
                      </button>
                      {canCancel && (order.status === "open" || order.status === "in_progress") ? (
                        <button
                          className="icon-button danger"
                          type="button"
                          onClick={() => setCancelModal({ open: true, order, reason: "", saving: false })}
                          aria-label="Cancelar OS"
                          title="Cancelar OS"
                        >
                          <Ban size={16} />
                        </button>
                      ) : null}
                      {canEdit ? (
                        <button className="icon-button danger" type="button" onClick={() => deleteOrderSoft(order)} aria-label="Remover" title="Remover OS">
                          <Trash2 size={16} />
                        </button>
                      ) : null}
                    </>
                  )}
                </div>
              </td>
            </tr>
          );
        })}
      </Table>

      <Pagination page={page} pages={pages} total={total} pageSize={pageSize} onPageChange={setPage} />

      <Modal title={editing ? (isReadOnly ? `Detalhes de ${orderCode(editing)}` : `Editar ${orderCode(editing)}`) : "Nova ordem de serviço"} open={modalOpen} onClose={() => setModalOpen(false)} width="lg">
        <form className="form-grid" onSubmit={saveOrder}>
          <label className="field">
            <span>Cliente</span>
            <input value={form.client_name} onChange={(event) => setForm({ ...form, client_name: event.target.value })} required disabled={isReadOnly} />
          </label>
          <label className="field">
            <span>Localização</span>
            <input value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} required disabled={isReadOnly} />
          </label>
          <label className="field">
            <span>Equipamento</span>
            <select value={form.asset_id ?? ""} onChange={(event) => setForm({ ...form, asset_id: event.target.value ? Number(event.target.value) : null })} disabled={isReadOnly}>
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
            <select value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value as OrderPriority })} disabled={isReadOnly}>
              <option value="low">Baixa</option>
              <option value="medium">Média</option>
              <option value="high">Alta</option>
              <option value="urgent">Urgente</option>
            </select>
          </label>
          <label className="field">
            <span>Data prevista</span>
            <input type="date" value={form.start_date ?? ""} onChange={(event) => setForm({ ...form, start_date: event.target.value })} disabled={isReadOnly} />
          </label>
          <label className="field">
            <span>Status</span>
            <select
              value={form.status}
              disabled={!editing || !canChangeStatus || isReadOnly}
              onChange={(event) => setForm({ ...form, status: event.target.value as OrderStatus })}
            >
              <option value="open">Aberta</option>
              <option value="in_progress">Em andamento</option>
              <option value="completed">Concluída</option>
              <option value="cancelled">Cancelada</option>
            </select>
          </label>
          <label className="field field-wide">
            <span>Técnico responsável</span>
            <select
              value={form.technician_id}
              disabled={!editing || !canAssign || isReadOnly}
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
          {editing && form.status === "cancelled" && canChangeStatus && !isReadOnly ? (
            <label className="field field-wide">
              <span>Motivo do cancelamento (obrigatório)</span>
              <textarea
                value={form.cancellation_reason}
                onChange={(event) => setForm({ ...form, cancellation_reason: event.target.value })}
                rows={2}
                required
              />
            </label>
          ) : null}
          <label className="field field-wide">
            <span>Descrição / diagnóstico</span>
            <textarea value={form.description ?? ""} onChange={(event) => setForm({ ...form, description: event.target.value })} rows={4} disabled={isReadOnly} />
          </label>
          {editing && !isReadOnly ? (
            <label className="field field-wide file-field">
              <span>Anexar arquivo (PDF, JPG, PNG, WEBP — máx. 20 MB)</span>
              <input type="file" accept="application/pdf,image/jpeg,image/png,image/webp" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
              {file ? <small>Selecionado: {file.name}</small> : null}
              <FileUp size={18} />
            </label>
          ) : null}
          {editing && attachments.length ? (
            <div className="history-panel field-wide">
              <h3>Anexos da OS</h3>
              {attachments.map((att) => (
                <p key={att.id} className="attachment-row">
                  <strong>{att.original_name}</strong>
                  <span>{(att.size_bytes / 1024).toFixed(1)} KB</span>
                  <button className="icon-button" type="button" onClick={() => downloadAttachment(att)} aria-label="Baixar anexo">
                    <Download size={15} />
                  </button>
                </p>
              ))}
            </div>
          ) : null}
          {history.length ? (
            <div className="history-panel field-wide">
              <h3>Histórico da OS</h3>
              {history.slice(0, 6).map((item) => (
                <p key={item.id}>
                  <strong>{item.action}</strong> — {formatDateTime(item.created_at)}
                </p>
              ))}
            </div>
          ) : null}
          <div className="modal-actions field-wide">
            <button className="button button-outline" type="button" onClick={() => setModalOpen(false)}>
              {isReadOnly ? "Fechar" : "Cancelar"}
            </button>
            {!isReadOnly ? (
              <button className="button button-primary" type="submit" disabled={saving}>
                {editing ? "Salvar alterações" : "Criar OS"}
              </button>
            ) : null}
          </div>
        </form>
      </Modal>

      <Modal title={cancelModal.order ? `Cancelar ${orderCode(cancelModal.order)}` : "Cancelar OS"} open={cancelModal.open} onClose={() => setCancelModal({ open: false, order: null, reason: "", saving: false })} width="sm">
        <form
          className="form-grid"
          onSubmit={(event) => {
            event.preventDefault();
            void confirmCancel();
          }}
        >
          <label className="field field-wide">
            <span>Motivo do cancelamento (obrigatório)</span>
            <textarea
              value={cancelModal.reason}
              onChange={(event) => setCancelModal((current) => ({ ...current, reason: event.target.value }))}
              rows={4}
              required
              minLength={3}
            />
          </label>
          <div className="modal-actions field-wide">
            <button className="button button-outline" type="button" onClick={() => setCancelModal({ open: false, order: null, reason: "", saving: false })}>
              Voltar
            </button>
            <button className="button button-danger" type="submit" disabled={cancelModal.saving}>
              Confirmar cancelamento
            </button>
          </div>
        </form>
      </Modal>
    </section>
  );
}
