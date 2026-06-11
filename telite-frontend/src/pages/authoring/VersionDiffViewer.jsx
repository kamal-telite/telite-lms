import React, { useState } from "react";
import { Badge, Button } from "../../components/common/ui";

const TYPE_ICONS = {
  section_added: "➕",
  section_removed: "➖",
  section_renamed: "✏️",
  section_reordered: "↕️",
  module_added: "➕",
  module_removed: "➖",
  module_renamed: "✏️",
  module_moved: "📦",
  module_reordered: "↕️",
  block_added: "➕",
  block_removed: "➖",
  block_reordered: "↕️",
  block_content_changed: "📝",
  block_settings_changed: "⚙️",
  media_changed: "🖼️",
  quiz_changed: "❓",
  assignment_changed: "📋",
  scorm_changed: "📦",
};

const TYPE_LABELS = {
  section_added: "Section Added",
  section_removed: "Section Removed",
  section_renamed: "Section Renamed",
  section_reordered: "Section Reordered",
  module_added: "Module Added",
  module_removed: "Module Removed",
  module_renamed: "Module Renamed",
  module_moved: "Module Moved",
  module_reordered: "Module Reordered",
  block_added: "Block Added",
  block_removed: "Block Removed",
  block_reordered: "Block Reordered",
  block_content_changed: "Content Changed",
  block_settings_changed: "Settings Changed",
  media_changed: "Media Changed",
  quiz_changed: "Quiz Changed",
  assignment_changed: "Assignment Changed",
  scorm_changed: "SCORM Changed",
};

function EventCard({ event }) {
  const [expanded, setExpanded] = useState(false);
  
  const icon = TYPE_ICONS[event.type] || "📄";
  const label = TYPE_LABELS[event.type] || event.type;
  
  let entityName = "Unknown";
  if (event.section_title) entityName = event.section_title;
  else if (event.module_title) entityName = event.module_title;
  else if (event.block_type) entityName = `${event.block_type.toUpperCase()} Block`;
  
  if (event.type === "section_renamed" || event.type === "module_renamed") {
    entityName = `"${event.old_title}" → "${event.new_title}"`;
  }

  const isAddition = event.type.includes("_added");
  const isRemoval = event.type.includes("_removed");
  
  const tone = isAddition ? "success" : isRemoval ? "danger" : "warning";

  return (
    <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: "8px", overflow: "hidden", marginBottom: "8px" }}>
      <div 
        style={{ 
          padding: "12px", 
          display: "flex", 
          justifyContent: "space-between", 
          alignItems: "center",
          cursor: event.diff_html ? "pointer" : "default",
          background: event.diff_html && expanded ? "#f8fafc" : "#fff"
        }}
        onClick={() => { if (event.diff_html) setExpanded(!expanded) }}
      >
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <div style={{ fontSize: "16px", width: "24px", textAlign: "center" }}>{icon}</div>
          <div>
            <div style={{ fontWeight: 600, color: "#1e293b", fontSize: "14px" }}>{label}</div>
            <div style={{ fontSize: "13px", color: "#64748b", marginTop: "2px" }}>
              {entityName}
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Badge tone={tone}>{isAddition ? "ADDED" : isRemoval ? "REMOVED" : "MODIFIED"}</Badge>
          {event.diff_html && (
            <div style={{ color: "#94a3b8", fontSize: "12px" }}>
              {expanded ? "▲ Hide Diff" : "▼ Show Diff"}
            </div>
          )}
        </div>
      </div>
      
      {expanded && event.diff_html && (
        <div style={{ padding: "16px", borderTop: "1px solid #e2e8f0", background: "#f8fafc" }}>
          <div style={{ fontSize: "11px", fontWeight: 700, color: "#94a3b8", marginBottom: "8px", textTransform: "uppercase" }}>Text Differences</div>
          <div 
            style={{ 
              padding: "12px", 
              background: "#fff", 
              border: "1px solid #e2e8f0", 
              borderRadius: "6px", 
              fontSize: "13px", 
              color: "#334155", 
              overflowX: "auto",
              lineHeight: 1.5,
              whiteSpace: "pre-wrap"
            }}
            dangerouslySetInnerHTML={{ __html: event.diff_html }}
          />
        </div>
      )}
    </div>
  );
}

export function VersionDiffViewer({ diffResult }) {
  if (!diffResult || !diffResult.changes) return null;

  const { changes, summary } = diffResult;

  if (changes.length === 0) {
    return (
      <div style={{ padding: "24px", textAlign: "center", color: "#64748b", background: "#f8fafc", borderRadius: "8px", border: "1px dashed #cbd5e1" }}>
        No structural or content differences found.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Summary Stats */}
      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", padding: "12px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
        <div style={{ fontSize: "12px" }}><span style={{ fontWeight: 600 }}>{summary.sections_added}</span> Sections Added</div>
        <div style={{ fontSize: "12px" }}><span style={{ fontWeight: 600 }}>{summary.modules_added}</span> Modules Added</div>
        <div style={{ fontSize: "12px" }}><span style={{ fontWeight: 600 }}>{summary.blocks_changed}</span> Blocks Changed</div>
      </div>

      {/* Events List */}
      <div>
        {changes.map((event, idx) => (
          <EventCard key={`evt-${idx}`} event={event} />
        ))}
      </div>
    </div>
  );
}
