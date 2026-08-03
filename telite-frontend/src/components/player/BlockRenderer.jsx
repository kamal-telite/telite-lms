import React from 'react';
import { richTextThemeStyles } from '../../features/learner-player/block-renderer/styles';
import { BlockWrapper } from '../../features/learner-player/block-renderer/BlockWrapper';
import { ImageBlock } from '../../features/learner-player/block-renderer/ImageBlock';
import {
  AudioBlock,
  EmbedBlock,
  H5PBlock,
  PdfBlock,
  ScormBlock,
  VideoBlock,
} from '../../features/learner-player/block-renderer/MediaBlocks';
import { AssignmentBlock } from '../../features/learner-player/block-renderer/AssignmentBlock';
import {
  FlashcardBlock,
  PollBlock,
  QuizBlock,
  ResourceCollectionBlock,
} from '../../features/learner-player/block-renderer/InteractiveBlocks';

const contentStyle = {
  display: "flex",
  flexDirection: "column",
  gap: "1em",
  fontSize: "16px",
  lineHeight: 1.6,
  color: "var(--text-primary)",
};

function parseContent(content) {
  if (!content) return { parsed: null };
  if (typeof content !== "string") return { parsed: content };

  try {
    return { parsed: JSON.parse(content) };
  } catch (error) {
    console.error("BlockRenderer: Failed to parse content as JSON", error);
    return { error };
  }
}

function getNativeBlockSettings(block) {
  return block.metadata_json || block.settings || {};
}

function BlockActions({ children }) {
  return children || null;
}

function BlockToolbar({ children }) {
  return children || null;
}

function BlockPreview({ children }) {
  return children || null;
}

function NativeBlockContent({ block, courseId, moduleId }) {
  const settings = getNativeBlockSettings(block);

  switch (block.block_type) {
    case "heading":
      return <h2 style={{ margin: "1em 0 0.5em 0", fontSize: "1.8rem", fontWeight: 600 }}>{block.content}</h2>;
    case "text":
    case "paragraph": {
      const isHtml = /<[a-z][\s\S]*>/i.test(block.content || "");
      if (isHtml) {
        return (
          <div
            className="rich-text-content"
            style={{ color: "var(--text-primary)" }}
            dangerouslySetInnerHTML={{ __html: block.content }}
          />
        );
      }
      return <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{block.content}</p>;
    }
    case "image":
      return <ImageBlock settings={settings} />;
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
      return <EmbedBlock title={block.content} src={settings.url} sandbox_policy={settings.sandbox_policy} />;
    case "assignment":
      return <AssignmentBlock title={block.content} dueDate={settings.due_date} points={settings.points} blockId={block.id} courseId={courseId} moduleId={moduleId} settings={settings} />;
    case "quiz_reference":
      return <div style={{ padding: "16px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)" }}>Quiz: {settings.quiz_title || settings.quiz_id || "Not configured"}</div>;
    default:
      return <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{block.content || ""}</p>;
  }
}

function NativeBlockList({ blocks, courseId, moduleId }) {
  const visibleBlocks = blocks.filter((block) => !block.settings?.hidden);

  return (
    <div className="native-block-content" style={contentStyle}>
      <style>{richTextThemeStyles}</style>
      {visibleBlocks.map((block) => (
        <BlockWrapper key={block.id || block.sort_order} blockId={block.id} courseId={courseId} moduleId={moduleId} blockType={block.block_type}>
          <BlockToolbar />
          <BlockPreview>
            <NativeBlockContent block={block} courseId={courseId} moduleId={moduleId} />
          </BlockPreview>
          <BlockActions />
        </BlockWrapper>
      ))}
    </div>
  );
}

function TipTapContent({ nodes, courseId, moduleId }) {
  return (
    <div className="tiptap-content" style={contentStyle}>
      <style>{richTextThemeStyles}</style>
      {nodes.map((node, index) => (
        <BlockWrapper key={index} blockId={`block_${index}`} courseId={courseId} moduleId={moduleId}>
          <BlockToolbar />
          <BlockPreview>
            <TipTapNode node={node} index={index} courseId={courseId} moduleId={moduleId} />
          </BlockPreview>
          <BlockActions />
        </BlockWrapper>
      ))}
    </div>
  );
}

