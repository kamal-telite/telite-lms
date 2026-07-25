import React from "react";
import { Button, Badge } from "../../common/ui";
import QuestionBankPicker from "../QuestionBankPicker";

export function NativeQuizBlockEditor({
  isLocked,
  onSettingsChange,
  settings,
  updateQuizQuestion,
  updateQuizOption,
  addQuizOption,
  removeQuizOption,
  createNativeQuizQuestion,
  bankPickerOpen,
  setBankPickerOpen,
  slug,
  staleQuestions,
}) {
  return (
    <div className="block-editor">
      <div className="block-editor__hint">
        <div className="block-editor__hint-title">Native quiz</div>
        <div className="block-editor__hint-text">
          Questions, scoring, and attempts are stored directly on this quiz block.
        </div>
      </div>

      <div className="block-editor__grid-2">
        <label className="field">
          <span className="field__label">Passing score (%)</span>
          <input
            className="field__input"
            type="number"
            min="0"
            max="100"
            value={settings.passing_score ?? 80}
            onChange={(e) => onSettingsChange("passing_score", Number(e.target.value))}
            disabled={isLocked}
          />
        </label>
        <label className="field">
          <span className="field__label">Maximum attempts</span>
          <select
            className="field__input"
            value={Number(settings.max_attempts || 0) === 0 ? "unlimited" : String(settings.max_attempts)}
            onChange={(e) => onSettingsChange("max_attempts", e.target.value === "unlimited" ? 0 : Number(e.target.value))}
            disabled={isLocked}
          >
            <option value="unlimited">Unlimited</option>
            {[1, 2, 3, 5].map((value) => <option key={value} value={value}>{value}</option>)}
            {Number(settings.max_attempts || 0) > 0 && ![1, 2, 3, 5].includes(Number(settings.max_attempts)) ? (
              <option value={settings.max_attempts}>{settings.max_attempts}</option>
            ) : null}
          </select>
        </label>
      </div>

      {(settings.questions || []).map((question, qIndex) => (
        <div key={question.id} className="block-card">
          <div className="block-card__header">
            <strong className="block-card__title" style={{ color: "var(--color-text-primary)", fontSize: 13 }}>
              Question {qIndex + 1}
            </strong>
            <Button
              tone="destructive"
              size="small"
              disabled={isLocked || (settings.questions || []).length <= 1}
              onClick={() => onSettingsChange("questions", (settings.questions || []).filter((_, idx) => idx !== qIndex))}
            >
              Remove
            </Button>
          </div>

          {question.type === "bank_reference" ? (
            <div className="block-editor__section" style={{ padding: 10 }}>
              <div className="block-card__header" style={{ alignItems: "flex-start" }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 550, marginBottom: 6 }}>
                    {question.snapshot?.question_text || `Question Bank Reference #${question.question_id}`}
                  </div>
                  <div className="block-editor__meta" style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
                    {question.snapshot?.question_type ? <span>Type: {question.snapshot.question_type}</span> : null}
                    {question.snapshot?.points ? <span>Points: {question.snapshot.points}</span> : null}
                  </div>
                  {staleQuestions[question.question_id]?.is_stale && (
                    <div className="block-editor__meta" style={{ marginTop: 8, color: "var(--warning)" }}>
                      Newer version available (v{staleQuestions[question.question_id].latest_version_id})
                    </div>
                  )}
                </div>
                <Badge tone="accent">Bank Ref v{question.version_id}</Badge>
              </div>
            </div>
          ) : (
            <>
              <label className="field">
                <span className="field__label">Question text</span>
                <textarea
                  className="field__input min-h-[70px] resize-vertical"
                  placeholder="Question text…"
                  value={question.text || ""}
                  onChange={(e) => updateQuizQuestion(qIndex, { text: e.target.value })}
                  disabled={isLocked}
                />
              </label>
              <label className="field">
                <span className="field__label">Points</span>
                <input
                  className="field__input"
                  type="number"
                  min="1"
                  value={question.points ?? 10}
                  onChange={(e) => updateQuizQuestion(qIndex, { points: Number(e.target.value) })}
                  disabled={isLocked}
                />
              </label>
              <div className="block-editor" style={{ gap: 8 }}>
                <div className="block-editor__section-title">Options</div>
                {(question.options || []).map((option, optionIndex) => (
                  <div key={option.id} className="block-editor__row" style={{ flexWrap: "nowrap" }}>
                    <input
                      type="radio"
                      name={`correct-${question.id}`}
                      checked={question.correct_option_id === option.id}
                      onChange={() => updateQuizQuestion(qIndex, { correct_option_id: option.id })}
                      disabled={isLocked}
                      aria-label={`Mark option ${optionIndex + 1} correct`}
                      style={{ flexShrink: 0 }}
                    />
                    <input
                      className="field__input"
                      style={{ flex: 1, minWidth: 0 }}
                      placeholder={`Option ${optionIndex + 1}`}
                      value={option.text || ""}
                      onChange={(e) => updateQuizOption(qIndex, optionIndex, e.target.value)}
                      disabled={isLocked}
                    />
                    <Button
                      tone="destructive"
                      size="small"
                      disabled={isLocked || (question.options || []).length <= 2}
                      onClick={() => removeQuizOption(qIndex, optionIndex)}
                    >
                      Remove
                    </Button>
                  </div>
                ))}
                <div>
                  <Button tone="neutral" size="small" disabled={isLocked} onClick={() => addQuizOption(qIndex)}>
                    + Add Option
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      ))}

      <div className="split-actions justify-start">
        <Button tone="neutral" disabled={isLocked} onClick={() => onSettingsChange("questions", [...(settings.questions || []), createNativeQuizQuestion()])}>
          + Add Native Question
        </Button>
        <Button tone="primary" disabled={isLocked} onClick={() => setBankPickerOpen(true)}>
          + Import from Bank
        </Button>
      </div>

      <QuestionBankPicker
        open={bankPickerOpen}
        onClose={() => setBankPickerOpen(false)}
        slug={slug}
        onImport={(references) => onSettingsChange("questions", [...(settings.questions || []), ...references])}
      />
    </div>
  );
}
