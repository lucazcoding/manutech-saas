import { useEffect, useRef, useState } from "react";
import { Bell, BellOff, Check, X } from "lucide-react";
import type { NotificationItem } from "../types";
import { formatDateTime } from "../utils";

interface NotificationPanelProps {
  notifications: NotificationItem[];
  onMarkRead: (id: number) => Promise<void> | void;
  onMarkAllRead: () => Promise<void> | void;
}

export function NotificationPanel({ notifications, onMarkRead, onMarkAllRead }: NotificationPanelProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const unread = notifications.filter((item) => !item.read).length;

  useEffect(() => {
    if (!open) return undefined;
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function handleEsc(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEsc);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEsc);
    };
  }, [open]);

  async function handleItemClick(item: NotificationItem) {
    if (item.read) return;
    await onMarkRead(item.id);
  }

  return (
    <div className="notif-wrapper" ref={containerRef}>
      <button
        className="bell-button"
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-label="Notificações"
        title="Ver notificações"
      >
        {unread > 0 ? <Bell size={19} /> : <BellOff size={19} />}
        {unread > 0 ? <span>{unread}</span> : null}
      </button>
      {open ? (
        <div className="notif-panel" role="dialog" aria-label="Notificações">
          <div className="notif-panel-header">
            <strong>Notificações</strong>
            <div className="notif-panel-actions">
              <button
                className="icon-button"
                type="button"
                onClick={() => void onMarkAllRead()}
                disabled={unread === 0}
                aria-label="Marcar todas como lidas"
                title="Marcar todas como lidas"
              >
                <Check size={15} />
              </button>
              <button
                className="icon-button"
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Fechar"
                title="Fechar"
              >
                <X size={15} />
              </button>
            </div>
          </div>
          <div className="notif-panel-list">
            {notifications.length === 0 ? (
              <div className="empty-state">Sem notificações por enquanto.</div>
            ) : (
              notifications.slice(0, 15).map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`notif-item ${item.read ? "read" : "unread"}`}
                  onClick={() => void handleItemClick(item)}
                  title={item.read ? "Notificação lida" : "Clique para marcar como lida"}
                >
                  <span className={item.read ? "dot dot-muted" : "dot"} />
                  <div className="notif-item-body">
                    <strong>{item.title}</strong>
                    <p>{item.message}</p>
                    <small>{formatDateTime(item.created_at)}</small>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
