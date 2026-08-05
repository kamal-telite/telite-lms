import { Badge } from "./ui";
import { Icon } from "./icons";
import PropTypes from "prop-types";

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
  const { is_read, title, message, created_at, type } = notification;

  return (
    <div
      className={`notification-card ${is_read ? 'is-read' : 'is-unread'}`}
      onClick={() => onClick(notification)}
    >
      <div className="notification-icon-wrapper">
        <Icon name={type === "task_assigned" ? "clipboard" : "bell"} size={16} />
      </div>
      
      <div className="notification-content">
        <div className="notification-header">
          <h4 className="notification-title">
            {title}
          </h4>
          {!is_read && (
            <div className="notification-unread-dot" title="Unread" />
          )}
        </div>
        
        <p className="notification-message">
          {message}
        </p>
        
        <div className="notification-footer">
          <span className="notification-timestamp">
            {formatTimestamp(created_at)}
          </span>
          {!is_read && (
            <button
              className="notification-action-btn"
              onClick={(e) => {
                e.stopPropagation();
                onMarkRead(notification.id);
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

NotificationCard.propTypes = {
  notification: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    is_read: PropTypes.bool,
    title: PropTypes.string.isRequired,
    body: PropTypes.string,
    created_at: PropTypes.string,
    type: PropTypes.string,
  }).isRequired,
  onClick: PropTypes.func.isRequired,
  onMarkRead: PropTypes.func.isRequired,
};
