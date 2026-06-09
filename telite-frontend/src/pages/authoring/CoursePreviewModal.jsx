import React, { useState } from "react";
import { Modal, Button, Badge } from "../../components/common/ui";

export function CoursePreviewModal({ open, onClose, courseId, courseName }) {
  const [role, setRole] = useState("learner"); // learner, cat_admin, super_admin

  const roleStyles = {
    learner: { bg: "#f0fdf4", color: "#166534", border: "#bbf7d0", text: "Learner View" },
    cat_admin: { bg: "#eff6ff", color: "#1e40af", border: "#bfdbfe", text: "Category Admin View" },
    super_admin: { bg: "#fdf2f8", color: "#9d174d", border: "#fbcfe8", text: "Super Admin View" }
  };

  const currentStyle = roleStyles[role];

  return (
    <Modal open={open} onClose={onClose} title={`Preview: ${courseName || "Course"}`} width="1000px">
      <div style={{ display: "flex", gap: "12px", marginBottom: "16px", padding: "12px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
        <div style={{ fontWeight: 600, color: "#475569", display: "flex", alignItems: "center", marginRight: "16px" }}>Preview As:</div>
        <Button tone={role === "learner" ? "primary" : "neutral"} onClick={() => setRole("learner")}>Learner</Button>
        <Button tone={role === "cat_admin" ? "primary" : "neutral"} onClick={() => setRole("cat_admin")}>Category Admin</Button>
        <Button tone={role === "super_admin" ? "primary" : "neutral"} onClick={() => setRole("super_admin")}>Super Admin</Button>
      </div>

      <div style={{ 
        border: `2px solid ${currentStyle.border}`, 
        borderRadius: "12px", 
        height: "600px", 
        display: "flex", 
        flexDirection: "column",
        overflow: "hidden"
      }}>
        {/* Mock Browser Header */}
        <div style={{ background: currentStyle.bg, padding: "12px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: `1px solid ${currentStyle.border}` }}>
          <div style={{ color: currentStyle.color, fontWeight: 600 }}>{currentStyle.text}</div>
          <Badge tone="neutral">SIMULATED</Badge>
        </div>

        {/* Player Canvas Placeholder */}
        <div style={{ flex: 1, background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", color: "#64748b" }}>
          <div style={{ fontSize: "48px", marginBottom: "16px" }}>🖥️</div>
          <h3 style={{ margin: "0 0 8px 0" }}>Course Player Context</h3>
          <p style={{ margin: 0, fontSize: "14px" }}>The full Player UI for {role.replace("_", " ")} will render here.</p>
          <div style={{ marginTop: "24px", padding: "16px", background: "#f1f5f9", borderRadius: "8px", maxWidth: "400px", textAlign: "center", fontSize: "13px" }}>
            <strong>Note:</strong> The actual player integration involves rendering the completed structure through the <code>/player</code> router, respecting the specific enrollment/admin bypassing rules for this role.
          </div>
        </div>
      </div>
    </Modal>
  );
}
