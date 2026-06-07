import { useEffect, useMemo, useState } from "react";
import { LoadingState } from "./components/LoadingState";
import { Layout, type ModuleKey } from "./components/Layout";
import { Toast } from "./components/Toast";
import { api, clearTokens, getAccessToken } from "./services/api";
import { AssetsPage } from "./pages/AssetsPage";
import { AuditPage } from "./pages/AuditPage";
import { DashboardPage } from "./pages/DashboardPage";
import { FinancePage } from "./pages/FinancePage";
import { InventoryPage } from "./pages/InventoryPage";
import { LoginPage } from "./pages/LoginPage";
import { MovementsPage } from "./pages/MovementsPage";
import { OrdersPage } from "./pages/OrdersPage";
import { UsersPage } from "./pages/UsersPage";
import type {
  Asset,
  AuditLogEntry,
  Budget,
  Cost,
  FinancialReport,
  Material,
  Movement,
  NotificationItem,
  OrderStats,
  Role,
  ServiceOrder,
  User
} from "./types";
import { can } from "./utils";

const moduleRoles: Record<ModuleKey, Role[]> = {
  dashboard: ["admin", "supervisor", "technician", "attendant"],
  orders: ["admin", "supervisor", "technician", "attendant"],
  assets: ["admin", "supervisor", "technician", "attendant"],
  inventory: ["admin", "supervisor", "technician", "attendant"],
  movements: ["admin", "supervisor", "technician"],
  finance: ["admin", "supervisor"],
  users: ["admin"],
  audit: ["admin", "supervisor"]
};

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [booting, setBooting] = useState(true);
  const [loadingData, setLoadingData] = useState(false);
  const [activeModule, setActiveModule] = useState<ModuleKey>("dashboard");
  const [toast, setToast] = useState<string | null>(null);

  const [orders, setOrders] = useState<ServiceOrder[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [movements, setMovements] = useState<Movement[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [orderStats, setOrderStats] = useState<OrderStats | null>(null);
  const [financialReport, setFinancialReport] = useState<FinancialReport | null>(null);
  const [costs, setCosts] = useState<Cost[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [auditEntries, setAuditEntries] = useState<AuditLogEntry[]>([]);

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 4000);
  }

  async function safely<T>(loader: () => Promise<T>, fallback: T, onError?: (error: Error) => void): Promise<T> {
    try {
      return await loader();
    } catch (err) {
      if (err instanceof Error) onError?.(err);
      return fallback;
    }
  }

  async function loadOperationalData(currentUser = user) {
    if (!currentUser) return;
    setLoadingData(true);

    const isStaff = can(currentUser.role, ["admin", "supervisor", "technician", "attendant"]);

    const [ordersPage, assetsPage, materialsPage, notificationsPage] = await Promise.all([
      safely(() => api.orders.list({ page_size: 100 }), { items: [], total: 0, page: 1, page_size: 100, pages: 0 }),
      safely(() => api.assets.list({ page_size: 100 }), { items: [], total: 0, page: 1, page_size: 100, pages: 0 }),
      safely(() => api.inventory.materials({ page_size: 100 }), { items: [], total: 0, page: 1, page_size: 100, pages: 0 }),
      safely(() => api.notifications.list({ page_size: 20 }), { items: [], total: 0, page: 1, page_size: 20, pages: 0 })
    ]);

    setOrders(ordersPage.items);
    setAssets(assetsPage.items);
    setMaterials(materialsPage.items);
    setNotifications(notificationsPage.items);

    if (isStaff && can(currentUser.role, ["admin", "supervisor", "technician"])) {
      const movementsPage = await safely(
        () => api.inventory.movements({ page_size: 100 }),
        { items: [], total: 0, page: 1, page_size: 100, pages: 0 }
      );
      setMovements(movementsPage.items);
    }

    if (can(currentUser.role, ["admin", "supervisor"])) {
      const [stats, report, costsPage, budgetsPage] = await Promise.all([
        safely(() => api.orders.stats(), null),
        safely(() => api.finance.report(), null),
        safely(() => api.finance.costs({ page_size: 100 }), { items: [], total: 0, page: 1, page_size: 100, pages: 0 }),
        safely(() => api.finance.budgets({ page_size: 100 }), { items: [], total: 0, page: 1, page_size: 100, pages: 0 })
      ]);

      setOrderStats(stats);
      setFinancialReport(report);
      setCosts(costsPage.items);
      setBudgets(budgetsPage.items);
    } else {
      setOrderStats(null);
      setFinancialReport(null);
      setCosts([]);
      setBudgets([]);
    }

    if (currentUser.role === "admin") {
      const usersPage = await safely(
        () => api.users.list({ page_size: 100 }),
        { items: [], total: 0, page: 1, page_size: 100, pages: 0 }
      );
      setUsers(usersPage.items);
    } else {
      setUsers([currentUser]);
    }

    setLoadingData(false);
  }

  async function handleChanged(message: string, entry?: AuditLogEntry) {
    if (entry) setAuditEntries((current) => [entry, ...current].slice(0, 80));
    await loadOperationalData();
    showToast(message);
  }

  async function handleLogin(login: string, password: string) {
    const response = await api.auth.login(login, password);
    setUser(response.user);
    await loadOperationalData(response.user);
    showToast(`Bem-vindo, ${response.user.name}.`);
  }

  async function handleLogout() {
    try {
      await api.auth.logout();
    } catch {
      clearTokens();
    }
    setUser(null);
    setOrders([]);
    setAssets([]);
    setMaterials([]);
    setMovements([]);
    setUsers([]);
    setNotifications([]);
    setCosts([]);
    setBudgets([]);
    setOrderStats(null);
    setFinancialReport(null);
    setActiveModule("dashboard");
  }

  async function readNotifications() {
    const unread = notifications.filter((item) => !item.read);
    await Promise.all(unread.map((item) => safely(() => api.notifications.markRead(item.id), { id: item.id, read: true })));
    setNotifications((current) => current.map((item) => ({ ...item, read: true })));
    showToast(unread.length ? `${unread.length} notificação(ões) marcada(s) como lida(s).` : "Não há notificações novas.");
  }

  async function markNotificationRead(id: number) {
    setNotifications((current) => current.map((item) => (item.id === id ? { ...item, read: true } : item)));
    await safely(() => api.notifications.markRead(id), { id, read: true });
  }

  useEffect(() => {
    async function boot() {
      const token = getAccessToken();
      if (!token) {
        setBooting(false);
        return;
      }
      try {
        const currentUser = await api.auth.me();
        setUser(currentUser);
        await loadOperationalData(currentUser);
      } catch {
        clearTokens();
      } finally {
        setBooting(false);
      }
    }
    void boot();
  }, []);

  useEffect(() => {
    if (!user) return undefined;
    const url = api.notifications.wsUrl();
    if (!url) return undefined;

    let active = true;
    const ws = new WebSocket(url);
    ws.onmessage = (event) => {
      if (!active) return;
      try {
        const item = JSON.parse(event.data) as NotificationItem;
        setNotifications((current) => [item, ...current].slice(0, 30));
      } catch {
        showToast("Nova notificação recebida.");
      }
    };
    ws.onerror = () => {
      if (active) showToast("Não foi possível conectar ao canal de notificações.");
    };

    return () => {
      active = false;
      ws.close();
    };
  }, [user]);

  useEffect(() => {
    if (user && !can(user.role, moduleRoles[activeModule])) setActiveModule("dashboard");
  }, [activeModule, user]);

  const page = useMemo(() => {
    if (!user) return null;
    if (loadingData && !orders.length && !assets.length && !movements.length) return <LoadingState />;

    switch (activeModule) {
      case "dashboard":
        return (
          <DashboardPage
            user={user}
            stats={orderStats}
            orders={orders}
            assets={assets}
            materials={materials}
            notifications={notifications}
          />
        );
      case "orders":
        return (
          <OrdersPage
            orders={orders}
            assets={assets}
            users={users}
            currentUserId={user.id}
            currentRole={user.role}
            onChanged={handleChanged}
            onToast={showToast}
          />
        );
      case "assets":
        return <AssetsPage assets={assets} currentRole={user.role} onChanged={handleChanged} onToast={showToast} />;
      case "inventory":
        return <InventoryPage materials={materials} currentRole={user.role} onChanged={handleChanged} onToast={showToast} />;
      case "movements":
        return (
          <MovementsPage
            movements={movements}
            materials={materials}
            orders={orders}
            currentRole={user.role}
            onChanged={handleChanged}
            onToast={showToast}
          />
        );
      case "finance":
        return (
          <FinancePage
            report={financialReport}
            costs={costs}
            budgets={budgets}
            orders={orders}
            currentRole={user.role}
            onReload={handleChanged}
            onToast={showToast}
          />
        );
      case "users":
        return <UsersPage users={users} onChanged={handleChanged} onToast={showToast} />;
      case "audit":
        return <AuditPage auditEntries={auditEntries} orders={orders} onToast={showToast} />;
      default:
        return null;
    }
  }, [activeModule, assets, auditEntries, budgets, costs, financialReport, loadingData, materials, movements, notifications, orderStats, orders, user, users]);

  if (booting) return <LoadingState label="Iniciando MANUTECH..." />;
  if (!user) {
    return (
      <>
        <LoginPage onLogin={handleLogin} />
        <Toast message={toast} />
      </>
    );
  }

  return (
    <>
      <Layout
        user={user}
        activeModule={activeModule}
        onModuleChange={setActiveModule}
        notifications={notifications}
        onReadNotifications={readNotifications}
        onMarkNotificationRead={markNotificationRead}
        onLogout={handleLogout}
      >
        {page}
      </Layout>
      <Toast message={toast} />
    </>
  );
}
