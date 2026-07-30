import React, { useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { IconButton } from "../../components/common/ui";
import { useBodyScrollLock } from "../../hooks/useBodyScrollLock";
import "./builder.css";

export function BuilderDrawer({ open, onClose, title, subtitle, children }) {
  const handleKeyDown = useCallback((event) => {
    if (event.key === "Escape" && open) {
      onClose();
    }
  }, [open, onClose]);

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  useBodyScrollLock(open);

  return createPortal(
    <>
      <div
        className={`builder-drawer__backdrop ${open ? "builder-drawer__backdrop--visible" : ""}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={`builder-drawer ${open ? "builder-drawer--open" : ""}`}
        role="complementary"
        aria-label={title}
      >
        <div className="builder-drawer__header">
          <div>
            <div className="builder-drawer__header-title">{title}</div>
            {subtitle && <div className="builder-drawer__header-subtitle">{subtitle}</div>}
          </div>
          <IconButton icon="x" label="Close" onClick={onClose} />
        </div>
        <div className="builder-drawer__body">
          {children}
        </div>
      </aside>
    </>,
    document.body
  );
}
