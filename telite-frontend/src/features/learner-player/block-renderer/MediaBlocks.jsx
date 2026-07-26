import React, { useEffect, useRef, useState } from 'react';
import { api } from "../../../services/client";
import { getEmbedUrl } from "../../../utils/embedUtils";
import { postLearnerEvents } from './events';

export function VideoBlock({ src, courseId, moduleId, blockId }) {
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
    </div>
  );
}

export function AudioBlock({ src }) {
  return (
    <audio
      src={src}
      controls
      style={{ width: "100%", margin: "1em 0" }}
    />
  );
}

export function EmbedBlock({ title, src, sandbox_policy }) {
  if (!src) {
    return (
      <div style={{ padding: "16px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)" }}>
        Embed not configured
      </div>
    );
  }

  const embedSrc = getEmbedUrl(src);

  return (
    <div style={{ margin: "1em 0" }}>
      {title ? <div style={{ fontWeight: 600, marginBottom: "8px" }}>{title}</div> : null}
      <div style={{ position: "relative", width: "100%", paddingBottom: "56.25%", height: 0, overflow: "hidden", borderRadius: "8px", border: "1px solid var(--border-subtle)" }}>
        <iframe
          src={embedSrc}
          title={title || "Embedded content"}
          loading="lazy"
          sandbox={sandbox_policy || "allow-scripts allow-same-origin allow-forms allow-popups"}
          style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", border: "none" }}
          allowFullScreen
        />
      </div>
    </div>
  );
}

export function ScormBlock({ title, src, filename }) {
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

export function H5PBlock({ title, src: _src, filename, courseId, moduleId, blockId, assetId, assetVersion }) {
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

export function PdfBlock({ title, src, filename, blockId, allowDownload = true }) {
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