function TipTapNode({ node, index, courseId, moduleId }) {
  if (!node) return null;

  switch (node.type) {
    case 'paragraph':
      return <p style={{ margin: 0 }}>{renderMarks(node.content, courseId, moduleId)}</p>;
    case 'heading': {
      const level = node.attrs?.level || 2;
      const HeadingTag = `h${level}`;
      const headingStyle = { margin: "1em 0 0.5em 0", fontWeight: 600 };
      if (level === 1) headingStyle.fontSize = "2.25rem";
      else if (level === 2) headingStyle.fontSize = "1.8rem";
      else if (level === 3) headingStyle.fontSize = "1.5rem";

      return <HeadingTag style={headingStyle}>{renderMarks(node.content, courseId, moduleId)}</HeadingTag>;
    }
    case 'bulletList':
      return (
        <ul style={{ paddingLeft: "1.5em", margin: 0 }}>
          {node.content?.map((item, i) => <TipTapNode key={i} node={item} index={i} courseId={courseId} moduleId={moduleId} />)}
        </ul>
      );
    case 'orderedList':
      return (
        <ol style={{ paddingLeft: "1.5em", margin: 0 }}>
          {node.content?.map((item, i) => <TipTapNode key={i} node={item} index={i} courseId={courseId} moduleId={moduleId} />)}
        </ol>
      );
    case 'listItem':
      return <li style={{ marginBottom: "0.25em" }}>{node.content?.map((item, i) => <TipTapNode key={i} node={item} index={i} courseId={courseId} moduleId={moduleId} />)}</li>;
    case 'codeBlock':
      return (
        <pre style={{ background: "var(--surface-sunken)", padding: "16px", borderRadius: "8px", overflowX: "auto", fontFamily: "monospace" }}>
          <code>{renderMarks(node.content, courseId, moduleId)}</code>
        </pre>
      );
    case 'blockquote':
      return (
        <blockquote style={{ borderLeft: "4px solid var(--border)", paddingLeft: "1em", margin: 0, color: "var(--text-muted)", fontStyle: "italic" }}>
          {node.content?.map((item, i) => <TipTapNode key={i} node={item} index={i} courseId={courseId} moduleId={moduleId} />)}
        </blockquote>
      );
    case 'horizontalRule':
      return <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "2em 0" }} />;
    case 'image':
      return <ImageBlock settings={node.attrs || {}} src={node.attrs?.src} alt={node.attrs?.alt || ""} title={node.attrs?.title} />;
    case 'video':
      return <VideoBlock src={node.attrs?.src} courseId={courseId} moduleId={moduleId} blockId={`block_${index}`} />;
    default:
      return renderMarks(node.content, courseId, moduleId);
  }
}

function renderMarks(contentNodes, courseId, moduleId) {
  if (!contentNodes || !Array.isArray(contentNodes)) return null;

  return contentNodes.map((node, index) => {
    if (node.type === 'text') {
      let textElement = node.text;

      if (node.marks) {
        node.marks.forEach((mark) => {
          if (mark.type === 'bold') {
            textElement = <strong key={`b-${index}`}>{textElement}</strong>;
          } else if (mark.type === 'italic') {
            textElement = <em key={`i-${index}`}>{textElement}</em>;
          } else if (mark.type === 'strike') {
            textElement = <s key={`s-${index}`}>{textElement}</s>;
          } else if (mark.type === 'code') {
            textElement = <code key={`c-${index}`} style={{ background: "var(--surface-sunken)", padding: "0.1em 0.3em", borderRadius: "3px", fontFamily: "monospace" }}>{textElement}</code>;
          } else if (mark.type === 'link') {
            textElement = <a key={`l-${index}`} href={mark.attrs?.href} target={mark.attrs?.target || "_blank"} style={{ color: "var(--primary)", textDecoration: "underline" }}>{textElement}</a>;
          }
        });
      }
      return <React.Fragment key={index}>{textElement}</React.Fragment>;
    }

    return <TipTapNode key={index} node={node} index={index} courseId={courseId} moduleId={moduleId} />;
  });
}

function BlockContent({ parsed, courseId, moduleId }) {
  if (Array.isArray(parsed)) {
    return <NativeBlockList blocks={parsed} courseId={courseId} moduleId={moduleId} />;
  }

  if (parsed?.type === "doc" && Array.isArray(parsed.content)) {
    return <TipTapContent nodes={parsed.content} courseId={courseId} moduleId={moduleId} />;
  }

  return <div className="rendered-content">Unsupported content format.</div>;
}

/**
 * BlockRenderer parses and renders TipTap JSON format.
 * Content blocks (e.g. paragraph, heading, codeBlock) are transformed into native React elements.
 */
export function BlockRenderer({ content, courseId, moduleId }) {
  const { parsed, error } = parseContent(content);

  if (!content) return null;
  if (error) return <div className="rendered-content error">Failed to load content.</div>;

  return <BlockContent parsed={parsed} courseId={courseId} moduleId={moduleId} />;
}

export {
  BlockActions,
  BlockContent,
  BlockPreview,
  BlockToolbar,
  BlockWrapper,
  NativeBlockContent,
};
