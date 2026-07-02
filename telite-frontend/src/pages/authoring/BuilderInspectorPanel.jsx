import React, { useState, useEffect } from "react";
import { Badge, Button, IconButton } from "../../components/common/ui";
import { inspectorRegistry } from "./inspectors/inspectorRegistry";
import { api, getErrorMessage } from "../../services/client";
import { useToast } from "../../components/common/ui";

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
  const { showToast } = useToast();
  const moduleCount = (activeSection?.modules || []).length;
  const blockSettings = activeBlock?.settings || {};
  
  const InspectorComponent = activeBlock ? inspectorRegistry[activeBlock.block_type] : null;
  
  // Progression Rules state
  const [progressionRules, setProgressionRules] = useState([]);
  const [showAddRule, setShowAddRule] = useState(false);
  const [newRuleType, setNewRuleType] = useState("previous_module_completed");
  const [loadingRules, setLoadingRules] = useState(false);

  // Fetch progression rules for the current module or section
  useEffect(() => {
    const fetchRules = async () => {
      if (!course?.id) return;
      setLoadingRules(true);
      try {
        const { data } = await api.get(`/authoring/courses/${course.id}/progression-rules`);
        setProgressionRules(data.rules || []);
      } catch (err) {
        console.error("Failed to fetch progression rules:", err);
      } finally {
        setLoadingRules(false);
      }
    };
    fetchRules();
  }, [course?.id]);

  // Get rules for current target (module or section)
  const currentTargetRules = React.useMemo(() => {
    if (activeModule) {
      return progressionRules.filter(r => r.target_type === "module" && r.target_id === activeModule.id);
    }
    if (activeSection && activeSection.id !== 0) {
      return progressionRules.filter(r => r.target_type === "section" && r.target_id === activeSection.id);
    }
    return [];
  }, [progressionRules, activeModule, activeSection]);

  const handleCreateRule = async () => {
    if (!course?.id || (!activeModule && !activeSection)) return;
    
    const target = activeModule ? { type: "module", id: activeModule.id } : { type: "section", id: activeSection.id };
    if (target.id === 0) {
      showToast("Cannot add rules to unassigned modules.", "warning");
      return;
    }

    try {
      const { data } = await api.post(`/authoring/courses/${course.id}/progression-rules`, {
        target_type: target.type,
        target_id: target.id,
        rule_type: newRuleType,
        rule_value: {},
      });
      setProgressionRules([...progressionRules, data.rule]);
      setShowAddRule(false);
      showToast("Rule added.", "success");
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to add rule."), "error");
    }
  };

  const handleDeleteRule = async (ruleId) => {
    if (!course?.id) return;
    
    try {
      await api.delete(`/authoring/progression-rules/${ruleId}`);
      setProgressionRules(progressionRules.filter(r => r.id !== ruleId));
      showToast("Rule deleted.", "success");
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to delete rule."), "error");
    }
  };

  const handleToggleRule = async (ruleId, currentStatus) => {
    if (!course?.id) return;
    
    try {
      const { data } = await api.put(`/authoring/progression-rules/${ruleId}`, {
        is_active: !currentStatus,
      });
      setProgressionRules(progressionRules.map(r => r.id === ruleId ? data.rule : r));
      showToast(`Rule ${!currentStatus ? "enabled" : "disabled"}.`, "success");
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to update rule."), "error");
    }
  };

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

        {(activeModule || (activeSection && activeSection.id !== 0)) && (
          <SectionCard title="Progression Rules">
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {currentTargetRules.length === 0 && !loadingRules && (
                <div style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                  No rules configured for this {activeModule ? "module" : "section"}.
                </div>
              )}
              {loadingRules && (
                <div style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                  Loading rules...
                </div>
              )}
              {currentTargetRules.map((rule) => (
                <div
                  key={rule.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "8px",
                    padding: "8px",
                    background: "var(--surface-subtle)",
                    borderRadius: "4px",
                    fontSize: "12px",
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                      {rule.rule_type.replace(/_/g, " ")}
                    </div>
                    <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>
                      {rule.is_active ? "Active" : "Inactive"}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "4px" }}>
                    <IconButton
                      icon={rule.is_active ? "toggle-on" : "toggle-off"}
                      size="small"
                      label={rule.is_active ? "Disable rule" : "Enable rule"}
                      onClick={() => handleToggleRule(rule.id, rule.is_active)}
                    />
                    <IconButton
                      icon="trash"
                      size="small"
                      label="Delete rule"
                      onClick={() => handleDeleteRule(rule.id)}
                    />
                  </div>
                </div>
              ))}
              {!showAddRule && (
                <Button
                  tone="neutral"
                  size="small"
                  icon="plus"
                  onClick={() => setShowAddRule(true)}
                  style={{ width: "100%" }}
                >
                  Add Rule
                </Button>
              )}
              {showAddRule && (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  <select
                    value={newRuleType}
                    onChange={(e) => setNewRuleType(e.target.value)}
                    style={{
                      padding: "8px",
                      borderRadius: "4px",
                      border: "1px solid var(--border-subtle)",
                      fontSize: "13px",
                    }}
                  >
                    <option value="previous_module_completed">Previous module completed</option>
                    <option value="previous_section_completed">Previous section completed</option>
                  </select>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <Button
                      tone="primary"
                      size="small"
                      onClick={handleCreateRule}
                      style={{ flex: 1 }}
                    >
                      Add
                    </Button>
                    <Button
                      tone="neutral"
                      size="small"
                      onClick={() => setShowAddRule(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </SectionCard>
        )}
      </div>
    </aside>
  );
}
