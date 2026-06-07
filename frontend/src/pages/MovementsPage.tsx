import { FormEvent, useMemo, useState } from "react";
import { ArrowDownCircle, ArrowUpCircle, Plus, Search } from "lucide-react";
import { Modal } from "../components/Modal";
import { Pagination } from "../components/Pagination";
import { Table } from "../components/Table";
import { api } from "../services/api";
import type { AuditLogEntry, Material, Movement, MovementType, Role, ServiceOrder } from "../types";
import { usePagination } from "../hooks/usePagination";
import { can, formatDateTime, numeric } from "../utils";

interface MovementsPageProps {
  movements: Movement[];
  materials: Material[];
  orders: ServiceOrder[];
  currentRole: Role;
  onChanged: (message: string, entry?: AuditLogEntry) => Promise<void>;
  onToast: (message: string) => void;
}

interface MovementForm {
  material_id: string;
  service_order_id: string;
  movement_type: MovementType;
  quantity: number;
  notes: string;
}

const blankMovement: MovementForm = {
  material_id: "",
  service_order_id: "",
  movement_type: "in",
  quantity: 1,
  notes: ""
};

export function MovementsPage({ movements, materials, orders, currentRole, onChanged, onToast }: MovementsPageProps) {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<"" | MovementType>("");
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<MovementForm>(blankMovement);
  const [saving, setSaving] = useState(false);

  const canCreate = can(currentRole, ["admin", "supervisor", "technician"]);
  const activeMaterials = useMemo(() => materials.filter((m) => m.status === "active"), [materials]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return movements.filter((movement) => {
      if (typeFilter && movement.movement_type !== typeFilter) return false;
      if (!term) return true;
      const material = materials.find((m) => m.id === movement.material_id);
      const haystack = [material?.name, material?.sku, movement.notes].filter(Boolean).join(" ").toLowerCase();
      return haystack.includes(term);
    });
  }, [movements, search, typeFilter, materials]);

  const { page, setPage, pages, pageSize, total, visible: visibleMovements } = usePagination(filtered);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!form.material_id) {
      onToast("Selecione um material.");
      return;
    }
    if (form.quantity <= 0) {
      onToast("A quantidade deve ser maior que zero.");
      return;
    }
    setSaving(true);
    try {
      const created = await api.inventory.createMovement({
        material_id: Number(form.material_id),
        service_order_id: form.service_order_id ? Number(form.service_order_id) : null,
        movement_type: form.movement_type,
        quantity: form.quantity,
        notes: form.notes || null
      });
      const material = materials.find((m) => m.id === created.material_id);
      setModalOpen(false);
      setForm(blankMovement);
      await onChanged("Movimentação registrada.", {
        id: `${Date.now()}`,
        action: form.movement_type === "in" ? "Entrada de estoque" : "Saída de estoque",
        module: "Movimentações",
        target: material?.sku ?? `#${created.material_id}`,
        created_at: new Date().toISOString()
      });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível registrar a movimentação.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="page-stack">
      <div className="toolbar">
        <div className="toolbar-filters">
          <label className="search-box">
            <Search size={17} />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Filtrar por material, SKU ou observação..." />
          </label>
          <select className="status-filter" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value as "" | MovementType)}>
            <option value="">Tipo: Todos</option>
            <option value="in">Entrada</option>
            <option value="out">Saída</option>
          </select>
        </div>
        {canCreate ? (
          <button className="button button-primary" type="button" onClick={() => setModalOpen(true)}>
            <Plus size={17} />
            Nova movimentação
          </button>
        ) : null}
      </div>

      <Table columns={["Data", "Material", "Tipo", "Quantidade", "OS vinculada", "Observação"]} empty={!visibleMovements.length}>
        {visibleMovements.map((movement) => {
          const material = materials.find((m) => m.id === movement.material_id);
          const order = orders.find((o) => o.id === movement.service_order_id);
          return (
            <tr key={movement.id}>
              <td>{formatDateTime(movement.created_at)}</td>
              <td>
                <strong>{material?.name ?? `#${movement.material_id}`}</strong>
                <small>{material?.sku}</small>
              </td>
              <td>
                {movement.movement_type === "in" ? (
                  <span className="badge badge-success">
                    <ArrowUpCircle size={13} /> Entrada
                  </span>
                ) : (
                  <span className="badge badge-warning">
                    <ArrowDownCircle size={13} /> Saída
                  </span>
                )}
              </td>
              <td>{numeric(movement.quantity)}</td>
              <td>{order ? `OS-${String(order.order_number).padStart(3, "0")}` : "-"}</td>
              <td>{movement.notes ?? "-"}</td>
            </tr>
          );
        })}
      </Table>

      <Pagination page={page} pages={pages} total={total} pageSize={pageSize} onPageChange={setPage} />

      <Modal title="Registrar movimentação" open={modalOpen} onClose={() => setModalOpen(false)}>
        <form className="form-grid" onSubmit={save}>
          <label className="field field-wide">
            <span>Material</span>
            <select value={form.material_id} onChange={(event) => setForm({ ...form, material_id: event.target.value })} required>
              <option value="">Selecione um material</option>
              {activeMaterials.map((material) => (
                <option key={material.id} value={material.id}>
                  {material.sku} — {material.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Tipo</span>
            <select value={form.movement_type} onChange={(event) => setForm({ ...form, movement_type: event.target.value as MovementType })}>
              <option value="in">Entrada</option>
              <option value="out">Saída</option>
            </select>
          </label>
          <label className="field">
            <span>Quantidade</span>
            <input
              type="number"
              min={1}
              step="1"
              value={form.quantity}
              onChange={(event) => setForm({ ...form, quantity: Number(event.target.value) })}
              required
            />
          </label>
          <label className="field field-wide">
            <span>OS vinculada (opcional)</span>
            <select value={form.service_order_id} onChange={(event) => setForm({ ...form, service_order_id: event.target.value })}>
              <option value="">Sem OS vinculada</option>
              {orders.map((order) => (
                <option key={order.id} value={order.id}>
                  OS-{String(order.order_number).padStart(3, "0")} — {order.client_name}
                </option>
              ))}
            </select>
          </label>
          <label className="field field-wide">
            <span>Observação</span>
            <textarea rows={3} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
          </label>
          <div className="modal-actions field-wide">
            <button className="button button-outline" type="button" onClick={() => setModalOpen(false)}>
              Cancelar
            </button>
            <button className="button button-primary" type="submit" disabled={saving}>
              Registrar
            </button>
          </div>
        </form>
      </Modal>
    </section>
  );
}
