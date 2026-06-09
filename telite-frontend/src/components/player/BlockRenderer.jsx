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
    <video 
      src={src} 
      controls 
      style={{ maxWidth: "100%", borderRadius: "8px", margin: "1em 0" }}
      onPlay={() => handleEvent("VIDEO_STARTED")}
      onPause={() => handleEvent("VIDEO_PAUSED")}
      onEnded={() => handleEvent("VIDEO_COMPLETED")}
    />
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
    return (
      <div className="native-block-content" style={{ display: "flex", flexDirection: "column", gap: "1em", fontSize: "16px", lineHeight: 1.6, color: "var(--text)" }}>
        {parsed.map((block) => (
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
    case "pdf":
      return <a href={settings.url} target="_blank" rel="noreferrer">Open PDF</a>;
    case "quiz_reference":
      return <div style={{ padding: "16px", borderRadius: "8px", background: "var(--surface)", border: "1px solid var(--border)" }}>Quiz: {settings.quiz_id || "Not configured"}</div>;
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
