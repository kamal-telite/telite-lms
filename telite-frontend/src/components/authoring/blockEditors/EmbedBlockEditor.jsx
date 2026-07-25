import React from "react";

export function EmbedBlockEditor({ block, isLocked, onContentChange, onSettingsChange }) {
  const handleContentChange = (e) => onContentChange(e.target.value);

  return (
    <div className="block-editor">
      <div className="block-editor__hint">
        <div className="block-editor__hint-title">Embedded content</div>
        <div className="block-editor__hint-text">
          Add a URL for an external page, tool, or video embed.
        </div>
      </div>
      <label className="field">
        <span className="field__label">Title</span>
        <input
          className="field__input"
          placeholder="Embed title…"
          value={block.content || ""}
          onChange={handleContentChange}
          disabled={isLocked}
        />
      </label>
      <label className="field">
        <span className="field__label">URL</span>
        <input
          className="field__input"
          placeholder="https://…"
          value={block.settings?.url || ""}
          onChange={(e) => onSettingsChange("url", e.target.value)}
          disabled={isLocked}
        />
      </label>
    </div>
  );
}
