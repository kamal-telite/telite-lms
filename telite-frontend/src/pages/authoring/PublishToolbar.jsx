import React, { useMemo, useState } from "react";
import { Button, useToast, Badge } from "../../components/common/ui";
import { api, getErrorMessage } from "../../services/client";
import { validateCourseForPublishing } from "../../services/publishValidation";

function groupValidationErrors(errors) {
  const groups = [];
  const byKey = new Map();

  errors.forEach((error) => {
    const title = error.moduleTitle
      ? `${error.sectionTitle || "Course"} / ${error.moduleTitle}`
      : error.sectionTitle || error.type || "Course";
    const key = `${title}-${error.moduleId || error.sectionId || error.type}`;

    if (!byKey.has(key)) {
      byKey.set(key, { key, title, moduleId: error.moduleId, items: [] });
      groups.push(byKey.get(key));
    }
    byKey.get(key).items.push(error);
  });

  return groups;
}

export function PublishToolbar({ courseId, courseStatus, onStatusChanged, validationStatus, onSelectModule }) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [validationErrors, setValidationErrors] = useState([]);
  const groupedErrors = useMemo(() => groupValidationErrors(validationErrors), [validationErrors]);

  const executeWorkflow = async (action) => {
    setLoading(true);
    setValidationErrors([]);

    // Pre-flight validation
    if (action === "submit_for_review" || action === "publish") {
      const validation = await validateCourseForPublishing(courseId);
      if (!validation.isValid) {
        setValidationErrors(validation.errors);
        showToast(`Cannot proceed. ${validation.errors.length} validation errors found.`, "error");
        console.error("Publish Validation Errors:", validation.errors);
        setLoading(false);
        return;
      }
    }

    try {
      const { data } = await api.post(`/authoring/publishing/courses/${courseId}/workflow`, { action });
      showToast(`Course marked as ${data.status.toUpperCase()}`, "success");
      if (onStatusChanged) onStatusChanged(data.status);
    } catch (err) {
      showToast(getErrorMessage(err, "Workflow action failed."), "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "16px 24px", background: "#fff", borderBottom: "1px solid #e2e8f0" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ fontSize: "14px", color: "#64748b", fontWeight: 500 }}>Publishing State:</div>
          <Badge tone={courseStatus === "published" ? "success" : courseStatus === "review" ? "warning" : "neutral"}>
            {(courseStatus || "DRAFT").toUpperCase()}
          </Badge>
        </div>
        
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          {courseStatus === "draft" && (
            <Button 
              tone="primary" 
              disabled={loading} 
              onClick={() => executeWorkflow("submit_for_review")}
            >
              Submit For Review
            </Button>
          )}

          {courseStatus === "review" && (
            <>
              <Button tone="danger" disabled={loading} onClick={() => executeWorkflow("reject")}>Reject</Button>
              <Button tone="success" disabled={loading} onClick={() => executeWorkflow("approve")}>Approve</Button>
            </>
          )}

          {courseStatus === "approved" && (
            <Button tone="primary" disabled={loading} onClick={() => executeWorkflow("publish")}>Publish Course</Button>
          )}

          {courseStatus === "published" && (
            <Button tone="neutral" disabled={loading} onClick={() => executeWorkflow("archive")}>Archive</Button>
          )}
        </div>
      </div>

      {validationErrors.length > 0 && (
        <div style={{ marginTop: "12px", padding: "12px", border: "1px solid #fecaca", background: "#fef2f2", borderRadius: "8px", color: "#991b1b", fontSize: "13px" }}>
          <div style={{ fontWeight: 600, marginBottom: "8px" }}>Fix these before publishing:</div>
          <div style={{ display: "grid", gap: "10px" }}>
            {groupedErrors.slice(0, 6).map((group) => (
              <div key={group.key} style={{ background: "#fff", border: "1px solid #fecaca", borderRadius: "8px", padding: "10px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center", marginBottom: "6px" }}>
                  <div style={{ fontWeight: 700 }}>{group.title}</div>
                  {group.moduleId && onSelectModule ? (
                    <Button tone="neutral" onClick={() => onSelectModule(group.moduleId)}>Fix</Button>
                  ) : null}
                </div>
                <ul style={{ margin: 0, paddingLeft: "18px" }}>
                  {group.items.slice(0, 3).map((error, index) => (
                    <li key={`${error.type}-${error.blockId || error.moduleId || index}`}>{error.message}</li>
                  ))}
                </ul>
                {group.items.length > 3 ? (
                  <div style={{ marginTop: "6px", color: "#64748b" }}>{group.items.length - 3} more issue(s) here.</div>
                ) : null}
              </div>
            ))}
          </div>
          {validationErrors.length > 8 && (
            <div style={{ marginTop: "6px" }}>And {validationErrors.length - 8} more.</div>
          )}
        </div>
      )}
    </div>
  );
}
