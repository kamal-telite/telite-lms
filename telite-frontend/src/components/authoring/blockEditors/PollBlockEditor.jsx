import React from "react";
import { Button } from "../../common/ui";

export function PollBlockEditor({ block, isLocked, onSettingsChange }) {
  return (
    <div className="block-editor">
      <div className="block-editor__hint">
        <div className="block-editor__hint-title">Poll</div>
        <div className="block-editor__hint-text">Ask a question and gather feedback.</div>
      </div>

      <label className="field">
        <span className="field__label">Question</span>
        <textarea
          className="field__input min-h-[80px] resize-vertical"
          placeholder="What would you like to ask?"
          value={block.settings?.question || ""}
          onChange={(e) => onSettingsChange("question", e.target.value)}
          disabled={isLocked}
        />
      </label>

      <div className="block-editor__section">
        <div className="block-editor__section-title">Options</div>
        {(block.settings?.options || []).map((opt, idx) => (
          <div key={opt.id} className="block-editor__row">
            <input
              className="field__input"
              style={{ flex: 1, minWidth: 0 }}
              placeholder={`Option ${idx + 1}`}
              value={opt.text}
              onChange={(e) => {
                const newOpts = [...(block.settings.options || [])];
                newOpts[idx] = { ...newOpts[idx], text: e.target.value };
                onSettingsChange("options", newOpts);
              }}
              disabled={isLocked}
            />
            <Button
              tone="destructive"
              size="small"
              onClick={() => {
                const newOpts = (block.settings.options || []).filter((_, i) => i !== idx);
                onSettingsChange("options", newOpts);
              }}
              disabled={isLocked || (block.settings.options || []).length <= 1}
            >
              Remove
            </Button>
          </div>
        ))}
        <div>
          <Button
            tone="neutral"
            size="small"
            onClick={() => {
              const newOpts = [...(block.settings?.options || []), { id: `opt_${Date.now()}`, text: "" }];
              onSettingsChange("options", newOpts);
            }}
            disabled={isLocked}
          >
            + Add Option
          </Button>
        </div>
      </div>

      <div className="block-editor__checks">
        <label className="block-check">
          <input
            type="checkbox"
            checked={block.settings?.allow_multiple || false}
            onChange={(e) => onSettingsChange("allow_multiple", e.target.checked)}
            disabled={isLocked}
          />
          Allow multiple selections
        </label>

        <label className="block-check">
          <input
            type="checkbox"
            checked={block.settings?.anonymous_voting || false}
            onChange={(e) => onSettingsChange("anonymous_voting", e.target.checked)}
            disabled={isLocked}
          />
          Anonymous voting
        </label>

        <label className="block-check">
          <input
            type="checkbox"
            checked={block.settings?.allow_vote_change || false}
            onChange={(e) => onSettingsChange("allow_vote_change", e.target.checked)}
            disabled={isLocked}
          />
          Allow vote change
        </label>

        <label className="field m-0">
          <span className="field__label">Result visibility</span>
          <select
            className="field__input"
            value={block.settings?.show_results || "after_vote"}
            onChange={(e) => onSettingsChange("show_results", e.target.value)}
            disabled={isLocked}
          >
            <option value="always">Always show</option>
            <option value="after_vote">After voting</option>
            <option value="never">Never show</option>
          </select>
        </label>
      </div>
    </div>
  );
}
