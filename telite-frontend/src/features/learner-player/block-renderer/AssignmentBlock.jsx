import React, { useEffect, useRef, useState } from 'react';
import { api } from "../../../services/client";
import { canEditAssignment, canResubmitAssignment, getAssignmentStatusLabel, normalizeAssignmentStatus } from "../../../utils/assignmentStatus";

export function AssignmentBlock({ title, settings, blockId }) {
  const dueDate = settings?.due_date;
  const points = settings?.points;

  const [status, setStatus] = useState("loading");
  const [submissionId, setSubmissionId] = useState(null);
  const [submissionText, setSubmissionText] = useState("");
  const [grade, setGrade] = useState(null);
  const [feedback, setFeedback] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [error, setError] = useState("");
  const [fileError, setFileError] = useState("");
  const [files, setFiles] = useState([]);
  const submittingRef = useRef(false);
  const hasLocalEditsRef = useRef(false);
  const hasLoadedSubmissionRef = useRef(false);

  const ALLOWED_FILE_EXTENSIONS = [
    ".pdf", ".doc", ".docx", ".zip", ".txt", ".csv", ".xlsx", ".ppt", ".pptx",
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp",
    ".java", ".kt", ".scala", ".py", ".js", ".mjs", ".ts", ".tsx",
    ".html", ".css", ".scss", ".json", ".xml", ".yml", ".yaml", ".md",
    ".cs", ".go", ".rs", ".swift", ".php", ".rb", ".pl", ".lua", ".dart",
    ".r", ".m", ".sh", ".bash", ".zsh", ".sql",
  ];
  const MAX_FILE_BYTES = 25 * 1024 * 1024;
  const fileAcceptString = ALLOWED_FILE_EXTENSIONS.join(",");

  const getFileCacheKey = (file) => {
    if (file.cache_key) return file.cache_key;
    if (file.isPending && file.file) {
      return `${file.filename}:${file.size_bytes}:${file.file.lastModified}`;
    }
    return `${file.file_path || file.asset_id || file.filename}:${file.size_bytes}:${file.mime_type || ""}`;
  };

  const normalizeServerFile = (file) => ({
    ...file,
    isPending: false,
    cache_key: `${file.file_path || file.asset_id || file.filename}:${file.size_bytes}:${file.mime_type || ""}`,
  });

  const normalizePendingFile = (selectedFile) => ({
    cache_key: `${selectedFile.name}:${selectedFile.size}:${selectedFile.lastModified}`,
    filename: selectedFile.name,
    original_filename: selectedFile.name,
    size_bytes: selectedFile.size,
    mime_type: selectedFile.type || "application/octet-stream",
    file: selectedFile,
    isPending: true,
  });

  // applySubmission is intentionally kept near the submit handlers below; this
  // polling effect should only restart when the assignment block changes.
  useEffect(() => {
    let cancelled = false;
    let requestId = 0;

    if (!blockId) {
      setStatus("idle");
      return undefined;
    }

    const resetSubmissionState = () => {
      setSubmissionId(null);
      setSubmissionText("");
      setGrade(null);
      setFeedback("");
      setFiles([]);
      setError("");
      setFileError("");
      setStatus("loading");
      hasLocalEditsRef.current = false;
      hasLoadedSubmissionRef.current = false;
    };

    const fetchSubmission = async () => {
      const currentRequestId = ++requestId;
      if (!hasLoadedSubmissionRef.current) {
        resetSubmissionState();
      }

      try {
        const { data } = await api.get(`/api/v1/learner/assignments/${blockId}/submission`);
        if (cancelled || currentRequestId !== requestId) return;
        hasLoadedSubmissionRef.current = true;
        applySubmission(data, "not_submitted");
      } catch (requestError) {
        if (cancelled || currentRequestId !== requestId) return;
        hasLoadedSubmissionRef.current = true;
        const errorDetail = requestError?.response?.data?.detail || "Unable to load your assignment submission.";
        if (requestError?.response?.status === 404) {
          setStatus("error");
          setError(errorDetail || "Assignment not found.");
          return;
        }
        setStatus("error");
        setError(errorDetail);
      }
    };

    fetchSubmission();
    const intervalId = window.setInterval(fetchSubmission, 10000);
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        fetchSubmission();
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      cancelled = true;
      requestId += 1;
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [blockId]); // eslint-disable-line react-hooks/exhaustive-deps

  const applySubmission = (response, fallbackStatus) => {
    const submission = response?.submission || response || null;
    const apiStatus = response?.status || submission?.normalized_status || submission?.status || fallbackStatus;

    if (!submission) {
      setSubmissionId(null);
      setSubmissionText((current) => (hasLocalEditsRef.current ? current : ""));
      setGrade(null);
      setFeedback("");
      setFiles((current) => (hasLocalEditsRef.current ? current.filter((file) => file.isPending) : []));
      setFileError("");
      setStatus(normalizeAssignmentStatus(apiStatus));
      return;
    }

    const normalizedStatus = normalizeAssignmentStatus(submission.normalized_status || submission.status || apiStatus);
    setSubmissionId(submission.id ?? null);
    setStatus(normalizedStatus);
    setSubmissionText((current) => (hasLocalEditsRef.current ? current : (submission.submission_text || "")));
    setGrade(submission.grade ?? null);
    setFeedback(submission.feedback || "");
    setFiles((current) => {
      const serverFiles = (submission.files || submission.submission_files_json || []).map(normalizeServerFile);
      if (!hasLocalEditsRef.current) return serverFiles;

      const serverKeys = new Set(serverFiles.map(getFileCacheKey));
      const pendingFiles = current.filter((file) => file.isPending && !serverKeys.has(getFileCacheKey(file)));
      return [...serverFiles, ...pendingFiles];
    });
    setFileError("");
  };

  const validateFile = (file) => {
    const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!file.name || extension === "" || !ALLOWED_FILE_EXTENSIONS.includes(extension)) {
      return `File type is not allowed. Accepted types: ${ALLOWED_FILE_EXTENSIONS.join(", ")}`;
    }
    if (file.size <= 0) {
      return "Uploaded file is empty.";
    }
    if (file.size > MAX_FILE_BYTES) {
      return `File is too large. Maximum size is ${Math.round(MAX_FILE_BYTES / (1024 * 1024))} MB.`;
    }
    return null;
  };

  const handleFileSelect = (event) => {
    const selectedFiles = Array.from(event.target.files || []);
    if (!selectedFiles.length) return;
    setFileError("");

    const newFiles = [];
    const currentKeys = new Set(files.map(getFileCacheKey));

    for (const file of selectedFiles) {
      const validationError = validateFile(file);
      if (validationError) {
        setFileError(validationError);
        continue;
      }
      const key = `${file.name}:${file.size}:${file.lastModified}`;
      if (currentKeys.has(key)) {
        setFileError("This file has already been selected.");
        continue;
      }
      currentKeys.add(key);
      newFiles.push(normalizePendingFile(file));
    }

    if (newFiles.length === 0) {
      event.target.value = null;
      return;
    }

    setFiles((current) => [
      ...current.filter((file) => !file.isPending),
      ...newFiles,
    ]);
    hasLocalEditsRef.current = true;
    event.target.value = null;
  };

  const buildFormData = () => {
    const formData = new FormData();
    formData.append("submission_text", submissionText || "");
    const existingFilePaths = files
      .filter((file) => !file.isPending)
      .map((file) => file.file_path || file.asset_id)
      .filter(Boolean);
    formData.append("existing_file_paths", JSON.stringify(existingFilePaths));
    files.forEach((file) => {
      if (file.isPending && file.file) {
        formData.append("files", file.file);
      }
    });
    return formData;
  };

  const buildDraftPayload = () => ({
    submission_text: submissionText || "",
    existing_file_paths: files
      .filter((file) => !file.isPending)
      .map((file) => file.file_path || file.asset_id)
      .filter(Boolean),
  });

  const removeFile = (index) => {
    setFiles((current) => current.filter((_, idx) => idx !== index));
    setFileError("");
    hasLocalEditsRef.current = true;
  };

  const handleSaveDraft = async () => {
    if (savingDraft || submittingRef.current) return;
    setSavingDraft(true);
    setError("");
    try {
      const { data } = await api.patch(`/api/v1/learner/assignments/${blockId}/draft`, buildDraftPayload());
      hasLocalEditsRef.current = false;
      applySubmission(data?.submission, "draft");
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || "Failed to save assignment draft.");
    } finally {
      setSavingDraft(false);
    }
  };

  const handleSubmit = async ({ resubmit = false } = {}) => {
    if (submittingRef.current) return;
    setError("");
    setFileError("");
    submittingRef.current = true;
    setSubmitting(true);
    try {
      const endpoint = resubmit
        ? `/api/v1/learner/assignments/${blockId}/resubmit`
        : `/api/v1/learner/assignments/${blockId}/submit`;
      const { data } = await api.post(endpoint, buildFormData());
      hasLocalEditsRef.current = false;
      applySubmission(data?.submission, resubmit ? "resubmitted" : "submitted");
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || "Failed to submit assignment.");
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  };

  const downloadUrl = (file) => {
    if (!submissionId) return "#";
    const assetId = file?.asset_id || file?.file_path;
    const query = assetId ? `?asset_id=${encodeURIComponent(assetId)}` : "";
    return `/api/v1/submissions/${submissionId}/download${query}`;
  };

  const canEdit = canEditAssignment(status);
  const statusLabel = getAssignmentStatusLabel(status);

  const renderFileList = () => files.length > 0 ? (
    <ul style={{ margin: "8px 0 0", paddingLeft: "20px", fontSize: "13px", color: "var(--text-secondary)" }}>
      {files.map((file, index) => (
        <li key={`${file.asset_id || file.file_path || file.filename}-${index}`}>
          {file.original_filename || file.filename || "Attachment"}
          {file.file_path && submissionId ? (
            <>
              {" "}
              <a href={downloadUrl(file)} style={{ color: "var(--primary)" }}>Download</a>
            </>
          ) : null}
          {canEdit ? (
            <button
              type="button"
              onClick={() => removeFile(index)}
              style={{ marginLeft: "10px", color: "var(--error)", background: "none", border: "none", cursor: "pointer", fontSize: "13px" }}
            >
              Remove
            </button>
          ) : null}
        </li>
      ))}
    </ul>
  ) : null;

  const renderEditor = ({ resubmit = false } = {}) => (
    <div>
      <textarea
        style={{ width: "100%", minHeight: "100px", padding: "8px", borderRadius: "4px", border: "1px solid var(--border-subtle)", background: "var(--surface-sunken)", color: "var(--text-primary)", fontFamily: "inherit" }}
        placeholder="Write your response here..."
        value={submissionText}
        onChange={(event) => {
          hasLocalEditsRef.current = true;
          setSubmissionText(event.target.value);
        }}
        disabled={submitting || savingDraft}
      />
      <div style={{ marginTop: "12px" }}>
        <label style={{ display: "inline-block", padding: "6px 12px", background: "var(--surface-sunken)", border: "1px solid var(--border-subtle)", borderRadius: "4px", cursor: submitting ? "not-allowed" : "pointer", fontSize: "13px", color: "var(--text-secondary)" }}>
          Attach File
          <input type="file" accept={fileAcceptString} multiple style={{ display: "none" }} onChange={handleFileSelect} disabled={submitting || savingDraft} />
        </label>
        {renderFileList()}
      </div>
      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "16px" }}>
        {!resubmit ? (
          <button
            onClick={handleSaveDraft}
            disabled={savingDraft || submitting}
            style={{ padding: "8px 16px", background: "var(--surface-sunken)", color: "var(--text-primary)", border: "1px solid var(--border-subtle)", borderRadius: "4px", cursor: savingDraft ? "not-allowed" : "pointer" }}
          >
            {savingDraft ? "Saving..." : "Save Draft"}
          </button>
        ) : null}
        <button
          onClick={() => handleSubmit({ resubmit })}
          disabled={submitting || (!submissionText.trim() && files.length === 0)}
          style={{ padding: "8px 16px", background: "var(--primary)", color: "#fff", border: "none", borderRadius: "4px", cursor: (submitting || (!submissionText.trim() && files.length === 0)) ? "not-allowed" : "pointer" }}
        >
          {submitting ? "Submitting..." : resubmit ? "Resubmit Assignment" : "Submit Assignment"}
        </button>
      </div>
    </div>
  );

  return (
    <div style={{ padding: "18px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)", margin: "1em 0" }}>
      <div style={{ fontWeight: 700, fontSize: "18px", marginBottom: "8px" }}>
        {title || "Assignment"}
      </div>
      <p style={{ margin: 0, whiteSpace: "pre-wrap", color: "var(--text-primary)" }}>
        {settings?.instructions || "Assignment instructions are not available."}
      </p>
      {(dueDate || points) ? (
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "14px", color: "var(--text-muted)", fontSize: "14px" }}>
          {dueDate ? <span>Due: {dueDate}</span> : null}
          {points ? <span>Points: {points}</span> : null}
        </div>
      ) : null}

      {error ? (
        <div style={{ marginTop: "14px", padding: "10px 12px", borderRadius: "6px", background: "var(--error-bg)", color: "var(--error)" }}>
          {error}
        </div>
      ) : null}
      {fileError ? (
        <div style={{ marginTop: "14px", padding: "10px 12px", borderRadius: "6px", background: "var(--error-bg)", color: "var(--error)" }}>
          {fileError}
        </div>
      ) : null}

      {status === "loading" ? (
        <div style={{ marginTop: "24px", color: "var(--text-secondary)" }}>Loading submission...</div>
      ) : status === "error" ? null : (
        <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid var(--border-subtle)" }}>
          <div style={{ fontWeight: 600, marginBottom: "8px" }}>Your Submission</div>
          {canEdit ? renderEditor({ resubmit: canResubmitAssignment(status) }) : (
            <div style={{ background: "var(--surface-sunken)", padding: "12px", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
              <div style={{ color: status === "graded" ? "var(--success)" : "var(--warning)", fontWeight: 600, fontSize: "14px", marginBottom: "8px" }}>
                Status: {statusLabel}
              </div>
              <p style={{ margin: 0, whiteSpace: "pre-wrap", color: "var(--text-secondary)" }}>{submissionText || "No written response."}</p>
              {renderFileList()}
              {(status === "graded" || status === "approved" || status === "rejected" || status === "resubmission_required") && (
                <div style={{ marginTop: "12px", paddingTop: "12px", borderTop: "1px dashed var(--border-strong)" }}>
                  {grade !== null && grade !== undefined ? <div style={{ fontWeight: 600, marginBottom: "4px" }}>Grade: {grade}</div> : null}
                  {feedback ? <div><strong>Feedback:</strong> {feedback}</div> : null}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * BlockRenderer parses and renders TipTap JSON format.
 * Content blocks (e.g. paragraph, heading, codeBlock) are transformed into native React elements.
 */
