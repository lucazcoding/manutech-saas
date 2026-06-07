import {
  ArrowLeftRight,
  Boxes,
  ClipboardList,
  Coins,
  Fingerprint,
  Gauge,
  LogOut,
  Menu,
  Microchip,
  UsersRound,
  Wrench
} from "lucide-react";
import type { ReactNode } from "react";
import type { NotificationItem, Role, User } from "../types";
import { can, initials, roleLabel } from "../utils";
import { NotificationPanel } from "./NotificationPanel";

export type ModuleKey = "dashboard" | "orders" | "assets" | "inventory" | "movements" | "finance" | "users" | "audit";

interface LayoutProps {
  user: User;
  activeModule: ModuleKey;
  onModuleChange: (module: ModuleKey) => void;
  notifications: NotificationItem[];
  onReadNotifications: () => void;
  onMarkNotificationRead: (id: number) => Promise<void> | void;
  onLogout: () => void;
  children: ReactNode;
}

const navGroups: Array<{
  label: string;
  items: Array<{ key: ModuleKey; label: string; icon: ReactNode; roles: Role[] }>;
}> = [
  {
    label: "Operacional",
    items: [
      { key: "dashboard", label: "Dashboard", icon: <Gauge size={18} />, roles: ["admin", "supervisor", "technician", "attendant"] },
      { key: "orders", label: "Ordens de serviço", icon: <ClipboardList size={18} />, roles: ["admin", "supervisor", "technician", "attendant"] },
      { key: "assets", label: "Equipamentos", icon: <Wrench size={18} />, roles: ["admin", "supervisor", "technician", "attendant"] }
    ]
  },
  {
    label: "Recursos e estoque",
    items: [
      { key: "inventory", label: "Materiais", icon: <Boxes size={18} />, roles: ["admin", "supervisor", "technician", "attendant"] },
      { key: "movements", label: "Movimentações", icon: <ArrowLeftRight size={18} />, roles: ["admin", "supervisor", "technician"] },
      { key: "finance", label: "Custos e finanças", icon: <Coins size={18} />, roles: ["admin", "supervisor"] }
    ]
  },
  {
    label: "Gestão",
    items: [
      { key: "users", label: "Usuários", icon: <UsersRound size={18} />, roles: ["admin"] },
      { key: "audit", label: "Auditoria (logs)", icon: <Fingerprint size={18} />, roles: ["admin", "supervisor"] }
    ]
  }
];

const titles: Record<ModuleKey, string> = {
  dashboard: "Dashboard operacional",
  orders: "Ordens de serviço",
  assets: "Gestão de equipamentos",
  inventory: "Estoque de materiais",
  movements: "Movimentações de estoque",
  finance: "Custos e finanças",
  users: "Usuários",
  audit: "Auditoria"
};

export function Layout({
  user,
  activeModule,
  onModuleChange,
  notifications,
  onReadNotifications,
  onMarkNotificationRead,
  onLogout,
  children
}: LayoutProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="logo">
          <Microchip size={24} />
          <span>MANUTECH</span>
        </div>
        <nav>
          {navGroups.map((group) => {
            const items = group.items.filter((item) => can(user.role, item.roles));
            if (!items.length) return null;
            return (
              <div className="nav-group" key={group.label}>
                <div className="nav-label">{group.label}</div>
                {items.map((item) => (
                  <button
                    className={`nav-item ${activeModule === item.key ? "active" : ""}`}
                    type="button"
                    key={item.key}
                    onClick={() => onModuleChange(item.key)}
                  >
                    {item.icon}
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            );
          })}
        </nav>
        <button className="logout-button" type="button" onClick={onLogout}>
          <LogOut size={18} />
          <span>Sair</span>
        </button>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="mobile-brand">
            <Menu size={20} />
            <span>MANUTECH</span>
          </div>
          <div className="module-title">{titles[activeModule]}</div>
          <div className="user-cluster">
            <NotificationPanel
              notifications={notifications}
              onMarkRead={onMarkNotificationRead}
              onMarkAllRead={onReadNotifications}
            />
            <div className="user-copy">
              <strong>{user.name}</strong>
              <span>{roleLabel[user.role] ?? user.role}</span>
            </div>
            <div className="avatar">{initials(user.name)}</div>
          </div>
        </header>
        <div className="content">{children}</div>
      </main>
    </div>
  );
}
