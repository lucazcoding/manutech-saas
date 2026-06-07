import { FormEvent, useState } from "react";
import { Edit, Plus } from "lucide-react";
import { Modal } from "../components/Modal";
import { Pagination } from "../components/Pagination";
import { Table } from "../components/Table";
import { api } from "../services/api";
import type { AuditLogEntry, CreateUserPayload, EntityStatus, Role, User } from "../types";
import { usePagination } from "../hooks/usePagination";
import { badgeClass, formatDate, roleLabel, statusLabel } from "../utils";

interface UsersPageProps {
  users: User[];
  onChanged: (message: string, entry?: AuditLogEntry) => Promise<void>;
  onToast: (message: string) => void;
}

interface UserForm extends CreateUserPayload {
  status: EntityStatus;
}

const blankUser: UserForm = {
  name: "",
  login: "",
  email: "",
  password: "",
  role: "technician",
  status: "active"
};

export function UsersPage({ users, onChanged, onToast }: UsersPageProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [form, setForm] = useState<UserForm>(blankUser);

  function openCreate() {
    setEditing(null);
    setForm(blankUser);
    setModalOpen(true);
  }

  function openEdit(user: User) {
    setEditing(user);
    setForm({
      name: user.name,
      login: user.login,
      email: user.email ?? "",
      password: "",
      role: user.role,
      status: user.status
    });
    setModalOpen(true);
  }

  async function saveUser(event: FormEvent) {
    event.preventDefault();
    try {
      const user = editing
        ? await api.users.update(editing.id, { name: form.name, email: form.email, role: form.role })
        : await api.users.create({
            name: form.name,
            login: form.login,
            email: form.email,
            password: form.password,
            role: form.role
          });

      if (user.status !== form.status) await api.users.setStatus(user.id, form.status);
      setModalOpen(false);
      await onChanged(editing ? "Usuário atualizado." : "Usuário cadastrado.", {
        id: `${Date.now()}`,
        action: editing ? "Atualização de usuário" : "Cadastro de usuário",
        module: "Usuários",
        target: user.login,
        created_at: new Date().toISOString()
      });
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Não foi possível salvar o usuário.");
    }
  }

  const { page, setPage, pages, pageSize, total, visible: visibleUsers } = usePagination(users);

  return (
    <section className="page-stack">
      <div className="toolbar">
        <div className="section-heading compact">
          <div>
            <h2>Usuários e permissões</h2>
            <p>Contas administrativas e operacionais do MANUTECH.</p>
          </div>
        </div>
        <button className="button button-primary" type="button" onClick={openCreate}>
          <Plus size={17} />
          Cadastrar usuário
        </button>
      </div>

      <Table columns={["Nome", "Login", "E-mail", "Perfil", "Status", "Criado em", "Ações"]} empty={!visibleUsers.length}>
        {visibleUsers.map((user) => (
          <tr key={user.id}>
            <td>{user.name}</td>
            <td>{user.login}</td>
            <td>{user.email ?? "-"}</td>
            <td>{roleLabel[user.role] ?? user.role}</td>
            <td>
              <span className={badgeClass(user.status)}>{statusLabel[user.status]}</span>
            </td>
            <td>{formatDate(user.created_at)}</td>
            <td>
              <button className="icon-button" type="button" onClick={() => openEdit(user)} aria-label="Editar">
                <Edit size={16} />
              </button>
            </td>
          </tr>
        ))}
      </Table>

      <Pagination page={page} pages={pages} total={total} pageSize={pageSize} onPageChange={setPage} />

      <Modal title={editing ? `Editar ${editing.name}` : "Cadastrar usuário"} open={modalOpen} onClose={() => setModalOpen(false)}>
        <form className="form-grid" onSubmit={saveUser}>
          <label className="field field-wide">
            <span>Nome completo</span>
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
          </label>
          <label className="field">
            <span>Login</span>
            <input value={form.login} onChange={(event) => setForm({ ...form, login: event.target.value })} required disabled={Boolean(editing)} />
          </label>
          <label className="field">
            <span>E-mail</span>
            <input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required />
          </label>
          {!editing ? (
            <label className="field">
              <span>Senha</span>
              <input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} minLength={8} required />
            </label>
          ) : null}
          <label className="field">
            <span>Perfil de acesso</span>
            <select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value as Role })}>
              <option value="admin">Administrador</option>
              <option value="supervisor">Supervisor</option>
              <option value="technician">Técnico</option>
              <option value="attendant">Atendente</option>
            </select>
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
              Salvar
            </button>
          </div>
        </form>
      </Modal>
    </section>
  );
}
