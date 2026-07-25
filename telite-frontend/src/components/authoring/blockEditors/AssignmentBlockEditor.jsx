import React from "react";

export function AssignmentBlockEditor({ block, isLocked, onContentChange, onSettingsChange }) {
  const handleContentChange = (e) => onContentChange(e.target.value);

  return (
    <div className="block-editor">
      <div className="block-editor__hint">
        <div className="block-editor__hint-title">Assignment</div>
        <div className="block-editor__hint-text">
          Add instructions, due date, and point value for learner submission work.
        </div>
      </div>
      <label className="field">
        <span className="field__label">Title</span>
        <input
          className="field__input"
          placeholder="Assignment title…"
          value={block.content || ""}
          onChange={handleContentChange}
          disabled={isLocked}
        />
      </label>
      <label className="field">
        <span className="field__label">Instructions</span>
        <textarea
          className="field__input min-h-[100px] resize-vertical"
          placeholder="Assignment instructions…"
          value={block.settings?.instructions || ""}
          onChange={(e) => onSettingsChange("instructions", e.target.value)}
          disabled={isLocked}
        />
      </label>
      <div className="block-editor__grid-2">
        <label className="field">
          <span className="field__label">Due date</span>
          <input
            className="field__input"
            type="date"
            value={block.settings?.due_date || ""}
            onChange={(e) => onSettingsChange("due_date", e.target.value)}
            disabled={isLocked}
          />
        </label>
        <label className="field">
          <span className="field__label">Points</span>
          <input
            className="field__input"
            type="number"
            min="0"
            placeholder="Points"
            value={block.settings?.points || ""}
            onChange={(e) => onSettingsChange("points", e.target.value)}
            disabled={isLocked}
          />
        </label>
      </div>
    </div>
  );
}
