import React, { useEffect, useRef, useState } from 'react';
import { api, fetchQuizStats } from "../../services/client";

const richTextThemeStyles = `
  .native-block-content,
  .tiptap-content {
    color: var(--text-primary);
  }

  .native-block-content h1,
  .native-block-content h2,
  .native-block-content h3,
  .native-block-content h4,
  .native-block-content h5,
  .native-block-content h6,
  .native-block-content p,
  .native-block-content span,
  .native-block-content li,
  .native-block-content strong,
  .native-block-content em,
  .tiptap-content h1,
  .tiptap-content h2,
  .tiptap-content h3,
  .tiptap-content h4,
  .tiptap-content h5,
  .tiptap-content h6,
  .tiptap-content p,
  .tiptap-content span,
  .tiptap-content li,
  .tiptap-content strong,
  .tiptap-content em {
    color: inherit;
  }
`;

function postLearnerEvents(events) {
  return api.post("/api/v1/learner/events", { events }).catch(() => {});
}

// Reusable component to track when a block enters the viewport
function TrackedBlock({ children, blockId, courseId, moduleId, blockType }) {
  const ref = useRef(null);
  const [viewed, setViewed] = useState(false);

  useEffect(() => {
    if (!ref.current || viewed || !courseId) return;

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setViewed(true);
        observer.disconnect();

        const eventType = blockType === "h5p" ? "H5P_STARTED" : "BLOCK_VIEWED";
        postLearnerEvents([{
          event_type: eventType,
          course_id: courseId,
          module_id: moduleId,
          ...(Number.isInteger(blockId) ? { block_id: blockId } : {})
        }]);
      }
    }, { threshold: 0.5 });

    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [viewed, courseId, moduleId, blockId, blockType]);

  return <div ref={ref}>{children}</div>;
}

function VideoBlock({ src, courseId, moduleId, blockId }) {
  const title = "Video lesson";

  if (!src) {
    return (
      <div style={{ padding: "16px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)", color: "var(--text-muted)" }}>
        Video is not configured.
      </div>
    );
  }

  const handleEvent = (eventType) => {
    if (!courseId) return;
    postLearnerEvents([{
      event_type: eventType,
      course_id: courseId,
      module_id: moduleId,
      ...(Number.isInteger(blockId) ? { block_id: blockId } : {})
    }]);
  };

  return (
    <div style={{ margin: "1em 0" }}>
      <video
        src={src}
        controls
        preload="metadata"
        title={title}
        style={{ width: "100%", maxHeight: "70vh", background: "var(--surface-bg)", borderRadius: "8px", display: "block" }}
        onPlay={() => handleEvent("VIDEO_STARTED")}
        onPause={() => handleEvent("VIDEO_PAUSED")}
        onEnded={() => handleEvent("VIDEO_COMPLETED")}
      >
        <a href={src} target="_blank" rel="noreferrer">Open video</a>
      </video>
      <div style={{ marginTop: "8px" }}>
        <a href={src} target="_blank" rel="noreferrer" style={{ color: "var(--primary)", fontWeight: 700 }}>
          Open video in new tab
        </a>
      </div>
    </div>
  );
}

function AudioBlock({ src }) {
  return (
    <audio
      src={src}
      controls
      style={{ width: "100%", margin: "1em 0" }}
    />
  );
}

function EmbedBlock({ title, src }) {
  if (!src) {
    return (
      <div style={{ padding: "16px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)" }}>
        Embed not configured
      </div>
    );
  }

  return (
    <div style={{ margin: "1em 0" }}>
      {title ? <div style={{ fontWeight: 600, marginBottom: "8px" }}>{title}</div> : null}
      <iframe
        src={src}
        title={title || "Embedded content"}
        loading="lazy"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
        style={{ width: "100%", minHeight: "420px", border: "1px solid var(--border-subtle)", borderRadius: "8px" }}
      />
    </div>
  );
}

function ScormBlock({ title, src, filename }) {
  return (
    <div style={{ padding: "16px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)", margin: "1em 0" }}>
      <div style={{ fontWeight: 700, marginBottom: "6px" }}>{title || "SCORM Package"}</div>
      <div style={{ color: "var(--text-muted)", fontSize: "14px", marginBottom: "12px" }}>
        {filename || "Launch the attached SCORM package."}
      </div>
      {src ? (
        <a href={src} target="_blank" rel="noreferrer" style={{ color: "var(--primary)", fontWeight: 700 }}>
          Launch SCORM
        </a>
      ) : (
        <span style={{ color: "var(--text-muted)" }}>Package not configured</span>
      )}
    </div>
  );
}

