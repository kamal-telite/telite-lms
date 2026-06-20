import React from "react";
import { createPortal } from "react-dom";
import { Button } from "../../components/common/ui";
import "./builder.css";

function getFixLabel(type, fixTarget) {
  switch (type) {
    case "empty_module": return "Go to Module";
    case "missing_title": return "Edit Title";
    case "missing_media": return "Add Media";
    case "missing_alt_text": return "Add Alt Text";
    case "missing_content": return "Edit Content";
    case "missing_url": return "Add URL";
    case "missing_quiz": return "Select Quiz";
    case "missing_instructions": return "Edit Instructions";
    default: return fixTarget?.module_title ? `Go to ${fixTarget.module_title}` : "Go to Module";
  }
}

function getFixIcon(type) {
  switch (type) {
    case "empty_module": return "arrow-right";
    case "missing_title": return "pencil";
    case "missing_media": return "image";
    default: return "arrow-right";
  }
}

export function ReadinessDrawer({ open, onClose, validationResults, onFixValidation }) {
  const errors = validationResults.filter(r => r.severity === "error");
  const warnings = validationResults.filter(r => r.severity === "warning");
  const infos = validationResults.filter(r => r.severity === "info");

  const ValidationCard = ({ result, icon }) => (
    <div className="validation-card">
      <div className="validation-card__content">
        <div className="validation-card__icon">{icon}</div>
        <div>
          <div className="validation-card__message">{result.message}</div>
          {result.fix_target?.module_title && (
            <div className="validation-card__location">
              Module: {result.fix_target.module_title}
            </div>
          )}
          {!result.fix_target?.module_title && result.fix_target?.section_title && (
            <div className="validation-card__location">
              Location: {result.fix_target.section_title}
            </div>
          )}
        </div>
      </div>
      {result.fix_target?.module_id && onFixValidation && (
        <Button tone="neutral" size="small" icon={getFixIcon(result.type)} onClick={() => { onClose(); onFixValidation(result.fix_target.module_id, result.fix_target.block_id); }}>
          {getFixLabel(result.type, result.fix_target)}
        </Button>
      )}
    </div>
  );

  if (!open) return null;

  return createPortal(
    <>
      <div
        className={`builder-drawer__backdrop ${open ? "builder-drawer__backdrop--visible" : ""}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <div className={`readiness-drawer ${open ? "readiness-drawer--open" : ""}`}>
        <div className="readiness-drawer__header">
          <div className="readiness-drawer__header-title">Publish Readiness</div>
          <Button tone="neutral" size="small" onClick={onClose}>Close</Button>
        </div>
        <div className="readiness-drawer__body">
          <div style={{ display: "grid", gap: "12px" }}>
            {errors.map((error, idx) => (
              <ValidationCard key={`err-${idx}`} result={error} icon="❌" />
            ))}
            {warnings.map((warning, idx) => (
              <ValidationCard key={`warn-${idx}`} result={warning} icon="⚠" />
            ))}
            {infos.map((info, idx) => (
              <ValidationCard key={`info-${idx}`} result={info} icon="ℹ️" />
            ))}
            {validationResults.length === 0 && (
              <div style={{ padding: "40px", textAlign: "center", color: "var(--text-secondary)" }}>
                No readiness issues found. Course is ready to publish.
              </div>
            )}
          </div>
        </div>
      </div>
    </>,
    document.body
  );
}
