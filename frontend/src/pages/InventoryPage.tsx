import { FormEvent, useMemo, useState } from "react";
import { Edit, Minus, Plus, Search } from "lucide-react";
import { Modal } from "../components/Modal";
import { Table } from "../components/Table";
import { api } from "../services/api";
import type { AuditLogEntry, CreateMaterialPayload, EntityStatus, Material, Role } from "../types";
import { badgeClass, can, formatCurrency, numeric, statusLabel } from "../utils";

interface InventoryPageProps {
  materials: Material[];
  currentRole: Role;
  onChanged: (message: string, entry?: AuditLogEntry) => Promise<void>;
  onToast: (message: string) => void;
}

interface MaterialForm extends CreateMaterialPayload {
  status: EntityStatus;
}

const blankMaterial: MaterialForm = {
  name: "",
  sku: "",
  unit_price: 0,
  quantity_in_stock: 0,
  min_quantity: 5,
  status: "active"
};

export function InventoryPage({ materials, currentRole, onChanged, onToast }: InventoryPageProps) {
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Material | null>(null);
  const [form, setForm] = useState<MaterialForm>(blankMaterial);
  const allowedToWrite = can(currentRole, ["admin", "supervisor"]);
  const allowedMovement = can(currentRole, ["admin", "supervisor", "technician"]);

  const filteredMaterials = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return materials;
    return materials.filter((material) => [material.name, material.sku].join(" ").toLowerCase().includes(term));
  }, [materials, search]);

  function openCreate() {
    setEditing(null);
    setForm(blankMaterial);
    setModalOpen(true);
  }

  function openEdit(material: Material) {
    setEditing(material);
    setForm({
      name: material.name,
      sku: material.sku,
      unit_price: numeric(material.unit_price),
      quantity_in_stock: numeric(material.quantity_in_stock),
      min_quantity: numeric(material.min_quantity),
      status: material.status
    });
    setModalOpen(true);
  }

  async function saveMaterial(event: FormEvent) {
    event.preventDefault();
    try {
      let material: Material;
      if (editing) {
        material = await api.inventory.updateMaterial(editing.id, {
          name: form.name,
          sku: form.sku,
          unit_price: form.unit_price,
          min_quantity: form.min_quantity
        });
      } else {
        material = await api.inventory.createMaterial(form);
      }
      if (material.status !== form.status) await api.inventory.setMaterialStatus(material.id, form.status);
      setModalOpen(false);
      await onChanged(editing ? "Material atualizado." : "Material registado.", {
        id: `${Date.now()}`,
        action: editing ? "Atualização de material" : "Criação de material",
        module: "Stock",
        target: material.sku,
        created_at: new Date().toISOString()
      });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível guardar o material.");
    }
  }

  async function moveStock(material: Material, movementType: "in" | "out") {
    try {
      await api.inventory.createMovement(material.id, movementType, 1, movementType === "in" ? "Entrada via frontend" : "Saída via frontend");
      await onChanged(movementType === "in" ? "Entrada de stock registada." : "Saída de stock registada.", {
        id: `${Date.now()}`,
        action: movementType === "in" ? "Entrada de stock" : "Saída de stock",
        module: "Stock",
        target: material.sku,
        created_at: new Date().toISOString()
      });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível movimentar o stock.");
    }
  }

  return (
    <section className="page-stack">
      <div className="toolbar">
        <label className="search-box">
          <Search size={17} />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Pesquisar material..." />
        </label>
        {allowedToWrite ? (
          <button className="button button-primary" type="button" onClick={openCreate}>
            <Plus size={17} />
            Novo Material
          </button>
        ) : null}
      </div>

      <Table columns={["Cód.", "Descrição", "Qtd. Atual", "Mínimo", "Preço", "Status", "Ações"]} empty={!filteredMaterials.length}>
        {filteredMaterials.map((material) => {
          const lowStock = numeric(material.quantity_in_stock) <= numeric(material.min_quantity);
          return (
            <tr key={material.id} className={lowStock ? "low-stock-row" : ""}>
              <td>{material.sku}</td>
              <td>
                <strong>{material.name}</strong>
                {lowStock ? <small>Stock abaixo do mínimo</small> : null}
              </td>
              <td>{numeric(material.quantity_in_stock)}</td>
              <td>{numeric(material.min_quantity)}</td>
              <td>{formatCurrency(material.unit_price)}</td>
              <td>
                <span className={badgeClass(material.status)}>{statusLabel[material.status]}</span>
              </td>
              <td>
                <div className="table-actions">
                  {allowedMovement ? (
                    <>
                      <button className="icon-button" type="button" onClick={() => moveStock(material, "in")} aria-label="Adicionar">
                        <Plus size={16} />
                      </button>
                      <button className="icon-button" type="button" onClick={() => moveStock(material, "out")} aria-label="Remover">
                        <Minus size={16} />
                      </button>
                    </>
                  ) : null}
                  <button className="icon-button" type="button" onClick={() => openEdit(material)} disabled={!allowedToWrite} aria-label="Editar">
                    <Edit size={16} />
                  </button>
                </div>
              </td>
            </tr>
          );
        })}
      </Table>

      <Modal title={editing ? `Editar ${editing.sku}` : "Registar Material"} open={modalOpen} onClose={() => setModalOpen(false)}>
        <form className="form-grid" onSubmit={saveMaterial}>
          <label className="field">
            <span>Cód. único</span>
            <input value={form.sku} onChange={(event) => setForm({ ...form, sku: event.target.value })} required />
          </label>
          <label className="field">
            <span>Descrição</span>
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
          </label>
          <label className="field">
            <span>Qtd. atual</span>
            <input
              type="number"
              value={form.quantity_in_stock}
              disabled={Boolean(editing)}
              onChange={(event) => setForm({ ...form, quantity_in_stock: Number(event.target.value) })}
            />
          </label>
          <label className="field">
            <span>Qtd. mínima</span>
            <input type="number" value={form.min_quantity} onChange={(event) => setForm({ ...form, min_quantity: Number(event.target.value) })} />
          </label>
          <label className="field">
            <span>Preço unitário</span>
            <input type="number" step="0.01" value={form.unit_price} onChange={(event) => setForm({ ...form, unit_price: Number(event.target.value) })} />
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
            <button className="button button-primary" type="submit">
              Guardar
            </button>
          </div>
        </form>
      </Modal>
    </section>
  );
}
