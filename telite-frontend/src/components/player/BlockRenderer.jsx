import React, { useEffect, useRef, useState } from 'react';

// Reusable component to track when a block enters the viewport
function TrackedBlock({ children, blockId, courseId, moduleId }) {
  const ref = useRef(null);
  const [viewed, setViewed] = useState(false);

  useEffect(() => {
    if (!ref.current || viewed || !courseId) return;

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setViewed(true);
        observer.disconnect();

        // Emit BLOCK_VIEWED
        const token = localStorage.getItem("token");
        fetch("/api/v1/learner/events", {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            events: [{
              event_type: "BLOCK_VIEWED",
              course_id: courseId,
              module_id: moduleId,
              ...(Number.isInteger(blockId) ? { block_id: blockId } : {})
            }]
          })
        }).catch(() => {});
      }
    }, { threshold: 0.5 });

    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [viewed, courseId, moduleId, blockId]);

  return <div ref={ref}>{children}</div>;
}

function VideoBlock({ src, courseId, moduleId, blockId }) {
  const title = "Video lesson";

  if (!src) {
    return (
      <div style={{ padding: "16px", borderRadius: "8px", background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
        Video is not configured.
      </div>
    );
  }

  const handleEvent = (eventType) => {
    if (!courseId) return;
    const token = localStorage.getItem("token");
    fetch("/api/v1/learner/events", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        events: [{
          event_type: eventType,
          course_id: courseId,
          module_id: moduleId,
          ...(Number.isInteger(blockId) ? { block_id: blockId } : {})
        }]
      })
    }).catch(() => {});
  };

  return (
    <div style={{ margin: "1em 0" }}>
      <video
        src={src}
        controls
        preload="metadata"
        title={title}
        style={{ width: "100%", maxHeight: "70vh", background: "#0f172a", borderRadius: "8px", display: "block" }}
        onPlay={() => handleEvent("VIDEO_STARTED")}
        onPause={() => handleEvent("VIDEO_PAUSED")}
        onEnded={() => handleEvent("VIDEO_COMPLETED")}
      >
        <a href={src} target="_blank" rel="noreferrer">Open video</a>
      </video>
      <div style={{ marginTop: "8px" }}>
        <a href={src} target="_blank" rel="noreferrer" style={{ color: "var(--brand)", fontWeight: 700 }}>
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
      <div style={{ padding: "16px", borderRadius: "8px", background: "var(--surface)", border: "1px solid var(--border)" }}>
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
        style={{ width: "100%", minHeight: "420px", border: "1px solid var(--border)", borderRadius: "8px" }}
      />
    </div>
  );
}

function ScormBlock({ title, src, filename }) {
  return (
    <div style={{ padding: "16px", borderRadius: "8px", background: "var(--surface)", border: "1px solid var(--border)", margin: "1em 0" }}>
      <div style={{ fontWeight: 700, marginBottom: "6px" }}>{title || "SCORM Package"}</div>
      <div style={{ color: "var(--text-muted)", fontSize: "14px", marginBottom: "12px" }}>
        {filename || "Launch the attached SCORM package."}
      </div>
      {src ? (
        <a href={src} target="_blank" rel="noreferrer" style={{ color: "var(--brand)", fontWeight: 700 }}>
          Launch SCORM
        </a>
      ) : (
        <span style={{ color: "var(--text-muted)" }}>Package not configured</span>
      )}
    </div>
  );
}

