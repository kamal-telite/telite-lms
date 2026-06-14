import React from "react";
import { Badge } from "../../components/common/ui";
import { inspectorRegistry } from "./inspectors/inspectorRegistry";

export function BlockInspectorContent({
  activeBlock,
  onBlockSettingChange
}) {
  const blockSettings = activeBlock?.settings || {};
  const InspectorComponent = activeBlock ? inspectorRegistry[activeBlock.block_type] : null;

  if (!activeBlock) {
    return (
      <div className="inspector-empty">
        <div style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.2 }}>⚙️</div>
        Select a lesson block to view and edit its properties.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <section className="inspector-section">
        <div className="inspector-section__title">
          Properties
        </div>
        <div className="inspector-section__body">
          <div className="inspector-row">
            <span className="inspector-row__label">Block ID</span>
            <span className="inspector-row__value">{activeBlock.id || "Unsaved"}</span>
          </div>
          <div className="inspector-row">
            <span className="inspector-row__label">Type</span>
            <span className="inspector-row__value">{activeBlock.block_type}</span>
          </div>
          
          <label style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", fontSize: "13px", color: "#334155", marginTop: "8px" }}>
            <span>Hide in learner preview</span>
            <input
              type="checkbox"
              checked={Boolean(blockSettings.hidden)}
              onChange={(event) => onBlockSettingChange?.("hidden", event.target.checked)}
            />
          </label>
          <label style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", fontSize: "13px", color: "#334155" }}>
            <span>Lock editing</span>
            <input
              type="checkbox"
              checked={Boolean(blockSettings.locked)}
              onChange={(event) => onBlockSettingChange?.("locked", event.target.checked)}
            />
          </label>
          {blockSettings.hidden || blockSettings.locked ? (
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "4px" }}>
              {blockSettings.hidden ? <Badge tone="warning">Hidden</Badge> : null}
              {blockSettings.locked ? <Badge tone="danger">Locked</Badge> : null}
            </div>
          ) : null}
        </div>
      </section>

      {InspectorComponent ? (
        <section className="inspector-section">
          <div className="inspector-section__title">
            Settings
          </div>
          <div className="inspector-section__body">
            <InspectorComponent 
              blockType={activeBlock.block_type}
              settings={blockSettings}
              onChange={onBlockSettingChange}
              disabled={Boolean(blockSettings.locked)}
            />
          </div>
        </section>
      ) : null}
    </div>
  );
}
