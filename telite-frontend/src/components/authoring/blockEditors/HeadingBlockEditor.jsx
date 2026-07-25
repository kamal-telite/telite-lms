import React from "react";

/**
 * HeadingBlockEditor - Editor for heading block type
 *
 * Renders a simple text input for block heading content.
 *
 * @param {Object} props
 * @param {Object} props.block - The block object
 * @param {boolean} props.isLocked - Whether block is locked
 * @param {Function} props.onChange - Callback when content changes (receives new content string)
 * @returns {React.ReactElement}
 */
export function HeadingBlockEditor({ block, isLocked, onChange }) {
  const inputRef = React.useRef(null);
  const content = typeof block.content === "string" ? block.content : "";

  const handleContentChange = (e) => {
    onChange(e.target.value);
  };

  React.useEffect(() => {
    if (!content && inputRef.current) {
      inputRef.current.focus();
    }
  }, [content]);

  return (
    <div className="block-editor">
      <input
        ref={inputRef}
        className="field__input block-heading-input"
        placeholder="Heading title…"
        value={content}
        onChange={handleContentChange}
        disabled={isLocked}
        aria-label="Heading title"
      />
    </div>
  );
}
