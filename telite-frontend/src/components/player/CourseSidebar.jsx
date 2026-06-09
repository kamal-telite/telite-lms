import React from "react";
import { Icon, Button } from "../common/ui";

export function CourseSidebar({ course, activeModule, onSelectModule, progressData, onExit }) {
  if (!course) return null;

  const modules = course.modules_json || [];

  return (
    <div className="course-sidebar" style={{ width: "300px", borderRight: "1px solid var(--border)", background: "var(--surface)", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{ padding: "16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: "12px" }}>
        <button onClick={onExit} style={{ background: "transparent", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", padding: "4px", borderRadius: "4px" }} title="Exit Course">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
        </button>
        <div style={{ fontWeight: 600, fontSize: "16px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {course.name}
        </div>
      </div>

      {/* Progress Summary */}
      <div style={{ padding: "16px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px", fontWeight: 500 }}>
          COURSE PROGRESS
        </div>
        <div className="progress-track" style={{ height: "6px", background: "var(--border)", borderRadius: "3px", overflow: "hidden" }}>
          <div 
            className="progress-fill" 
            style={{ 
              width: `${(Object.values(progressData).filter(status => status === "completed").length / (modules.length || 1)) * 100}%`,
              background: "var(--brand)", 
              height: "100%" 
            }} 
          />
        </div>
      </div>

      {/* Module List */}
      <div style={{ flex: 1, overflowY: "auto", padding: "12px 0" }}>
        {modules.map((mod, index) => {
          const isActive = activeModule?.id === mod.id;
          const isCompleted = progressData[mod.id] === "completed";
          
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
                background: isActive ? "var(--surface-hover)" : "transparent",
                borderLeft: isActive ? "3px solid var(--brand)" : "3px solid transparent",
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
                color: isCompleted ? "#fff" : "var(--text-muted)",
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
                  color: isActive ? "var(--text)" : "var(--text-secondary)",
                  fontSize: "14px",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis"
                }}>
                  {mod.title}
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px", textTransform: "capitalize" }}>
                  {mod.module_type || "Lesson"}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
