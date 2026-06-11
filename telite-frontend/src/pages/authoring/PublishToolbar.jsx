import React, { useState } from "react";
import { Button, useToast, Badge, Modal } from "../../components/common/ui";
import { api, getErrorMessage } from "../../services/client";
import { validateCourseForPublishing } from "../../services/publishValidation";
import { useCapability } from "../../hooks/useCapability";

export function PublishToolbar({ courseId, courseStatus, onStatusChanged, validationStatus, onFixValidation }) {
  const { canSubmit, canApprove, canReject, canPublish } = useCapability();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [validationData, setValidationData] = useState(null);
  const [workflowDialog, setWorkflowDialog] = useState(null);
  const [workflowNotes, setWorkflowNotes] = useState("");
  
  // Use real-time validation status from backend if available, fallback to fetched data
  const validationSummary = validationStatus?.summary || validationData?.summary;
  const validationResults = validationStatus?.results || validationData?.results || [];

  const executeWorkflow = async (action, notes = "") => {
    setLoading(true);

    // Pre-flight validation on frontend
    if (action === "submit_for_review" || action === "publish") {
      const validation = await validateCourseForPublishing(courseId);
      if (validation.summary && validation.summary.errors > 0) {
        setValidationData({ summary: validation.summary, results: validation.results || [] });
        showToast(`Cannot proceed. ${validation.summary.errors} validation errors found.`, "error");
        setLoading(false);
        return;
      }
    }

    try {
      const { data } = await api.post(`/authoring/publishing/courses/${courseId}/workflow`, { action, notes });
      showToast(`Course marked as ${data.status.toUpperCase()}`, "success");
      if (onStatusChanged) onStatusChanged(data.status);
    } catch (err) {
      showToast(getErrorMessage(err, "Workflow action failed."), "error");
    } finally {
      setLoading(false);
    }
  };

  const openWorkflowDialog = (action) => {
    setWorkflowDialog(action);
    setWorkflowNotes("");
  };

  const confirmWorkflowDialog = async () => {
    if (!workflowDialog) return;
    const action = workflowDialog;
    const notes = workflowNotes.trim();
    setWorkflowDialog(null);
    setWorkflowNotes("");
    await executeWorkflow(action, notes);
  };

  const workflowLabels = {
    submit_for_review: "Submit For Review",
    approve: "Approve Course",
    reject: "Reject Course",
    publish: "Publish Course",
    archive: "Archive Course",
  };

  // Grouping by severity
  const errors = validationResults.filter(r => r.severity === "error");
  const warnings = validationResults.filter(r => r.severity === "warning");
  const infos = validationResults.filter(r => r.severity === "info");

  const ValidationCard = ({ result, icon }) => (
    <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
        <div style={{ fontSize: "16px" }}>{icon}</div>
        <div>
          <div style={{ fontWeight: 600, color: "#1e293b" }}>{result.message}</div>
          {result.fix_target?.module_title && (
            <div style={{ fontSize: "12px", color: "#64748b", marginTop: "2px" }}>
              Module: {result.fix_target.module_title}
            </div>
          )}
          {!result.fix_target?.module_title && result.fix_target?.section_title && (
            <div style={{ fontSize: "12px", color: "#64748b", marginTop: "2px" }}>
              Location: {result.fix_target.section_title}
            </div>
          )}
        </div>
      </div>
      {result.fix_target?.module_id && onFixValidation && (
        <Button tone="neutral" size="small" onClick={() => onFixValidation(result.fix_target.module_id, result.fix_target.block_id)}>Fix</Button>
      )}
    </div>
  );

  return (
    <div style={{ padding: "16px 24px", background: "#fff", borderBottom: "1px solid #e2e8f0" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ fontSize: "14px", color: "#64748b", fontWeight: 500 }}>Publishing State:</div>
          <Badge tone={courseStatus === "published" ? "success" : courseStatus === "review" ? "warning" : "neutral"}>
            {(courseStatus || "DRAFT").toUpperCase()}
          </Badge>
          
          {validationSummary && validationSummary.score !== undefined && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginLeft: "16px", borderLeft: "1px solid #e2e8f0", paddingLeft: "16px" }}>
              <div style={{ fontSize: "13px", color: "#64748b", fontWeight: 500 }}>Readiness Score:</div>
              <Badge tone={validationSummary.score === 100 ? "success" : validationSummary.score > 50 ? "warning" : "danger"}>
                {validationSummary.score}%
              </Badge>
            </div>
          )}
        </div>
        
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          {courseStatus === "draft" && canSubmit && (
            <Button 
              tone="primary" 
              disabled={loading} 
              onClick={() => openWorkflowDialog("submit_for_review")}
            >
              Submit For Review
            </Button>
          )}

          {courseStatus === "review" && (
            <>
              {canReject && <Button tone="danger" disabled={loading} onClick={() => openWorkflowDialog("reject")}>Reject</Button>}
              {canApprove && <Button tone="success" disabled={loading} onClick={() => openWorkflowDialog("approve")}>Approve</Button>}
            </>
          )}

          {courseStatus === "approved" && canPublish && (
            <Button tone="primary" disabled={loading} onClick={() => openWorkflowDialog("publish")}>Publish Course</Button>
          )}

          {courseStatus === "published" && canPublish && (
            <Button tone="neutral" disabled={loading} onClick={() => openWorkflowDialog("archive")}>Archive</Button>
          )}
        </div>
      </div>

      {validationResults.length > 0 && (
        <div style={{ marginTop: "24px", padding: "16px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px" }}>
          <div style={{ fontWeight: 600, marginBottom: "16px", fontSize: "16px", color: "#0f172a" }}>Publish Readiness</div>
          
          <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "12px", maxHeight: "400px", overflowY: "auto" }}>
            {errors.map((error, idx) => (
              <ValidationCard key={`err-${idx}`} result={error} icon="❌" />
            ))}
            
            {warnings.map((warning, idx) => (
              <ValidationCard key={`warn-${idx}`} result={warning} icon="⚠" />
            ))}
            
            {infos.map((info, idx) => (
              <ValidationCard key={`info-${idx}`} result={info} icon="ℹ️" />
            ))}
          </div>
        </div>
      )}

      <Modal
        open={Boolean(workflowDialog)}
        onClose={() => setWorkflowDialog(null)}
        title={workflowLabels[workflowDialog] || "Update Workflow"}
        description="Add a note for the course review history."
        width={520}
        footer={
          <>
            <Button tone="neutral" onClick={() => setWorkflowDialog(null)}>Cancel</Button>
            <Button tone="primary" disabled={loading} onClick={confirmWorkflowDialog}>
              {workflowLabels[workflowDialog] || "Confirm"}
            </Button>
          </>
        }
      >
        <textarea
          className="field__input"
          style={{ minHeight: "120px", resize: "vertical" }}
          placeholder="Reviewer notes..."
          value={workflowNotes}
          onChange={(event) => setWorkflowNotes(event.target.value)}
        />
      </Modal>
    </div>
  );
}
