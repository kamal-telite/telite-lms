import { createPortal } from "react-dom";
import { useBodyScrollLock } from "../../hooks/useBodyScrollLock";

export default function ConfirmDialog({ open, title, description, confirmLabel, variant = "primary", onConfirm, onCancel }) {
  useBodyScrollLock(open);

  if (!open) return null;

  return createPortal(
    <div className="overlay" style={{zIndex: 250}} onClick={onCancel}>
      <div className="modal modal-sm" onClick={e => e.stopPropagation()} style={{maxWidth: '400px'}}>
        <div className="modal-head">
          <div>
            <div className="modal-title">{title}</div>
            <div className="modal-sub">{description}</div>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onCancel}>Cancel</button>
          <button className={`btn ${variant === 'destructive' ? 'btn-danger' : 'btn-primary'}`} onClick={onConfirm}>
            {confirmLabel || 'Confirm'}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
