import React from "react";
import { Badge } from "../../components/common/ui";

function TextDiff({ oldText, newText }) {
  return (
    <div style={{ display: "flex", gap: "16px", marginTop: "12px", borderTop: "1px solid var(--border-subtle)", paddingTop: "12px" }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "4px", textTransform: "uppercase" }}>Previous</div>
        <div style={{ padding: "12px", background: "var(--error-bg)", borderRadius: "6px", fontSize: "13px", color: "var(--error)", overflowX: "auto" }}>
          {oldText ? <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontFamily: "inherit" }}>{oldText}</pre> : <em>(Empty)</em>}
        </div>
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "4px", textTransform: "uppercase" }}>New</div>
        <div style={{ padding: "12px", background: "var(--success-bg)", borderRadius: "6px", fontSize: "13px", color: "var(--success)", overflowX: "auto" }}>
          {newText ? <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontFamily: "inherit" }}>{newText}</pre> : <em>(Empty)</em>}
        </div>
      </div>
    </div>
  );
}

function DiffSection({ title, diffData }) {
  if (!diffData || (diffData.added.length === 0 && diffData.removed.length === 0 && diffData.modified.length === 0)) {
    return null;
  }

  return (
    <div style={{ marginBottom: "24px" }}>
      <h4 style={{ margin: "0 0 12px 0", color: "var(--text-primary)", borderBottom: "2px solid var(--border-subtle)", paddingBottom: "8px" }}>{title}</h4>
      
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {diffData.added.map(item => (
          <div key={`added-${item.id}`} style={{ padding: "12px", background: "var(--surface-sunken)", borderLeft: "4px solid var(--success)", borderRadius: "4px", boxShadow: "0 1px 2px rgba(0,0,0,0.05)" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{item.title || item.block_type || `Item ${item.id}`}</div>
              <Badge tone="success">ADDED</Badge>
            </div>
            {item.content && <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.content}</div>}
          </div>
        ))}

        {diffData.removed.map(item => (
          <div key={`removed-${item.id}`} style={{ padding: "12px", background: "var(--surface-sunken)", borderLeft: "4px solid var(--error)", borderRadius: "4px", opacity: 0.8 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <div style={{ fontWeight: 600, color: "var(--text-muted)", textDecoration: "line-through" }}>{item.title || item.block_type || `Item ${item.id}`}</div>
              <Badge tone="danger">REMOVED</Badge>
            </div>
          </div>
        ))}

        {diffData.modified.map(item => (
          <div key={`mod-${item.id}`} style={{ padding: "12px", background: "var(--surface-sunken)", borderLeft: "4px solid var(--warning)", borderRadius: "4px", boxShadow: "0 1px 2px rgba(0,0,0,0.05)" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{item.title || item.block_type || `Item ${item.id}`}</div>
              <Badge tone="warning">MODIFIED</Badge>
            </div>
            <div style={{ marginTop: "8px", fontSize: "12px" }}>
              {item._changes.map((c, i) => (
                <div key={i} style={{ color: "var(--text-secondary)", marginBottom: "4px" }}>
                  <span style={{ fontWeight: 600, color: "var(--text-secondary)" }}>{c.field}:</span> changed
                </div>
              ))}
            </div>
            {item._changes.some(c => c.field === "content") && (
               <TextDiff oldText={item._old_content} newText={item._new_content} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export function CourseDiffViewer({ diff }) {
  if (!diff) return null;

  const hasChanges = ["sections", "modules", "blocks"].some(k => 
    diff[k] && (diff[k].added.length > 0 || diff[k].removed.length > 0 || diff[k].modified.length > 0)
  );

  if (!hasChanges) {
    return (
      <div style={{ padding: "24px", textAlign: "center", color: "var(--text-secondary)", background: "var(--surface-sunken)", borderRadius: "8px", border: "1px dashed var(--border-subtle)" }}>
        No structural or content differences found.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      <DiffSection title="Sections" diffData={diff.sections} />
      <DiffSection title="Modules" diffData={diff.modules} />
      <DiffSection title="Blocks" diffData={diff.blocks} />
    </div>
  );
}