function H5PBlock({ title, src, filename, courseId, moduleId, blockId, assetId, assetVersion }) {
  console.log("H5P BLOCK RENDERED", { title, src, filename, courseId, moduleId, blockId, assetId, assetVersion });
  const [completed, setCompleted] = React.useState(false);

  React.useEffect(() => {
    const sendEvent = (eventType, statement) => {
      if (!courseId) return;
      postLearnerEvents([{
        event_type: eventType,
        course_id: courseId,
        module_id: moduleId,
        ...(Number.isInteger(blockId) ? { block_id: blockId } : {}),
        payload_json: {
          source: "h5p_xapi",
          verb: statement?.verb?.id,
          activity: statement?.object?.definition?.name || statement?.object?.id,
          score: statement?.result?.score || null,
          success: statement?.result?.success,
          completion: statement?.result?.completion
        }
      }]);
    };

    const handleMessage = (event) => {
      if (event.data?.type === 'H5P_xAPI') {
        const stmt = event.data.event;
        const verb = stmt?.verb?.id;

        if (stmt?.result?.score) {
          sendEvent("H5P_SCORED", stmt);
        }

        if (verb === 'http://adlnet.gov/expapi/verbs/completed') {
          if (!completed && courseId) {
            setCompleted(true);
            sendEvent("H5P_COMPLETED", stmt);
          }
        } else if (verb === 'http://adlnet.gov/expapi/verbs/passed') {
          if (!completed && courseId) {
            setCompleted(true);
            sendEvent("H5P_PASSED", stmt);
          }
        } else if (verb === 'http://adlnet.gov/expapi/verbs/failed') {
          sendEvent("H5P_FAILED", stmt);
        }
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [completed, courseId, moduleId, blockId]);

  if (!assetId) {
    return (
      <div style={{ padding: "16px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)", color: "var(--text-muted)", margin: "1em 0" }}>
        H5P content is not configured or missing asset reference.
      </div>
    );
  }

  const version = assetVersion || 1;
  const h5pContentUrl = `/api/v1/player/h5p/${assetId}/versions/${version}`;
  const playerUrl = `/h5p/index.html?src=${encodeURIComponent(h5pContentUrl)}`;

  return (
    <div style={{ margin: "1em 0", border: "1px solid var(--border-subtle)", borderRadius: "8px", overflow: "hidden", background: "var(--surface-raised)" }}>
      <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border-subtle)", fontWeight: 700 }}>
        {title || filename || "H5P Interactive Content"}
      </div>
      <iframe
        src={playerUrl}
        title={title || filename || "H5P Content"}
        style={{ width: "100%", height: "600px", border: 0, display: "block", background: "var(--surface-bg)" }}
        allowFullScreen
        allow="microphone; camera; autoplay"
      />
    </div>
  );
}

function PdfBlock({ title, src, filename, blockId, allowDownload = true }) {
  const [pdfUrl, setPdfUrl] = useState("");
  const [directUrl, setDirectUrl] = useState("");
  const [loading, setLoading] = useState(Boolean(blockId || src));
  const [error, setError] = useState("");
  const frameRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    let objectUrl = "";
    const endpoint = blockId ? `/api/v1/learner/blocks/${blockId}/pdf` : src;
    if (!endpoint) {
      setLoading(false);
      setPdfUrl("");
      setDirectUrl("");
      return undefined;
    }

    setDirectUrl(api.getUri({ url: endpoint }));
    setLoading(true);
    setError("");
    api.get(endpoint, { responseType: "blob" })
      .then((response) => {
        if (cancelled) return;
        const contentType = response.headers?.["content-type"] || response.data?.type || "";
        if (!String(contentType).includes("application/pdf")) {
          throw new Error("The server did not return a PDF file.");
        }
        objectUrl = URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
        setPdfUrl(objectUrl);
      })
      .catch((err) => {
        if (cancelled) return;
        setPdfUrl("");
        setError(err?.response?.data?.detail || err?.message || "Unable to load this PDF.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [blockId, src]);

  const openPdf = () => {
    const targetUrl = directUrl || pdfUrl;
    if (targetUrl) window.open(targetUrl, "_blank", "noopener,noreferrer");
  };

  const downloadPdf = () => {
    if (!pdfUrl) return;
    const link = document.createElement("a");
    link.href = pdfUrl;
    link.download = filename || `${title || "document"}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const toggleFullscreen = () => {
    const target = frameRef.current?.parentElement;
    if (target?.requestFullscreen) {
      target.requestFullscreen();
    } else {
      openPdf();
    }
  };

  if (!blockId && !src) {
    return (
      <div style={{ padding: "16px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)", color: "var(--text-muted)" }}>
        PDF is not configured.
      </div>
    );
  }

  return (
    <div style={{ margin: "1em 0", border: "1px solid var(--border-subtle)", borderRadius: "8px", overflow: "hidden", background: "var(--surface-raised)" }}>
      <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
        <div>
          <div style={{ fontWeight: 700 }}>{title || filename || "PDF Document"}</div>
          {filename ? <div style={{ color: "var(--text-muted)", fontSize: "13px", marginTop: "2px" }}>{filename}</div> : null}
        </div>
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <button type="button" className="link-button" onClick={openPdf} disabled={!pdfUrl} style={{ color: "var(--primary)", fontWeight: 700 }}>Open</button>
          <button type="button" className="link-button" onClick={toggleFullscreen} disabled={!pdfUrl} style={{ color: "var(--primary)", fontWeight: 700 }}>Full Screen</button>
          {allowDownload ? (
            <button type="button" className="link-button" onClick={downloadPdf} disabled={!pdfUrl} style={{ color: "var(--primary)", fontWeight: 700 }}>Download</button>
          ) : null}
        </div>
      </div>
      {loading ? (
        <div style={{ minHeight: "360px", display: "grid", placeItems: "center", color: "var(--text-muted)", background: "var(--surface-bg)" }}>
          Loading PDF...
        </div>
      ) : error ? (
        <div style={{ minHeight: "260px", padding: "24px", display: "grid", placeItems: "center", textAlign: "center", color: "var(--text-muted)", background: "var(--surface-bg)" }}>
          <div>
            <div style={{ fontWeight: 700, color: "var(--text-primary)", marginBottom: "6px" }}>PDF could not be loaded</div>
            <div>{error}</div>
          </div>
        </div>
      ) : (
        <iframe
          ref={frameRef}
          src={pdfUrl}
          title={title || filename || "PDF document"}
          style={{ width: "100%", height: "min(78vh, 760px)", minHeight: "520px", border: 0, display: "block", background: "var(--surface-bg)" }}
          onError={() => setError("The browser could not display this PDF. Use Open to view it in a new tab.")}
        />
      )}
    </div>
  );
}

function AssignmentBlock({ title, settings, blockId }) {
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
  const [files, setFiles] = useState([]);
  const [pendingFiles, setPendingFiles] = useState([]);

  useEffect(() => {
    let cancelled = false;
    if (!blockId) {
      setStatus("idle");
      return undefined;
    }
    setError("");
    api.get(`/api/v1/learner/assignments/${blockId}/submission`)
      .then(({ data }) => {
        if (cancelled) return;
        applySubmission(data?.submission, "idle");
      })
      .catch((requestError) => {
        if (cancelled) return;
        if (requestError?.response?.status === 404) {
          setStatus("idle");
          return;
        }
        setStatus("error");
        setError(requestError?.response?.data?.detail || "Unable to load your assignment submission.");
      });
    return () => {
      cancelled = true;
    };
  }, [blockId]);

  const applySubmission = (submission, fallbackStatus) => {
    if (!submission) {
      setStatus(fallbackStatus);
      return;
    }
    setSubmissionId(submission.id ?? null);
    setStatus(submission.status || fallbackStatus);
    setSubmissionText(submission.submission_text || "");
    setGrade(submission.grade ?? null);
    setFeedback(submission.feedback || "");
    setFiles(submission.files || submission.submission_files_json || []);
    setPendingFiles([]);
  };

  const handleFileSelect = (event) => {
    const selectedFiles = Array.from(event.target.files || []);
    if (!selectedFiles.length) return;
    setPendingFiles((current) => [...current, ...selectedFiles]);
    setFiles((current) => [
      ...current,
      ...selectedFiles.map((file) => ({
        filename: file.name,
        original_filename: file.name,
        size_bytes: file.size,
      })),
    ]);
    event.target.value = null;
  };

  const buildFormData = () => {
    const formData = new FormData();
    formData.append("submission_text", submissionText || "");
    for (const file of pendingFiles) {
      formData.append("files", file);
    }
    return formData;
  };

  const handleSaveDraft = async () => {
    setSavingDraft(true);
    setError("");
    try {
      const { data } = await api.patch(`/api/v1/learner/assignments/${blockId}/draft`, {
        submission_text: submissionText,
      });
      applySubmission(data?.submission, "draft");
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || "Failed to save assignment draft.");
    } finally {
      setSavingDraft(false);
    }
  };

  const handleSubmit = async ({ resubmit = false } = {}) => {
    setSubmitting(true);
    setError("");
    try {
      const endpoint = resubmit
        ? `/api/v1/learner/assignments/${blockId}/resubmit`
        : `/api/v1/learner/assignments/${blockId}/submit`;
      const { data } = await api.post(endpoint, buildFormData());
      applySubmission(data?.submission, resubmit ? "resubmitted" : "submitted");
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || "Failed to submit assignment.");
    } finally {
      setSubmitting(false);
    }
  };

  const downloadUrl = (file) => {
    if (!submissionId) return "#";
    const assetId = file?.asset_id || file?.file_path;
    const query = assetId ? `?asset_id=${encodeURIComponent(assetId)}` : "";
    return `/api/v1/submissions/${submissionId}/download${query}`;
  };

  const canEdit = ["idle", "draft", "returned"].includes(status);
  const statusLabel = {
    draft: "Draft saved",
    submitted: "Submitted - Awaiting Review",
    resubmitted: "Resubmitted - Awaiting Review",
    graded: "Graded",
    returned: "Returned for revision",
  }[status] || "Not submitted";

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
        onChange={(event) => setSubmissionText(event.target.value)}
        disabled={submitting || savingDraft}
      />
      <div style={{ marginTop: "12px" }}>
        <label style={{ display: "inline-block", padding: "6px 12px", background: "var(--surface-sunken)", border: "1px solid var(--border-subtle)", borderRadius: "4px", cursor: submitting ? "not-allowed" : "pointer", fontSize: "13px", color: "var(--text-secondary)" }}>
          Attach File
          <input type="file" multiple style={{ display: "none" }} onChange={handleFileSelect} disabled={submitting || savingDraft} />
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

      {status === "loading" ? (
        <div style={{ marginTop: "24px", color: "var(--text-secondary)" }}>Loading submission...</div>
      ) : status === "error" ? null : (
        <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid var(--border-subtle)" }}>
          <div style={{ fontWeight: 600, marginBottom: "8px" }}>Your Submission</div>
          {canEdit ? renderEditor({ resubmit: status === "returned" }) : (
            <div style={{ background: "var(--surface-sunken)", padding: "12px", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
              <div style={{ color: status === "graded" ? "var(--success)" : "var(--warning)", fontWeight: 600, fontSize: "14px", marginBottom: "8px" }}>
                Status: {statusLabel}
              </div>
              <p style={{ margin: 0, whiteSpace: "pre-wrap", color: "var(--text-secondary)" }}>{submissionText || "No written response."}</p>
              {renderFileList()}
              {status === "graded" && (
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
export function BlockRenderer({ content, courseId, moduleId }) {
  if (!content) return null;

  let parsed = content;
  if (typeof content === "string") {
    try {
      parsed = JSON.parse(content);
    } catch (e) {
      console.error("BlockRenderer: Failed to parse content as JSON", e);
      return <div className="rendered-content error">Failed to load content.</div>;
    }
  }

  if (Array.isArray(parsed)) {
    const visibleBlocks = parsed.filter((block) => !block.settings?.hidden);

    return (
      <div className="native-block-content" style={{ display: "flex", flexDirection: "column", gap: "1em", fontSize: "16px", lineHeight: 1.6, color: "var(--text-primary)" }}>
        <style>{richTextThemeStyles}</style>
        {visibleBlocks.map((block) => (
          <TrackedBlock key={block.id || block.sort_order} blockId={block.id} courseId={courseId} moduleId={moduleId} blockType={block.block_type}>
            {renderNativeBlock(block, courseId, moduleId)}
          </TrackedBlock>
        ))}
      </div>
    );
  }

  // TipTap structure: { type: 'doc', content: [ { type: 'paragraph', content: [...] }, ... ] }
  if (parsed.type === "doc" && Array.isArray(parsed.content)) {
    return (
      <div className="tiptap-content" style={{ display: "flex", flexDirection: "column", gap: "1em", fontSize: "16px", lineHeight: 1.6, color: "var(--text-primary)" }}>
        <style>{richTextThemeStyles}</style>
        {parsed.content.map((node, i) => (
          <TrackedBlock key={i} blockId={`block_${i}`} courseId={courseId} moduleId={moduleId}>
            {renderNode(node, i, courseId, moduleId)}
          </TrackedBlock>
        ))}
      </div>
    );
  }

  return <div className="rendered-content">Unsupported content format.</div>;
}

function renderNativeBlock(block, courseId, moduleId) {
  const settings = block.metadata_json || block.settings || {};

  switch (block.block_type) {
    case "heading":
      return <h2 style={{ margin: "1em 0 0.5em 0", fontSize: "1.8rem", fontWeight: 600 }}>{block.content}</h2>;
    case "text":
    case "paragraph":
      return <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{block.content}</p>;
    case "image":
      return <img src={settings.url} alt={settings.alt || ""} style={{ maxWidth: "100%", height: "auto", borderRadius: "8px", margin: "1em 0" }} />;
    case "video":
      return <VideoBlock src={settings.url} courseId={courseId} moduleId={moduleId} blockId={block.id} />;
    case "audio":
      return <AudioBlock src={settings.url} />;
    case "pdf":
      return <PdfBlock title={block.content} src={settings.url} filename={settings.filename} blockId={block.id} allowDownload={settings.allow_download !== false} />;
    case "scorm":
      return <ScormBlock title={block.content} src={settings.url} filename={settings.filename} />;
    case "h5p":
      return <H5PBlock title={block.content} src={settings.url} filename={settings.filename} courseId={courseId} moduleId={moduleId} blockId={block.id} assetId={settings.asset_id} assetVersion={settings.asset_version} />;
    case "poll":
      return <PollBlock blockId={block.id} courseId={courseId} moduleId={moduleId} settings={settings} />;
    case "flashcard":
      return <FlashcardBlock blockId={block.id} courseId={courseId} moduleId={moduleId} settings={settings} />;
    case "resource_collection":
      return <ResourceCollectionBlock blockId={block.id} courseId={courseId} moduleId={moduleId} settings={settings} />;
    case "quiz":
      return <QuizBlock blockId={block.id} courseId={courseId} moduleId={moduleId} settings={settings} />;
    case "embed":
      return <EmbedBlock title={block.content} src={settings.url} />;
    case "assignment":
      return <AssignmentBlock title={block.content} dueDate={settings.due_date} points={settings.points} blockId={block.id} courseId={courseId} moduleId={moduleId} settings={settings} />;
    case "quiz_reference":
      return <div style={{ padding: "16px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)" }}>Quiz: {settings.quiz_title || settings.quiz_id || "Not configured"}</div>;
    default:
      return <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{block.content || ""}</p>;
  }
}

function renderNode(node, index, courseId, moduleId) {
  if (!node) return null;

  switch (node.type) {
    case 'paragraph':
      return <p style={{ margin: 0 }}>{renderMarks(node.content)}</p>;
    case 'heading': {
      const level = node.attrs?.level || 2;
      const HeadingTag = `h${level}`;
      const headingStyle = { margin: "1em 0 0.5em 0", fontWeight: 600 };
      if (level === 1) headingStyle.fontSize = "2.25rem";
      else if (level === 2) headingStyle.fontSize = "1.8rem";
      else if (level === 3) headingStyle.fontSize = "1.5rem";
      
      return <HeadingTag style={headingStyle}>{renderMarks(node.content)}</HeadingTag>;
    }
    case 'bulletList':
      return (
        <ul style={{ paddingLeft: "1.5em", margin: 0 }}>
          {node.content?.map((item, i) => <React.Fragment key={i}>{renderNode(item, i, courseId, moduleId)}</React.Fragment>)}
        </ul>
      );
    case 'orderedList':
      return (
        <ol style={{ paddingLeft: "1.5em", margin: 0 }}>
          {node.content?.map((item, i) => <React.Fragment key={i}>{renderNode(item, i, courseId, moduleId)}</React.Fragment>)}
        </ol>
      );
    case 'listItem':
      return <li style={{ marginBottom: "0.25em" }}>{node.content?.map((item, i) => <React.Fragment key={i}>{renderNode(item, i, courseId, moduleId)}</React.Fragment>)}</li>;
    case 'codeBlock':
      return (
        <pre style={{ background: "var(--surface-sunken)", padding: "16px", borderRadius: "8px", overflowX: "auto", fontFamily: "monospace" }}>
          <code>{renderMarks(node.content)}</code>
        </pre>
      );
    case 'blockquote':
      return (
        <blockquote style={{ borderLeft: "4px solid var(--border)", paddingLeft: "1em", margin: 0, color: "var(--text-muted)", fontStyle: "italic" }}>
          {node.content?.map((item, i) => <React.Fragment key={i}>{renderNode(item, i, courseId, moduleId)}</React.Fragment>)}
        </blockquote>
      );
    case 'horizontalRule':
      return <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "2em 0" }} />;
    case 'image':
      return (
        <img 
          src={node.attrs?.src} 
          alt={node.attrs?.alt || ""} 
          title={node.attrs?.title}
          style={{ maxWidth: "100%", height: "auto", borderRadius: "8px", margin: "1em 0" }} 
        />
      );
    case 'video':
      return <VideoBlock src={node.attrs?.src} courseId={courseId} moduleId={moduleId} blockId={`block_${index}`} />;
    default:
      // Fallback for unknown block types
      return renderMarks(node.content);
  }
}

function renderMarks(contentNodes) {
  if (!contentNodes || !Array.isArray(contentNodes)) return null;

  return contentNodes.map((node, i) => {
    if (node.type === 'text') {
      let textElement = node.text;
      
      if (node.marks) {
        node.marks.forEach(mark => {
          if (mark.type === 'bold') {
            textElement = <strong key={`b-${i}`}>{textElement}</strong>;
          } else if (mark.type === 'italic') {
            textElement = <em key={`i-${i}`}>{textElement}</em>;
          } else if (mark.type === 'strike') {
            textElement = <s key={`s-${i}`}>{textElement}</s>;
          } else if (mark.type === 'code') {
            textElement = <code key={`c-${i}`} style={{ background: "var(--surface-sunken)", padding: "0.1em 0.3em", borderRadius: "3px", fontFamily: "monospace" }}>{textElement}</code>;
          } else if (mark.type === 'link') {
            textElement = <a key={`l-${i}`} href={mark.attrs?.href} target={mark.attrs?.target || "_blank"} style={{ color: "var(--primary)", textDecoration: "underline" }}>{textElement}</a>;
          }
        });
      }
      return <React.Fragment key={i}>{textElement}</React.Fragment>;
    }
    
    // Nested inline nodes?
    return <React.Fragment key={i}>{renderNode(node, i)}</React.Fragment>;
  });
}

export function PollBlock({ blockId, courseId, moduleId, settings }) {
  const [loading, setLoading] = React.useState(true);
  const [voted, setVoted] = React.useState(false);
  const [results, setResults] = React.useState({});
  const [totalVotes, setTotalVotes] = React.useState(0);
  const [selectedOptions, setSelectedOptions] = React.useState([]);
  const [isVoting, setIsVoting] = React.useState(false);

  const fetchResults = async () => {
    try {
      const { data } = await api.get(`/api/v1/learner/blocks/${blockId}/poll-results`);
      setResults(data.results || {});
      setTotalVotes(data.total_votes || 0);
      if (data.my_vote && data.my_vote.length > 0) {
        setVoted(true);
        setSelectedOptions(data.my_vote);
      }
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  React.useEffect(() => {
    if (blockId) fetchResults();
    else setLoading(false);
  }, [blockId]);

  const handleVote = async () => {
    if (selectedOptions.length === 0) return;
    setIsVoting(true);
    try {
      const optionId = selectedOptions[0];
      await api.post(`/api/v1/learner/blocks/${blockId}/poll/vote`, { option_id: optionId });
      await fetchResults();
      setVoted(true);
    } catch (err) {
      if (err?.response?.status === 409) {
        // Already voted — refresh results to show current state
        await fetchResults();
        setVoted(true);
      } else {
        console.error(err);
      }
    }
    setIsVoting(false);
  };

  const toggleOption = (optId) => {
    if (settings?.allow_multiple) {
      setSelectedOptions(prev => prev.includes(optId) ? prev.filter(id => id !== optId) : [...prev, optId]);
    } else {
      setSelectedOptions([optId]);
    }
  };

  if (loading) return <div style={{ padding: "18px" }}>Loading poll...</div>;

  const showResults = settings?.show_results === "always" || (voted && settings?.show_results === "after_vote");
  const options = settings?.options || [];

  return (
    <div style={{ padding: "18px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)", margin: "1em 0" }}>
      <div style={{ fontWeight: 600, fontSize: "16px", marginBottom: "16px" }}>
        {settings?.question || "Poll"}
      </div>

      {(!voted || settings?.allow_vote_change) ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: showResults ? "24px" : "0" }}>
          {options.map((opt) => {
            const isSelected = selectedOptions.includes(opt.id);
            return (
              <label key={opt.id} style={{ 
                display: "flex", alignItems: "center", gap: "12px", cursor: "pointer",
                padding: "12px 16px", borderRadius: "8px", border: "1px solid",
                background: isSelected ? "var(--primary-bg)" : "var(--surface-sunken)",
                borderColor: isSelected ? "var(--border-strong)" : "var(--border-subtle)",
                transition: "all 0.2s"
              }}>
                <input
                  type={settings?.allow_multiple ? "checkbox" : "radio"}
                  name={`poll_${blockId}`}
                  checked={isSelected}
                  onChange={() => toggleOption(opt.id)}
                  style={{ margin: 0, cursor: "pointer" }}
                />
                <span style={{ fontSize: "14px", color: "var(--text-primary)", lineHeight: "1.4" }}>{opt.text}</span>
              </label>
            );
          })}
          <div style={{ marginTop: "8px" }}>
            <button
              onClick={handleVote}
              disabled={selectedOptions.length === 0 || isVoting}
              style={{ padding: "8px 16px", background: "var(--primary)", color: "#fff", border: "none", borderRadius: "4px", cursor: selectedOptions.length === 0 ? "not-allowed" : "pointer" }}
            >
              {isVoting ? "Voting..." : (voted ? "Change Vote" : "Submit Vote")}
            </button>
            {settings?.allow_vote_change && voted && !isVoting && <span style={{ marginLeft: "12px", fontSize: "13px", color: "var(--success)" }}>Your vote is recorded.</span>}
          </div>
        </div>
      ) : (
        !showResults && <div style={{ color: "var(--success)", fontWeight: 500 }}>Thank you for voting!</div>
      )}

      {showResults && (
        <div style={{ borderTop: (!voted || settings?.allow_vote_change) ? "1px solid var(--border)" : "none", paddingTop: (!voted || settings?.allow_vote_change) ? "16px" : "0" }}>
          <div style={{ fontSize: "14px", color: "var(--text-muted)", marginBottom: "12px" }}>Results ({totalVotes} votes)</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {options.map((opt) => {
              const count = results[opt.id] || 0;
              const percent = totalVotes > 0 ? Math.round((count / totalVotes) * 100) : 0;
              return (
                <div key={opt.id}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "14px", marginBottom: "4px" }}>
                    <span>{opt.text}</span>
                    <span>{percent}%</span>
                  </div>
                  <div style={{ height: "8px", background: "var(--border-subtle)", borderRadius: "4px", overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${percent}%`, background: "var(--primary)", transition: "width 0.3s ease" }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export function FlashcardBlock({ blockId, courseId, moduleId, settings }) {
  const [cards, setCards] = React.useState([]);
  const [currentIndex, setCurrentIndex] = React.useState(0);
  const [isFlipped, setIsFlipped] = React.useState(false);
  const [viewedIndices, setViewedIndices] = React.useState(new Set([0]));
  const [completed, setCompleted] = React.useState(false);

  React.useEffect(() => {
    let deck = [...(settings?.cards || [])];
    if (settings?.randomize_order) {
      for (let i = deck.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [deck[i], deck[j]] = [deck[j], deck[i]];
      }
    }
    setCards(deck);
  }, [settings?.cards, settings?.randomize_order]);

  const emitEvent = (eventType, payload = {}) => {
    postLearnerEvents([{
      event_type: eventType,
      course_id: courseId,
      module_id: moduleId,
      block_id: blockId,
      payload_json: payload
    }]).catch(err => console.error(err));
  };

  const handleFlip = () => {
    if (!isFlipped) {
      emitEvent("FLASHCARD_FLIPPED", { card_id: cards[currentIndex]?.id });
    }
    setIsFlipped(!isFlipped);
  };

  const handleNext = () => {
    if (currentIndex < cards.length - 1) {
      const nextIdx = currentIndex + 1;
      setCurrentIndex(nextIdx);
      setIsFlipped(false);
      
      const newViewed = new Set(viewedIndices);
      newViewed.add(nextIdx);
      setViewedIndices(newViewed);

      if (!completed && newViewed.size === cards.length) {
        setCompleted(true);
        emitEvent("BLOCK_COMPLETED");
      }
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setIsFlipped(false);
    }
  };

  if (cards.length === 0) return null;

  const currentCard = cards[currentIndex];

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", margin: "2em 0" }}>
      <div 
        onClick={handleFlip}
        style={{
          width: "100%",
          maxWidth: "500px",
          height: "300px",
          perspective: "1000px",
          cursor: "pointer",
          marginBottom: "24px"
        }}
      >
        <div style={{
          position: "relative",
          width: "100%",
          height: "100%",
          transition: "transform 0.6s",
          transformStyle: "preserve-3d",
          transform: isFlipped ? "rotateY(180deg)" : "rotateY(0deg)"
        }}>
          {/* Front */}
          <div style={{
            position: "absolute",
            width: "100%",
            height: "100%",
            backfaceVisibility: "hidden",
            background: "var(--surface-raised)",
            border: "2px solid var(--border-subtle)",
            borderRadius: "12px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
            boxShadow: "var(--shadow-card)",
            fontSize: "20px",
            textAlign: "center",
            color: "var(--text-primary)",
            whiteSpace: "pre-wrap"
          }}>
            {currentCard?.front_text || "Empty Card"}
          </div>
          {/* Back */}
          <div style={{
            position: "absolute",
            width: "100%",
            height: "100%",
            backfaceVisibility: "hidden",
            background: "var(--surface-sunken)",
            border: "2px solid var(--border-strong)",
            borderRadius: "12px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
            boxShadow: "var(--shadow-card)",
            fontSize: "20px",
            textAlign: "center",
            color: "var(--text-primary)",
            transform: "rotateY(180deg)",
            whiteSpace: "pre-wrap"
          }}>
            {currentCard?.back_text || "Empty Card"}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
        <button 
          onClick={handlePrev} 
          disabled={currentIndex === 0}
          style={{ padding: "12px 24px", fontWeight: 500, background: currentIndex === 0 ? "var(--surface-sunken)" : "var(--primary)", color: currentIndex === 0 ? "var(--text-muted)" : "#fff", border: "none", borderRadius: "24px", cursor: currentIndex === 0 ? "not-allowed" : "pointer", transition: "all 0.2s" }}
        >
          Previous
        </button>
        <span style={{ fontSize: "14px", color: "var(--text-muted)", fontWeight: 500, minWidth: "40px", textAlign: "center" }}>
          {currentIndex + 1} / {cards.length}
        </span>
        <button 
          onClick={handleNext} 
          disabled={currentIndex === cards.length - 1}
          style={{ padding: "12px 24px", fontWeight: 500, background: currentIndex === cards.length - 1 ? "var(--surface-sunken)" : "var(--primary)", color: currentIndex === cards.length - 1 ? "var(--text-muted)" : "#fff", border: "none", borderRadius: "24px", cursor: currentIndex === cards.length - 1 ? "not-allowed" : "pointer", transition: "all 0.2s" }}
        >
          Next
        </button>
      </div>
      
      {completed && <div style={{ marginTop: "16px", color: "var(--success)", fontSize: "14px", fontWeight: 500 }}>All cards viewed!</div>}
    </div>
  );
}

export function ResourceCollectionBlock({ blockId, courseId, moduleId, settings }) {
  const [downloadedIndices, setDownloadedIndices] = React.useState(new Set());
  const [completed, setCompleted] = React.useState(false);
  const resources = settings?.resources || [];
  const completionMode = settings?.completion_mode || "view";

  const emitEvent = React.useCallback((eventType, payload = {}) => {
    postLearnerEvents([{
      event_type: eventType,
      course_id: courseId,
      module_id: moduleId,
      block_id: blockId,
      payload_json: payload
    }]).catch(err => console.error(err));
  }, [courseId, moduleId, blockId]);

  React.useEffect(() => {
    if (completionMode === "view" && !completed) {
      setCompleted(true);
      emitEvent("BLOCK_COMPLETED");
    }
  }, [completionMode, completed, emitEvent]);

  const handleDownload = async (assetId, index) => {
    try {
      const { data } = await api.get(`/api/v1/learner/blocks/${blockId}/resources/${assetId}/download`);
        // Since backend triggers RESOURCE_DOWNLOADED automatically, we don't need to emit it here.
        // We trigger the browser download:
        window.open(data.url, '_blank');
        
        const newDownloaded = new Set(downloadedIndices);
        newDownloaded.add(index);
        setDownloadedIndices(newDownloaded);

        if (!completed) {
          if (completionMode === "download_any" && newDownloaded.size >= 1) {
            setCompleted(true);
            emitEvent("BLOCK_COMPLETED");
          } else if (completionMode === "download_all" && newDownloaded.size >= resources.length) {
            setCompleted(true);
            emitEvent("BLOCK_COMPLETED");
          }
        }
    } catch (err) {
      console.error(err);
      alert("Error downloading resource.");
    }
  };

  if (resources.length === 0) {
    return <div style={{ padding: "16px", color: "var(--text-muted)", fontStyle: "italic" }}>No resources attached.</div>;
  }

  return (
    <div style={{ padding: "18px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)", margin: "1em 0" }}>
      <div style={{ fontWeight: 600, fontSize: "16px", marginBottom: "16px", color: "var(--text-primary)" }}>
        Resource Collection
      </div>
      
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {resources.map((res, idx) => (
          <div key={res.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", border: "1px solid var(--border-subtle)", borderRadius: "6px", background: downloadedIndices.has(idx) ? "var(--success-bg)" : "var(--surface-sunken)" }}>
            <div>
              <div style={{ fontWeight: 500, fontSize: "14px", color: "var(--text-primary)" }}>{res.title}</div>
              <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>{res.description}</div>
            </div>
            <button
              onClick={() => handleDownload(res.asset_id, idx)}
              style={{ padding: "8px 16px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)", borderRadius: "4px", cursor: "pointer", fontWeight: 500, fontSize: "13px", display: "flex", alignItems: "center", gap: "6px" }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              {downloadedIndices.has(idx) ? "Downloaded" : "Download"}
            </button>
          </div>
        ))}
      </div>

      {completed && completionMode !== "view" && completionMode !== "manual_complete" && (
        <div style={{ marginTop: "16px", color: "var(--success)", fontSize: "14px", fontWeight: 500 }}>
          {completionMode === "download_any" ? "Resource downloaded!" : "All resources downloaded!"}
        </div>
      )}
    </div>
  );
}

export function QuizBlock({ blockId, courseId, moduleId, settings }) {
  const [answers, setAnswers] = React.useState({});
  const [submitted, setSubmitted] = React.useState(false);
  const [result, setResult] = React.useState(null);
  const [stats, setStats] = React.useState(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [loadingStats, setLoadingStats] = React.useState(false);

  const questions = settings?.questions || [];
  const passingScore = settings?.passing_score || 80;
  const maxAttempts = Number(settings?.max_attempts || 0);
  const effectiveMaxAttempts = stats?.maximum_attempts ?? (maxAttempts > 0 ? maxAttempts : null);
  const attemptsUsed = stats?.attempts_used ?? 0;
  const attemptsRemaining = stats?.attempts_remaining ?? (effectiveMaxAttempts ? Math.max(effectiveMaxAttempts - attemptsUsed, 0) : null);
  const questionResults = React.useMemo(() => {
    const byQuestion = {};
    (result?.question_results || []).forEach((item) => {
      byQuestion[item.question_id] = item;
    });
    return byQuestion;
  }, [result]);

  React.useEffect(() => {
    let cancelled = false;
    setLoadingStats(true);
    fetchQuizStats(blockId)
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch(() => {
        if (!cancelled) setStats(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingStats(false);
      });
    return () => { cancelled = true; };
  }, [blockId]);

  const handleOptionSelect = (qId, optId) => {
    if (submitted) return;
    setAnswers(prev => ({ ...prev, [qId]: optId }));
  };

  const handleSubmit = async () => {
    // Basic validation: ensure all questions are answered
    if (Object.keys(answers).length < questions.length) {
      alert("Please answer all questions before submitting.");
      return;
    }

    setIsSubmitting(true);
    try {
      const { data } = await api.post(`/api/v1/learner/blocks/${blockId}/quiz/submit`, { answers });
      setResult(data);
      setStats({
        ...(stats || {}),
        maximum_attempts: data.max_attempts,
        max_attempts: data.max_attempts,
        attempts_used: data.attempts_used,
        attempts_remaining: data.attempts_remaining,
        highest_score: data.highest_score,
        latest_score: data.latest_score,
        best_attempt: data.best_attempt,
        attempt_history: data.attempt_history || [],
      });
      setSubmitted(true);
    } catch (err) {
      const detail = err?.response?.data?.detail || "Error submitting quiz.";
      alert(detail);
    }
    setIsSubmitting(false);
  };

  const allAnswered = Object.keys(answers).length === questions.length;
  const attemptsExhausted = attemptsRemaining === 0 && effectiveMaxAttempts !== null && !result?.passed;
  const history = stats?.attempt_history || result?.attempt_history || [];

  return (
    <div style={{ padding: "24px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)", margin: "1em 0" }}>
      <div style={{ fontWeight: 600, fontSize: "20px", marginBottom: "8px", color: "var(--text-primary)", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "12px" }}>
        Quiz
      </div>
      <div style={{ fontSize: "14px", color: "var(--text-muted)", marginBottom: "24px" }}>
        Passing Score: {passingScore}%{maxAttempts > 0 ? ` · Max Attempts: ${maxAttempts}` : " · Unlimited Attempts"}
        {loadingStats ? " · Loading attempts..." : effectiveMaxAttempts ? ` · Attempts Left: ${attemptsRemaining} / ${effectiveMaxAttempts}` : " · Attempts Left: Unlimited"}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {questions.map((q, idx) => {
          const questionResult = questionResults[q.id];
          const isCorrect = Boolean(questionResult?.is_correct);
          const showFeedback = submitted && result;
          
          return (
            <div key={q.id} style={{ 
              padding: "16px", 
              borderRadius: "6px", 
              border: showFeedback ? (isCorrect ? "1px solid var(--success)" : "1px solid var(--error)") : "1px solid var(--border-subtle)",
              background: showFeedback ? (isCorrect ? "var(--success-bg)" : "var(--error-bg)") : "var(--surface-sunken)"
            }}>
              <div style={{ fontWeight: 500, fontSize: "15px", marginBottom: "12px", color: "var(--text-primary)" }}>
                {idx + 1}. {q.text}
                <span style={{ fontSize: "13px", color: "var(--text-muted)", marginLeft: "8px", fontWeight: "normal" }}>({q.points || 10} pts)</span>
              </div>
              
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {(q.options || []).map(opt => {
                  const isSelected = answers[q.id] === opt.id;
                  
                  let optStyle = {
                    display: "flex", alignItems: "center", gap: "8px", padding: "10px", 
                    borderRadius: "4px", border: "1px solid var(--border-subtle)", cursor: submitted ? "default" : "pointer",
                    background: isSelected ? "var(--primary-bg)" : "var(--surface-raised)",
                    borderColor: isSelected ? "var(--border-strong)" : "var(--border-subtle)",
                    transition: "all 0.2s"
                  };

                  if (showFeedback) {
                    if (isSelected && isCorrect) {
                      optStyle.background = "var(--success-bg)";
                      optStyle.borderColor = "var(--success)";
                    } else if (isSelected && !isCorrect) {
                      optStyle.background = "var(--error-bg)";
                      optStyle.borderColor = "var(--error)";
                    }
                  }

                  return (
                    <div 
                      key={opt.id} 
                      style={optStyle}
                      onClick={() => handleOptionSelect(q.id, opt.id)}
                    >
                      <input 
                        type="radio" 
                        name={`q_${q.id}`} 
                        checked={isSelected}
                        onChange={() => {}} // Handle via parent div onClick
                        disabled={submitted}
                        style={{ margin: 0, cursor: submitted ? "default" : "pointer" }}
                      />
                      <span style={{ color: "var(--text-primary)", fontSize: "14px" }}>{opt.text}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid var(--border-subtle)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        {!submitted ? (
          attemptsExhausted ? (
            <div style={{ padding: "10px 14px", color: "var(--error)", background: "var(--error-bg)", border: "1px solid var(--error)", borderRadius: "6px", fontWeight: 500 }}>
              You have reached the maximum number of allowed attempts.
            </div>
          ) : (
          <button
            onClick={handleSubmit}
            disabled={!allAnswered || isSubmitting}
            style={{ 
              padding: "10px 24px", 
              background: (!allAnswered || isSubmitting) ? "var(--surface-sunken)" : "var(--primary)", 
              color: (!allAnswered || isSubmitting) ? "var(--text-muted)" : "#fff", 
              border: "none", 
              borderRadius: "4px", 
              cursor: (!allAnswered || isSubmitting) ? "not-allowed" : "pointer",
              fontWeight: 500
            }}
          >
            {isSubmitting ? "Submitting..." : "Submit Quiz"}
          </button>
          )
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "16px", width: "100%" }}>
            <div style={{ flex: "1 1 auto", minWidth: "200px" }}>
              <div style={{ fontSize: "18px", fontWeight: 600, color: result?.passed ? "var(--success)" : "var(--error)" }}>
                Score: {result?.score}% {result?.passed ? "(Passed)" : "(Failed)"}
              </div>
              <div style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
                {result?.passed ? "Great job! Your score meets the passing requirement." : "You did not meet the passing score requirement."}
                {effectiveMaxAttempts ? ` Attempts remaining: ${attemptsRemaining}.` : ""}
              </div>
            </div>
            {!result?.passed && !attemptsExhausted && (
              <button
                onClick={() => { setAnswers({}); setSubmitted(false); setResult(null); }}
                style={{ padding: "10px 20px", background: "var(--surface-sunken)", border: "1px solid var(--border-subtle)", borderRadius: "6px", cursor: "pointer", fontWeight: 500, flexShrink: 0 }}
              >
                Retake Quiz
              </button>
            )}
            {attemptsExhausted && (
              <div style={{ padding: "10px 14px", color: "var(--error)", background: "var(--error-bg)", border: "1px solid var(--error)", borderRadius: "6px", fontWeight: 500 }}>
                Maximum attempts reached
              </div>
            )}
          </div>
        )}
      </div>
      {history.length > 0 && (
        <div style={{ marginTop: "18px", paddingTop: "16px", borderTop: "1px solid var(--border-subtle)" }}>
          <div style={{ fontWeight: 600, marginBottom: "10px" }}>Attempt History</div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Attempt</th>
                  <th>Date</th>
                  <th style={{ textAlign: "right" }}>Score</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {history.map((attempt) => (
                  <tr key={attempt.attempt_id || attempt.attempt_number}>
                    <td className="mono">{attempt.attempt_number}</td>
                    <td>{attempt.attempt_date ? new Date(attempt.attempt_date).toLocaleString() : "-"}</td>
                    <td className="mono" style={{ textAlign: "right" }}>{Math.round(attempt.score)}%</td>
                    <td>{attempt.status === "passed" ? "Passed" : "Failed"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
