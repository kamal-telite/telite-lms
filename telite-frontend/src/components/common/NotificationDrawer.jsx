import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import PropTypes from "prop-types";
import { IconButton } from "./ui";
import { Icon } from "./icons";
import NotificationCard from "./NotificationCard";

export default function NotificationDrawer({
  open,
  onClose,
  notifications,
  isLoading,
  onMarkRead,
  onMarkAllRead,
  onNotificationClick,
}) {
  const drawerRef = useRef(null);

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === "Escape") onClose();
    };
    if (open) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="notification-drawer-overlay" onClick={onClose}>
      <div 
        ref={drawerRef} 
        className="notification-drawer" 
        onClick={(e) => e.stopPropagation()}
      >
        <div className="notification-drawer-header">
          <div className="notification-drawer-actions">
            <h3 className="notification-drawer-title">
              Notifications
            </h3>
            {notifications.items.some(n => !n.is_read) && (
              <button
                className="notification-mark-all"
                onClick={onMarkAllRead}
              >
                Mark all as read
              </button>
            )}
          </div>
          <IconButton icon="x" label="Close notifications" onClick={onClose} />
        </div>

        <div className="notification-drawer-content">
          {isLoading && notifications.items.length === 0 ? (
            <div className="notification-loading-state">
              <div className="spinner" />
              <p>Loading notifications...</p>
            </div>
          ) : notifications.items.length === 0 ? (
            <div className="notification-empty-state">
              <Icon name="bell" size={48} className="notification-empty-icon" />
              <h4 className="notification-empty-title">
                You're all caught up!
              </h4>
              <p className="notification-empty-desc">
                No new notifications at this time.
              </p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column" }}>
              {notifications.items.map(notification => (
                <NotificationCard
                  key={notification.id}
                  notification={notification}
                  onClick={onNotificationClick}
                  onMarkRead={onMarkRead}
                />
              ))}
              
              {/* Pagination ready footer */}
              {notifications.total > notifications.items.length && (
                <div style={{ padding: "var(--space-16)", textAlign: "center" }}>
                  <button 
                    className="btn btn--outline" 
                    style={{ width: "100%" }}
                  >
                    Load more
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}

NotificationDrawer.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  notifications: PropTypes.shape({
    items: PropTypes.arrayOf(PropTypes.object).isRequired,
    total: PropTypes.number.isRequired,
  }).isRequired,
  isLoading: PropTypes.bool.isRequired,
  onMarkRead: PropTypes.func.isRequired,
  onMarkAllRead: PropTypes.func.isRequired,
  onNotificationClick: PropTypes.func.isRequired,
};
