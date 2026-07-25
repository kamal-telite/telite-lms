import React from "react";
import RichTextEditor from "../../authoring/RichTextEditor";

/**
 * TextBlockEditor - Editor for text/paragraph block types
 *
 * Renders a rich text editor for block content.
 *
 * @param {Object} props
 * @param {Object} props.block - The block object
 * @param {boolean} props.isLocked - Whether block is locked
 * @param {Function} props.onChange - Callback when content changes (receives new content string)
 * @returns {React.ReactElement}
 */
export function TextBlockEditor({ block, isLocked, onChange }) {
  const handleContentChange = (newContent) => {
    // RichTextEditor emits an HTML string; coerce safely if a legacy event slips through
    const html =
      typeof newContent === "string"
        ? newContent
        : typeof newContent?.target?.value === "string"
          ? newContent.target.value
          : "";
    onChange(html);
  };

  const content =
    typeof block.content === "string" ? block.content : "";

  return (
    <div className="block-editor">
      <RichTextEditor
        value={content}
        onChange={handleContentChange}
        disabled={isLocked}
      />
    </div>
  );
}
