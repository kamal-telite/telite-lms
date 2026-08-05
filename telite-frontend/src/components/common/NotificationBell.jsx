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
        aria-label="Notifications"
        title="Notifications"
      >
        <Icon name="bell" size={20} />
        {unreadCount > 0 && (
          <span className="notification-badge">
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
