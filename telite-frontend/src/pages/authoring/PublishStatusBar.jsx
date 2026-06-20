import React, { useState } from "react";
import { Button, useToast, Badge, Modal } from "../../components/common/ui";
import { api, getErrorMessage } from "../../services/client";
import { validateCourseForPublishing } from "../../services/publishValidation";
import { useCapability } from "../../hooks/useCapability";
import { ReadinessDrawer } from "./ReadinessDrawer";
import "./builder.css";

export function PublishStatusBar({ courseId, courseStatus, onStatusChanged, validationStatus, onFixValidation, saveState, lockState }) {
  const { canSubmit, canApprove, canReject, canPublish } = useCapability();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [validationData, setValidationData] = useState(null);
  const [workflowDialog, setWorkflowDialog] = useState(null);
  const [workflowNotes, setWorkflowNotes] = useState("");
  const [showReadiness, setShowReadiness] = useState(false);
  
  const validationSummary = validationStatus?.summary || validationData?.summary;
  const validationResults = validationStatus?.results || validationData?.results || [];

  const executeWorkflow = async (action, notes = "") => {
    setLoading(true);

    if (action === "submit_for_review" || action === "publish") {
      const validation = await validateCourseForPublishing(courseId);
      if (validation.summary && validation.summary.errors > 0) {
        setValidationData({ summary: validation.summary, results: validation.results || [] });
        showToast(`Cannot proceed. ${validation.summary.errors} validation errors found.`, "error");
        setShowReadiness(true);
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

  const errors = validationResults.filter(r => r.severity === "error");

  // saveState is an object { state: string, lastSaved: Date|null } passed from CourseBuilderLayout
  const saveStateValue = typeof saveState === 'object' ? saveState?.state : saveState;
  const saveLastSaved = typeof saveState === 'object' ? saveState?.lastSaved : null;

  // Normalize status: backend may store 'active' which is equivalent to 'published'
  const normalizedStatus = courseStatus === 'active' ? 'published' : (courseStatus || 'draft');

  return (
    <>
      <div className="builder-status-bar">
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {saveStateValue === 'saving' && <div className="saving-dot" />}
          <span>
            {saveStateValue === 'saving' ? 'Saving...' 
              : saveStateValue === 'error' ? 'Save Error' 
              : saveStateValue === 'offline' ? 'Offline (cached locally)'
              : saveStateValue === 'conflict' ? 'Save Conflict'
              : saveLastSaved ? `Saved ${saveLastSaved.toLocaleTimeString()}` 
              : 'Saved'}
          </span>
        </div>

        <div className="builder-status-bar__divider" />

        <div className="builder-status-bar__readiness" onClick={() => setShowReadiness(true)}>
          Readiness: {validationSummary?.score !== undefined ? `${validationSummary.score}%` : "Checking..."}
          {errors.length > 0 && <span style={{ color: "var(--error)", fontWeight: 600 }}>({errors.length} errors)</span>}
        </div>

        <div className="builder-status-bar__divider" />

        <div>{lockState || "Active editor session"}</div>

        <div className="builder-status-bar__spacer" />
        
        <div style={{ display: "flex", alignItems: "center", gap: "16px", fontWeight: 600 }}>
          <Badge tone={normalizedStatus === "published" ? "success" : normalizedStatus === "review" ? "warning" : normalizedStatus === "approved" ? "accent" : "neutral"}>
            {normalizedStatus.toUpperCase()}
          </Badge>
        </div>
        
        <div style={{ display: "flex", gap: "8px" }}>
          {normalizedStatus === "draft" && canSubmit && (
            <Button tone="primary" size="small" disabled={loading || saveStateValue === 'saving'} onClick={() => openWorkflowDialog("submit_for_review")}>Submit For Review</Button>
          )}
          {normalizedStatus === "review" && (
            <>
              {canReject && <Button tone="danger" size="small" disabled={loading} onClick={() => openWorkflowDialog("reject")}>Reject</Button>}
              {canApprove && <Button tone="success" size="small" disabled={loading} onClick={() => openWorkflowDialog("approve")}>Approve</Button>}
            </>
          )}
          {normalizedStatus === "approved" && canPublish && (
            <Button tone="primary" size="small" disabled={loading} onClick={() => openWorkflowDialog("publish")}>Publish Course</Button>
          )}
          {normalizedStatus === "published" && canPublish && (
            <Button tone="neutral" size="small" disabled={loading} onClick={() => openWorkflowDialog("archive")}>Archive</Button>
          )}
        </div>
      </div>

      <ReadinessDrawer 
        open={showReadiness} 
        onClose={() => setShowReadiness(false)} 
        validationResults={validationResults} 
        onFixValidation={onFixValidation} 
      />

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
    </>
  );
}
