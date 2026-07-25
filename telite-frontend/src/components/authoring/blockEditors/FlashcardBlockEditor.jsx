import React from "react";
import { Button } from "../../common/ui";

export function FlashcardBlockEditor({ block, isLocked, onSettingsChange }) {
  return (
    <div className="block-editor">
      <div className="block-editor__hint">
        <div className="block-editor__hint-title">Flashcards</div>
        <div className="block-editor__hint-text">
          Create interactive two-sided cards for learning and memorization.
        </div>
      </div>

      <div className="block-editor__section">
        <div className="block-editor__section-title">
          Cards ({(block.settings?.cards || []).length})
        </div>

        {(block.settings?.cards || []).map((card, idx) => (
          <div key={card.id} className="block-card">
            <div className="block-card__header">
              <span className="block-card__title">Card {idx + 1}</span>
              <Button
                tone="destructive"
                size="small"
                onClick={() => {
                  const newCards = (block.settings.cards || []).filter((_, i) => i !== idx);
                  onSettingsChange("cards", newCards);
                }}
                disabled={isLocked || (block.settings.cards || []).length <= 1}
              >
                Remove
              </Button>
            </div>
            <div className="block-card__sides">
              <div className="block-card__side">
                <span className="block-card__side-label">Front</span>
                <textarea
                  className="field__input min-h-[90px] resize-vertical"
                  placeholder="Front of card…"
                  value={card.front_text || ""}
                  onChange={(e) => {
                    const newCards = [...(block.settings?.cards || [])];
                    newCards[idx] = { ...newCards[idx], front_text: e.target.value };
                    onSettingsChange("cards", newCards);
                  }}
                  disabled={isLocked}
                />
              </div>
              <div className="block-card__side">
                <span className="block-card__side-label">Back</span>
                <textarea
                  className="field__input min-h-[90px] resize-vertical"
                  placeholder="Back of card…"
                  value={card.back_text || ""}
                  onChange={(e) => {
                    const newCards = [...(block.settings?.cards || [])];
                    newCards[idx] = { ...newCards[idx], back_text: e.target.value };
                    onSettingsChange("cards", newCards);
                  }}
                  disabled={isLocked}
                />
              </div>
            </div>
          </div>
        ))}

        <div>
          <Button
            tone="neutral"
            size="small"
            onClick={() => {
              const newCards = [
                ...(block.settings?.cards || []),
                { id: `card_${Date.now()}`, front_text: "", back_text: "" },
              ];
              onSettingsChange("cards", newCards);
            }}
            disabled={isLocked}
          >
            + Add Card
          </Button>
        </div>
      </div>
    </div>
  );
}
