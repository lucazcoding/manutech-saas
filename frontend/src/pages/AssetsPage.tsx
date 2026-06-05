import { FormEvent, useMemo, useState } from "react";
import { Edit, Plus, Search } from "lucide-react";
import { Modal } from "../components/Modal";
import { Table } from "../components/Table";
import { api } from "../services/api";
import type { Asset, AuditLogEntry, CreateAssetPayload, EntityStatus, Role } from "../types";
import { badgeClass, can, formatDate, statusLabel } from "../utils";

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

  const filteredAssets = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return assets;
    return assets.filter((asset) =>
      [asset.name, asset.model, asset.manufacturer, asset.serial_number, asset.location].filter(Boolean).join(" ").toLowerCase().includes(term)
    );
  }, [assets, search]);

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
      await onChanged(editing ? "Equipamento atualizado." : "Equipamento registado.", {
        id: `${Date.now()}`,
        action: editing ? "Atualização de equipamento" : "Criação de equipamento",
        module: "Equipamentos",
        target: asset.name,
        delta: payload,
        created_at: new Date().toISOString()
      });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível guardar o equipamento.");
    } finally {
      setSaving(false);
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
            Registar Equipamento
          </button>
        ) : null}
      </div>

      <Table columns={["ID", "Nome", "Modelo", "Localização", "Status", "Atualização", "Ações"]} empty={!filteredAssets.length}>
        {filteredAssets.map((asset) => (
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
              <button className="icon-button" type="button" onClick={() => openEdit(asset)} disabled={!allowedToWrite} aria-label="Editar">
                <Edit size={16} />
              </button>
            </td>
          </tr>
        ))}
      </Table>

      <Modal title={editing ? `Editar ${editing.name}` : "Registar Equipamento"} open={modalOpen} onClose={() => setModalOpen(false)}>
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
              Guardar
            </button>
          </div>
        </form>
      </Modal>
    </section>
  );
}