function PdfBlock({ title, src, filename }) {
  if (!src) {
    return (
      <div style={{ padding: "16px", borderRadius: "8px", background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
        PDF is not configured.
      </div>
    );
  }

  return (
    <div style={{ margin: "1em 0", border: "1px solid var(--border)", borderRadius: "8px", overflow: "hidden", background: "var(--surface)" }}>
      <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
        <div>
          <div style={{ fontWeight: 700 }}>{title || filename || "PDF Document"}</div>
          {filename ? <div style={{ color: "var(--text-muted)", fontSize: "13px", marginTop: "2px" }}>{filename}</div> : null}
        </div>
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <a href={src} target="_blank" rel="noreferrer" style={{ color: "var(--brand)", fontWeight: 700 }}>Open</a>
          <a href={src} download style={{ color: "var(--brand)", fontWeight: 700 }}>Download</a>
        </div>
      </div>
      <iframe
        src={src}
        title={title || filename || "PDF document"}
        style={{ width: "100%", height: "680px", border: 0, display: "block", background: "#fff" }}
      />
    </div>
  );
}

function AssignmentBlock({ title, settings }) {
  const dueDate = settings?.due_date;
  const points = settings?.points;

  return (
    <div style={{ padding: "18px", borderRadius: "8px", background: "var(--surface)", border: "1px solid var(--border)", margin: "1em 0" }}>
      <div style={{ fontWeight: 700, fontSize: "18px", marginBottom: "8px" }}>
        {title || "Assignment"}
      </div>
      <p style={{ margin: 0, whiteSpace: "pre-wrap", color: "var(--text)" }}>
        {settings?.instructions || "Assignment instructions are not available."}
      </p>
      {(dueDate || points) ? (
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "14px", color: "var(--text-muted)", fontSize: "14px" }}>
          {dueDate ? <span>Due: {dueDate}</span> : null}
          {points ? <span>Points: {points}</span> : null}
        </div>
      ) : null}
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
      <div className="native-block-content" style={{ display: "flex", flexDirection: "column", gap: "1em", fontSize: "16px", lineHeight: 1.6, color: "var(--text)" }}>
        {visibleBlocks.map((block) => (
          <TrackedBlock key={block.id || block.sort_order} blockId={block.id} courseId={courseId} moduleId={moduleId}>
            {renderNativeBlock(block, courseId, moduleId)}
          </TrackedBlock>
        ))}
      </div>
    );
  }

  // TipTap structure: { type: 'doc', content: [ { type: 'paragraph', content: [...] }, ... ] }
  if (parsed.type === "doc" && Array.isArray(parsed.content)) {
    return (
      <div className="tiptap-content" style={{ display: "flex", flexDirection: "column", gap: "1em", fontSize: "16px", lineHeight: 1.6, color: "var(--text)" }}>
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
  const settings = block.settings || {};

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
      return <PdfBlock title={block.content} src={settings.url} filename={settings.filename} />;
    case "scorm":
      return <ScormBlock title={block.content} src={settings.url} filename={settings.filename} />;
    case "embed":
      return <EmbedBlock title={block.content} src={settings.url} />;
    case "assignment":
      return <AssignmentBlock title={block.content} settings={settings} />;
    case "quiz_reference":
      return <div style={{ padding: "16px", borderRadius: "8px", background: "var(--surface)", border: "1px solid var(--border)" }}>Quiz: {settings.quiz_title || settings.quiz_id || "Not configured"}</div>;
    default:
      return <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{block.content || ""}</p>;
  }
}

function renderNode(node, index, courseId, moduleId) {
  if (!node) return null;

  switch (node.type) {
    case 'paragraph':
      return <p style={{ margin: 0 }}>{renderMarks(node.content)}</p>;
    case 'heading':
      const level = node.attrs?.level || 2;
      const HeadingTag = `h${level}`;
      const style = { margin: "1em 0 0.5em 0", fontWeight: 600 };
      if (level === 1) style.fontSize = "2.25rem";
      else if (level === 2) style.fontSize = "1.8rem";
      else if (level === 3) style.fontSize = "1.5rem";
      
      return <HeadingTag style={style}>{renderMarks(node.content)}</HeadingTag>;
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
        <pre style={{ background: "var(--surface-hover)", padding: "16px", borderRadius: "8px", overflowX: "auto", fontFamily: "monospace" }}>
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
            textElement = <code key={`c-${i}`} style={{ background: "var(--surface-hover)", padding: "0.1em 0.3em", borderRadius: "3px", fontFamily: "monospace" }}>{textElement}</code>;
          } else if (mark.type === 'link') {
            textElement = <a key={`l-${i}`} href={mark.attrs?.href} target={mark.attrs?.target || "_blank"} style={{ color: "var(--brand)", textDecoration: "underline" }}>{textElement}</a>;
          }
        });
      }
      return <React.Fragment key={i}>{textElement}</React.Fragment>;
    }
    
    // Nested inline nodes?
    return <React.Fragment key={i}>{renderNode(node, i)}</React.Fragment>;
  });
}
