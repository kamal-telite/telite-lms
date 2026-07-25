import { EmptyState } from "../common/ui";

/**
 * NotificationDrawer - Slide-out drawer for displaying learner notifications
 * 
 * @param {boolean} open - Whether drawer is visible
 * @param {function} onClose - Callback when close button clicked
 * @param {array} notifications - Array of notification objects
 */
export function NotificationDrawer({ open, onClose, notifications }) {
  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        bottom: 0,
        width: 320,
        background: "var(--surface)",
        borderLeft: "1px solid var(--border)",
        zIndex: 100,
        boxShadow: "-4px 0 15px rgba(0,0,0,0.05)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          padding: 16,
          borderBottom: "1px solid var(--border)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h3 style={{ margin: 0, fontSize: "16px" }}>Notifications</h3>
        <button
          onClick={onClose}
          style={{
            background: "transparent",
            border: "none",
            fontSize: "18px",
            cursor: "pointer",
            color: "var(--text-muted)",
          }}
        >
          ×
        </button>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
        {notifications?.length === 0 ? (
          <EmptyState
            title="You're all caught up! 🎉"
            body="No new notifications."
          />
        ) : (
          notifications?.map((n) => (
            <div
              key={n.id}
              style={{ padding: 12, borderBottom: "1px solid var(--border)" }}
            >
              <div style={{ fontSize: "13px", fontWeight: "bold" }}>
                {n.title}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: 4 }}>
                {n.message}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
