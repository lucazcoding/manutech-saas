import { FormEvent, useMemo, useState } from "react";
import { ClipboardList, Edit, Plus, Search } from "lucide-react";
import { Modal } from "../components/Modal";
import { Pagination } from "../components/Pagination";
import { Table } from "../components/Table";
import { api } from "../services/api";
import type { Asset, AuditLogEntry, CreateAssetPayload, EntityStatus, Role, ServiceOrder } from "../types";
import { usePagination } from "../hooks/usePagination";
import { badgeClass, can, formatDate, orderStatusLabel, priorityLabel, statusLabel } from "../utils";

interface AssetsPageProps {
  assets: Asset[];
  currentRole: Role;
  onChanged: (message: string, entry?: AuditLogEntry) => Promise<void>;
  onToast: (message: string) => void;
}

interface AssetForm extends CreateAssetPayload {
  status: EntityStatus;
}

const blankAsset: AssetForm = {
  name: "",
  model: "",
  manufacturer: "",
  serial_number: "",
  location: "",
  status: "active"
};

export function AssetsPage({ assets, currentRole, onChanged, onToast }: AssetsPageProps) {
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Asset | null>(null);
  const [form, setForm] = useState<AssetForm>(blankAsset);
  const [saving, setSaving] = useState(false);
  const allowedToWrite = can(currentRole, ["admin", "supervisor"]);

  const [ordersModal, setOrdersModal] = useState<{ open: boolean; asset: Asset | null; orders: ServiceOrder[]; loading: boolean }>({
    open: false,
    asset: null,
    orders: [],
    loading: false
  });

  const filteredAssets = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return assets;
    return assets.filter((asset) =>
      [asset.name, asset.model, asset.manufacturer, asset.serial_number, asset.location].filter(Boolean).join(" ").toLowerCase().includes(term)
    );
  }, [assets, search]);

  const { page, setPage, pages, pageSize, total, visible: visibleAssets } = usePagination(filteredAssets);

  function openCreate() {
    setEditing(null);
    setForm(blankAsset);
    setModalOpen(true);
  }

  function openEdit(asset: Asset) {
    setEditing(asset);
    setForm({
      name: asset.name,
      model: asset.model ?? "",
      manufacturer: asset.manufacturer ?? "",
      serial_number: asset.serial_number ?? "",
      location: asset.location ?? "",
      status: asset.status
    });
    setModalOpen(true);
  }

  async function saveAsset(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const payload: CreateAssetPayload = {
        name: form.name,
        model: form.model || null,
        manufacturer: form.manufacturer || null,
        serial_number: form.serial_number || null,
        location: form.location || null
      };
      const asset = editing ? await api.assets.update(editing.id, payload) : await api.assets.create(payload);
      if (asset.status !== form.status) await api.assets.setStatus(asset.id, form.status);
      setModalOpen(false);
      await onChanged(editing ? "Equipamento atualizado." : "Equipamento cadastrado.", {
        id: `${Date.now()}`,
        action: editing ? "Atualização de equipamento" : "Cadastro de equipamento",
        module: "Equipamentos",
        target: asset.name,
        delta: payload,
        created_at: new Date().toISOString()
      });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível salvar o equipamento.");
    } finally {
      setSaving(false);
    }
  }

  async function openAssetOrders(asset: Asset) {
    setOrdersModal({ open: true, asset, orders: [], loading: true });
    try {
      const page = await api.assets.orders(asset.id, { page_size: 50 });
      setOrdersModal({ open: true, asset, orders: page.items, loading: false });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível carregar as ordens do equipamento.");
      setOrdersModal((current) => ({ ...current, open: false, loading: false }));
    }
  }

  return (
    <section className="page-stack">
      <div className="toolbar">
        <label className="search-box">
          <Search size={17} />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Pesquisar por nome, série, localização..." />
        </label>
        {allowedToWrite ? (
          <button className="button button-primary" type="button" onClick={openCreate}>
            <Plus size={17} />
            Cadastrar equipamento
          </button>
        ) : null}
      </div>

      <Table columns={["ID", "Nome", "Modelo", "Localização", "Status", "Atualizado em", "Ações"]} empty={!visibleAssets.length}>
        {visibleAssets.map((asset) => (
          <tr key={asset.id}>
            <td>AT-{asset.id}</td>
            <td>
              <strong>{asset.name}</strong>
              <small>{asset.serial_number ?? "Sem número de série"}</small>
            </td>
            <td>{asset.model ?? "-"}</td>
            <td>{asset.location ?? "-"}</td>
            <td>
              <span className={badgeClass(asset.status)}>{statusLabel[asset.status]}</span>
            </td>
            <td>{formatDate(asset.updated_at)}</td>
            <td>
              <div className="table-actions">
                <button className="icon-button" type="button" onClick={() => openAssetOrders(asset)} aria-label="Ver ordens">
                  <ClipboardList size={16} />
                </button>
                <button className="icon-button" type="button" onClick={() => openEdit(asset)} disabled={!allowedToWrite} aria-label="Editar">
                  <Edit size={16} />
                </button>
              </div>
            </td>
          </tr>
        ))}
      </Table>

      <Pagination page={page} pages={pages} total={total} pageSize={pageSize} onPageChange={setPage} />

      <Modal title={editing ? `Editar ${editing.name}` : "Cadastrar equipamento"} open={modalOpen} onClose={() => setModalOpen(false)}>
        <form className="form-grid" onSubmit={saveAsset}>
          <label className="field field-wide">
            <span>Nome do equipamento</span>
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
          </label>
          <label className="field">
            <span>Modelo</span>
            <input value={form.model ?? ""} onChange={(event) => setForm({ ...form, model: event.target.value })} />
          </label>
          <label className="field">
            <span>Fabricante</span>
            <input value={form.manufacturer ?? ""} onChange={(event) => setForm({ ...form, manufacturer: event.target.value })} />
          </label>
          <label className="field">
            <span>Número de série</span>
            <input value={form.serial_number ?? ""} onChange={(event) => setForm({ ...form, serial_number: event.target.value })} />
          </label>
          <label className="field">
            <span>Localização</span>
            <input value={form.location ?? ""} onChange={(event) => setForm({ ...form, location: event.target.value })} />
          </label>
          <label className="field">
            <span>Status</span>
            <select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value as EntityStatus })}>
              <option value="active">Ativo</option>
              <option value="inactive">Inativo</option>
            </select>
          </label>
          <div className="modal-actions field-wide">
            <button className="button button-outline" type="button" onClick={() => setModalOpen(false)}>
              Cancelar
            </button>
            <button className="button button-primary" type="submit" disabled={saving}>
              Salvar
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        title={ordersModal.asset ? `Ordens de ${ordersModal.asset.name}` : "Ordens do equipamento"}
        open={ordersModal.open}
        onClose={() => setOrdersModal({ open: false, asset: null, orders: [], loading: false })}
        width="lg"
      >
        {ordersModal.loading ? (
          <div className="loading-state">Carregando ordens…</div>
        ) : (
          <Table columns={["OS", "Cliente", "Status", "Prioridade", "Técnico"]} empty={!ordersModal.orders.length}>
            {ordersModal.orders.map((order) => (
              <tr key={order.id}>
                <td>OS-{String(order.order_number).padStart(3, "0")}</td>
                <td>{order.client_name}</td>
                <td>
                  <span className={badgeClass(order.status)}>{orderStatusLabel[order.status]}</span>
                </td>
                <td>
                  <span className={badgeClass(order.priority)}>{priorityLabel[order.priority]}</span>
                </td>
                <td>{order.assigned_technician?.name ?? "-"}</td>
              </tr>
            ))}
          </Table>
        )}
      </Modal>
    </section>
  );
}
