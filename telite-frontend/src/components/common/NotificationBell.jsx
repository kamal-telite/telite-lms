import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useNotifications } from "../../hooks/useNotifications";
import NotificationDrawer from "./NotificationDrawer";
import { Icon } from "./icons";
import { getNavigableNotificationRoute } from "../../utils/notificationNavigation";

export default function NotificationBell() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const {
    notifications,
    unreadCount,
    isLoading,
    fetchCount,
    fetchList,
    markRead,
    markAllRead
  } = useNotifications();

  // Fetch count on mount
  useEffect(() => {
    fetchCount();
  }, [fetchCount]);

  // When drawer opens, fetch the full list if we haven't already or if we want to refresh
  useEffect(() => {
    if (drawerOpen) {
      fetchList();
    }
  }, [drawerOpen, fetchList]);

  // We explicitly do NOT refresh on every route change per requirements.
  // We only refresh on mount, drawer open, and explicitly after mark read/mark all read
  // (which is handled inside useNotifications).

  const handleNotificationClick = async (notification) => {
    // 1. Mark as read immediately if it's unread
    if (!notification.is_read) {
      await markRead(notification.id);
    }

    // 2. Deep linking safety check
    const route = getNavigableNotificationRoute(notification);
    if (route) {
      setDrawerOpen(false);
      navigate(route);
    }
  };

  const handleToggleDrawer = () => {
    setDrawerOpen((prev) => !prev);
  };

  return (
    <>
      <button
        type="button"
        className="notification-bell-btn"
        onClick={handleToggleDrawer}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: 36,
          height: 36,
          borderRadius: "50%",
          color: "var(--text-secondary)",
          transition: "background-color 0.2s, color 0.2s"
        }}
        aria-label="Notifications"
        title="Notifications"
      >
        <Icon name="bell" size={20} />
        {unreadCount > 0 && (
          <span
            style={{
              position: "absolute",
              top: 2,
              right: 2,
              backgroundColor: "var(--color-danger, #d93025)",
              color: "#fff",
              fontSize: "10px",
              fontWeight: "bold",
              height: 16,
              minWidth: 16,
              padding: "0 4px",
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              lineHeight: 1
            }}
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      <NotificationDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        notifications={notifications}
        isLoading={isLoading}
        onMarkRead={markRead}
        onMarkAllRead={markAllRead}
        onNotificationClick={handleNotificationClick}
      />
    </>
  );
}
