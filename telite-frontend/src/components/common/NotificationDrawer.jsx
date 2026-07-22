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
    <div className="notification-drawer-overlay" style={overlayStyle} onClick={onClose}>
      <div 
        ref={drawerRef} 
        className="notification-drawer" 
        style={drawerStyle} 
        onClick={(e) => e.stopPropagation()}
      >
        <div style={headerStyle}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-8)" }}>
            <h3 style={{ margin: 0, fontSize: "var(--text-lg)", color: "var(--text-primary)" }}>
              Notifications
            </h3>
            {notifications.items.some(n => !n.is_read) && (
              <button
                onClick={onMarkAllRead}
                style={{
                  background: "none",
                  border: "none",
                  padding: "var(--space-4) var(--space-8)",
                  color: "var(--brand-primary)",
                  fontSize: "var(--text-xs)",
                  cursor: "pointer",
                  fontWeight: 500,
                  marginLeft: "auto"
                }}
              >
                Mark all as read
              </button>
            )}
          </div>
          <IconButton icon="x" label="Close notifications" onClick={onClose} />
        </div>

        <div style={contentStyle}>
          {isLoading && notifications.items.length === 0 ? (
            <div style={loadingStyle}>
              <div className="spinner" />
              <p>Loading notifications...</p>
            </div>
          ) : notifications.items.length === 0 ? (
            <div style={emptyStyle}>
              <Icon name="bell" size={48} style={{ color: "var(--text-muted)", opacity: 0.5 }} />
              <h4 style={{ margin: "var(--space-16) 0 var(--space-8)", color: "var(--text-primary)" }}>
                You&apos;re all caught up!
              </h4>
              <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: "var(--text-sm)" }}>
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

const overlayStyle = {
  position: "fixed",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: "rgba(0, 0, 0, 0.4)",
  zIndex: 9999,
  display: "flex",
  justifyContent: "flex-end"
};

const drawerStyle = {
  width: "100%",
  maxWidth: "400px",
  height: "100%",
  backgroundColor: "var(--bg-surface)",
  boxShadow: "-4px 0 24px rgba(0, 0, 0, 0.1)",
  display: "flex",
  flexDirection: "column",
  animation: "slideInRight 0.3s ease forwards"
};

const headerStyle = {
  padding: "var(--space-16) var(--space-24)",
  borderBottom: "1px solid var(--border-color)",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  flex: "none"
};

const contentStyle = {
  flex: 1,
  overflowY: "auto"
};

const emptyStyle = {
  padding: "var(--space-48) var(--space-24)",
  textAlign: "center",
  display: "flex",
  flexDirection: "column",
  alignItems: "center"
};

const loadingStyle = {
  padding: "var(--space-48)",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: "var(--space-16)",
  color: "var(--text-secondary)"
};

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
