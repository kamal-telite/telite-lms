import { Badge } from "./ui";
import { Icon } from "./icons";

function formatTimestamp(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
  }).format(date);
}

export default function NotificationCard({ notification, onClick, onMarkRead }) {
  const { is_read, title, body, created_at, type } = notification;

  return (
    <div
      className={`notification-card ${is_read ? 'is-read' : 'is-unread'}`}
      style={{
        padding: "var(--space-16)",
        borderBottom: "1px solid var(--border-color)",
        cursor: "pointer",
        display: "flex",
        gap: "var(--space-12)",
        transition: "background-color 0.2s ease",
        backgroundColor: is_read ? "transparent" : "var(--bg-surface-hover)"
      }}
      onClick={() => onClick(notification)}
    >
      <div style={{ flex: "none", marginTop: "2px" }}>
        {/* Replace with specific icons based on `type` if necessary */}
        <div style={{
          width: 32,
          height: 32,
          borderRadius: "50%",
          backgroundColor: is_read ? "var(--bg-surface-raised)" : "var(--brand-surface)",
          color: is_read ? "var(--text-muted)" : "var(--brand-primary)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center"
        }}>
          <Icon name={type === "task_assigned" ? "clipboard" : "bell"} size={16} />
        </div>
      </div>
      
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "var(--space-8)" }}>
          <h4 style={{ 
            margin: 0, 
            fontSize: "var(--text-body)", 
            fontWeight: is_read ? 400 : 600,
            color: "var(--text-primary)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis"
          }}>
            {title}
          </h4>
          {!is_read && (
            <div 
              style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: "var(--brand-primary)", flex: "none", marginTop: 6 }} 
              title="Unread"
            />
          )}
        </div>
        
        <p style={{ 
          margin: "var(--space-4) 0", 
          fontSize: "var(--text-sm)", 
          color: "var(--text-secondary)",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden"
        }}>
          {body}
        </p>
        
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "var(--space-8)" }}>
          <span style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
            {formatTimestamp(created_at)}
          </span>
          {!is_read && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onMarkRead(notification.id);
              }}
              style={{
                background: "none",
                border: "none",
                padding: 0,
                color: "var(--brand-primary)",
                fontSize: "var(--text-xs)",
                cursor: "pointer",
                fontWeight: 500
              }}
            >
              Mark as read
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
