import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Icon } from "./icons";

const ToastContext = createContext({ showToast: () => {} });

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const contextValue = useMemo(
    () => ({
      showToast(message, tone = "info") {
        const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        setToasts((current) => [...current, { id, message, tone }]);
        window.setTimeout(() => {
          setToasts((current) => current.filter((toast) => toast.id !== id));
        }, 3000);
      },
    }),
    []
  );

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <div className="toast-stack">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast--${toast.tone}`}>
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}

export function Button({
  children,
  tone = "ghost",
  icon,
  className = "",
  type = "button",
  ...props
}) {
  return (
    <button className={`btn btn--${tone} ${className}`.trim()} type={type} {...props}>
      {icon ? <Icon name={icon} size={15} /> : null}
      <span>{children}</span>
    </button>
  );
}

export function IconButton({ label, icon, className = "", ...props }) {
  return (
    <button className={`icon-btn ${className}`.trim()} type="button" aria-label={label} {...props}>
      <Icon name={icon} size={15} />
    </button>
  );
}

export function Badge({ children, tone = "neutral", className = "" }) {
  return <span className={`badge badge--${tone} ${className}`.trim()}>{children}</span>;
}

export function Avatar({ initials, gradient = ["#2563EB", "#7C3AED"], size = 30 }) {
  const background = `linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})`;
  return (
    <span
      className="avatar"
      style={{ width: size, height: size, background, fontSize: Math.max(10, size * 0.34) }}
    >
      {initials}
    </span>
  );
}

export function Panel({ title, subtitle, action, children, footer, className = "" }) {
  return (
    <section className={`panel ${className}`.trim()}>
      {(title || action) && (
        <header className="panel__header">
          <div>
            {title ? <h3>{title}</h3> : null}
            {subtitle ? <p>{subtitle}</p> : null}
          </div>
          {action ? <div className="panel__action">{action}</div> : null}
        </header>
      )}
      <div className="panel__body">{children}</div>
      {footer ? <footer className="panel__footer">{footer}</footer> : null}
    </section>
  );
}

export function StatCard({ accent, label, value, meta, pulse = false, suffix }) {
  return (
    <article className={`stat-card ${pulse ? "is-pulse" : ""}`}>
      <span className="stat-card__accent" style={{ background: accent }} />
      <div className="stat-card__label">{label}</div>
      <div className="stat-card__value">
        <span>{value}</span>
        {suffix ? <small>{suffix}</small> : null}
      </div>
      {meta ? <div className="stat-card__meta">{meta}</div> : null}
    </article>
  );
}

export function Modal({ open, title, description, children, footer, onClose, width = 480 }) {
  useEffect(() => {
    if (!open) {
      return undefined;
    }

    function onKeyDown(event) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return createPortal(
    <div className="modal-root" role="presentation" onMouseDown={onClose}>
      <div
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        style={{ maxWidth: width }}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-card__top">
          <div>
            <h2>{title}</h2>
            {description ? <p>{description}</p> : null}
          </div>
          <IconButton label="Close" icon="x" onClick={onClose} />
        </div>
        <div className="modal-card__content">{children}</div>
        {footer ? <div className="modal-card__footer">{footer}</div> : null}
      </div>
    </div>,
    document.body
  );
}

export function EmptyState({ title, body }) {
  return (
    <div className="empty-state">
      <h4>{title}</h4>
      <p>{body}</p>
    </div>
  );
}

export function LoadingState({ title = "Loading dashboard...", body = "Fetching the latest data." }) {
  return (
    <div className="state-card">
      <div className="spinner" />
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}

export function ErrorState({ title = "Unable to load data.", body, action }) {
  return (
    <div className="state-card state-card--error">
      <h3>{title}</h3>
      <p>{body}</p>
      {action}
    </div>
  );
}

export function SkeletonLoader({ rows = 5, showStats = false }) {
  return (
    <div className="skeleton">
      {showStats && (
        <div className="skeleton-stat-row">
          {[1, 2, 3, 4].map((i) => (
            <div className="skeleton-stat-card" key={i}>
              <div className="skeleton-block skeleton-block--sm" style={{ width: "60%" }} />
              <div className="skeleton-block skeleton-block--lg" style={{ width: "40%" }} />
            </div>
          ))}
        </div>
      )}
      <div className="skeleton-table">
        {Array.from({ length: rows + 1 }).map((_, i) => (
          <div className="skeleton-table-row" key={i}>
            <div className="skeleton-block skeleton-block--circle" style={{ width: 28, height: 28 }} />
            <div className="skeleton-block skeleton-block--md" style={{ width: "30%", flex: "none" }} />
            <div className="skeleton-block skeleton-block--sm" style={{ flex: 1 }} />
            <div className="skeleton-block skeleton-block--sm" style={{ width: "15%", flex: "none" }} />
          </div>
        ))}
      </div>
    </div>
  );
}
