import React from "react";
import { Button, LoadingState } from "../../components/common/ui";

export function MediaUsageDrawer({ open, onClose, asset, usageData, loading }) {
  if (!open) return null;

  return (
    <div style={{
      position: "fixed",
      top: 0,
      right: 0,
      bottom: 0,
      width: "400px",
      background: "#fff",
      boxShadow: "-4px 0 16px rgba(0,0,0,0.1)",
      zIndex: 9999,
      display: "flex",
      flexDirection: "column",
      borderLeft: "1px solid #e2e8f0"
    }}>
      <div style={{
        padding: "20px",
        borderBottom: "1px solid #e2e8f0",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center"
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 600, color: "#0f172a" }}>Media Usage</h2>
          <div style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>
            {asset?.filename} is used in {asset?.used_by_blocks} location(s)
          </div>
        </div>
        <button 
          onClick={onClose}
          style={{ background: "none", border: "none", fontSize: "20px", cursor: "pointer", color: "#64748b" }}
        >
          ×
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "20px" }}>
        {loading ? (
          <LoadingState message="Loading usage data..." />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {usageData.map((u, i) => (
              <div key={i} style={{ border: "1px solid #e2e8f0", borderRadius: "8px", overflow: "hidden" }}>
                <div style={{ padding: "12px", background: "#f8fafc", borderBottom: "1px solid #e2e8f0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontWeight: 600, fontSize: "14px", color: "#0f172a" }}>
                    {u.course_title}
                  </div>
                  <Button tone="neutral" size="small" onClick={() => window.open(`/authoring/courses/${u.course_id}/builder?module=${u.module_id}&block=${u.block_id}`, "_blank")}>
                    Open
                  </Button>
                </div>
                <div style={{ padding: "12px", fontFamily: "monospace", fontSize: "12px", color: "#475569", lineHeight: 1.5 }}>
                  <div style={{ paddingLeft: "12px", borderLeft: "2px solid #cbd5e1" }}>
                    {u.section_title}
                  </div>
                  <div style={{ paddingLeft: "24px", borderLeft: "2px solid #cbd5e1" }}>
                    └─ {u.module_title}
                  </div>
                  <div style={{ paddingLeft: "36px", borderLeft: "2px solid #cbd5e1" }}>
                    &nbsp;&nbsp;└─ Block #{u.block_id} ({u.block_type})
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
