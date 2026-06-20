import React from "react";
import { Badge, Button } from "../../components/common/ui";
import { inspectorRegistry } from "./inspectors/inspectorRegistry";

function DetailRow({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", fontSize: "13px" }}>
      <span style={{ color: "var(--text-secondary)" }}>{label}</span>
      <span style={{ color: "var(--text-primary)", fontWeight: 600, textAlign: "right", overflowWrap: "anywhere" }}>
        {value || "Not set"}
      </span>
    </div>
  );
}

function SectionCard({ title, children }) {
  return (
    <section style={{ border: "1px solid var(--border-subtle)", borderRadius: "8px", background: "var(--surface-raised)", overflow: "hidden" }}>
      <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border-subtle)", fontWeight: 700, fontSize: "13px", color: "var(--text-primary)" }}>
        {title}
      </div>
      <div style={{ padding: "14px", display: "flex", flexDirection: "column", gap: "10px" }}>
        {children}
      </div>
    </section>
  );
}

export function BuilderInspectorPanel({
  course,
  activeSection,
  activeModule,
  activeBlock,
  onBlockSettingChange,
  lockState,
  onOpenHistory,
}) {
  const moduleCount = (activeSection?.modules || []).length;
  const blockSettings = activeBlock?.settings || {};
  
  const InspectorComponent = activeBlock ? inspectorRegistry[activeBlock.block_type] : null;

  return (
    <aside style={{ width: "320px", background: "var(--surface-sunken)", borderLeft: "1px solid var(--border-subtle)", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "16px", borderBottom: "1px solid var(--border-subtle)", background: "var(--surface-raised)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>Inspector</div>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>Course context</div>
        </div>
        <Button tone="neutral" icon="clock" onClick={onOpenHistory}>History</Button>
      </div>

      <div style={{ padding: "16px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "16px" }}>
        <SectionCard title="Course">
          <DetailRow label="Name" value={course?.name} />
          <DetailRow label="Course ID" value={course?.id} />
          <DetailRow label="Status" value={course?.status} />
          <DetailRow label="Category" value={course?.category_slug} />
        </SectionCard>

        <SectionCard title="Selected Module">
          {activeModule ? (
            <>
              <DetailRow label="Title" value={activeModule.title} />
              <DetailRow label="Module ID" value={activeModule.id} />
              <DetailRow label="Type" value={activeModule.module_type} />
              <DetailRow label="Section" value={activeSection?.title} />
            </>
          ) : (
            <div style={{ color: "var(--text-secondary)", fontSize: "13px" }}>Select a module to inspect its properties.</div>
          )}
        </SectionCard>

        <SectionCard title="Selected Block">
          {activeBlock ? (
            <>
              <DetailRow label="Block ID" value={activeBlock.id || "Unsaved"} />
              <DetailRow label="Type" value={activeBlock.block_type} />
              <DetailRow label="Sort Order" value={activeBlock.sort_order} />
              <label style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", fontSize: "13px", color: "var(--text-primary)" }}>
                <span>Hide in learner preview</span>
                <input
                  type="checkbox"
                  checked={Boolean(blockSettings.hidden)}
                  onChange={(event) => onBlockSettingChange?.("hidden", event.target.checked)}
                />
              </label>
              <label style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", fontSize: "13px", color: "var(--text-primary)" }}>
                <span>Lock editing</span>
                <input
                  type="checkbox"
                  checked={Boolean(blockSettings.locked)}
                  onChange={(event) => onBlockSettingChange?.("locked", event.target.checked)}
                />
              </label>
              {blockSettings.hidden || blockSettings.locked ? (
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {blockSettings.hidden ? <Badge tone="warning">Hidden</Badge> : null}
                  {blockSettings.locked ? <Badge tone="danger">Locked</Badge> : null}
                </div>
              ) : null}
            </>
          ) : (
            <div style={{ color: "var(--text-secondary)", fontSize: "13px" }}>Select a lesson block to edit visibility and lock settings.</div>
          )}
        </SectionCard>

        {InspectorComponent ? (
          <SectionCard title="Block Properties">
            <InspectorComponent 
              blockType={activeBlock.block_type}
              settings={blockSettings}
              onChange={onBlockSettingChange}
              disabled={Boolean(blockSettings.locked)}
            />
          </SectionCard>
        ) : null}

        <SectionCard title="Section">
          {activeSection ? (
            <>
              <DetailRow label="Title" value={activeSection.title} />
              <DetailRow label="Section ID" value={activeSection.id === 0 ? "Unassigned" : activeSection.id} />
              <DetailRow label="Modules" value={moduleCount} />
            </>
          ) : (
            <div style={{ color: "var(--text-secondary)", fontSize: "13px" }}>No section selected.</div>
          )}
        </SectionCard>

        <SectionCard title="Lock">
          <DetailRow label="State" value={lockState || "Active editor session"} />
        </SectionCard>
      </div>
    </aside>
  );
}
