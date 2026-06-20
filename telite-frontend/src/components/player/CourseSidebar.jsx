import React from "react";


export function CourseSidebar({ course, activeModule, onSelectModule, progressData, onExit }) {
  if (!course) return null;

  const modules = course.modules_json || [];

  // Count completed modules
  const completedCount = Object.values(progressData).filter(status => status === "completed").length;
  const totalCount = modules.length || 1;
  const progressPercent = Math.round((completedCount / totalCount) * 100);

  return (
    <div className="course-sidebar" style={{ width: "300px", borderRight: "1px solid var(--border-subtle)", background: "var(--surface-bg)", display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div style={{ padding: "16px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: "12px", flexShrink: 0 }}>
        <button onClick={onExit} style={{ background: "transparent", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", padding: "4px", borderRadius: "4px" }} title="Exit Course">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
        </button>
        <div style={{ fontWeight: 600, fontSize: "16px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {course.name}
        </div>
      </div>

      {/* Progress Summary */}
      <div style={{ padding: "16px", borderBottom: "1px solid var(--border-subtle)", flexShrink: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 500 }}>
            COURSE PROGRESS
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 500 }}>
            {completedCount}/{modules.length} modules · {progressPercent}%
          </div>
        </div>
        <div className="progress-track" style={{ height: "6px", background: "var(--border-subtle)", borderRadius: "3px", overflow: "hidden" }}>
          <div 
            className="progress-fill" 
            style={{ 
              width: `${progressPercent}%`,
              background: "var(--primary)", 
              height: "100%",
              transition: "width 0.3s ease"
            }} 
          />
        </div>
      </div>

      {/* Module List */}
      <div style={{ flex: 1, overflowY: "auto", padding: "12px 0" }}>
        {modules.map((mod, index) => {
          const isActive = activeModule?.id === mod.id;
          const isCompleted = progressData[mod.id] === "completed";
          const blockCount = Array.isArray(mod.content) ? mod.content.length : 0;
          
          return (
            <button
              key={mod.id}
              onClick={() => onSelectModule(mod)}
              style={{
                display: "flex",
                alignItems: "center",
                width: "100%",
                padding: "12px 16px",
                border: "none",
                background: isActive ? "var(--surface-raised)" : "transparent",
                borderLeft: isActive ? "3px solid var(--primary)" : "3px solid transparent",
                cursor: "pointer",
                textAlign: "left",
                gap: "12px",
                transition: "background 0.2s"
              }}
            >
              <div style={{ 
                width: "24px", 
                height: "24px", 
                borderRadius: "50%", 
                border: isCompleted ? "none" : "1px solid var(--border-strong)",
                background: isCompleted ? "var(--success)" : "transparent",
                color: isCompleted ? "var(--text-inverse)" : "var(--text-muted)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "12px",
                flexShrink: 0
              }}>
                {isCompleted ? "✓" : index + 1}
              </div>
              <div style={{ flex: 1, overflow: "hidden" }}>
                <div style={{ 
                  fontWeight: isActive ? 600 : 500, 
                  color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                  fontSize: "14px",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis"
                }}>
                  {mod.title}
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span style={{ textTransform: "capitalize" }}>{mod.module_type || "Lesson"}</span>
                  {blockCount > 0 && (
                    <span style={{ background: "var(--border-subtle)", borderRadius: "8px", padding: "0 6px", fontSize: "11px", fontWeight: 500 }}>
                      {blockCount} {blockCount === 1 ? "block" : "blocks"}
                    </span>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
