import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Button, IconButton, Badge, LoadingState, Modal, useToast } from "../../components/common/ui";
import { api, getErrorMessage } from "../../services/client";
import { useAutosave } from "../../hooks/useAutosave";
import { validateBlocks } from "../../services/validationEngine";
import { MediaLibrary } from "./MediaLibrary";
import QuestionBankPicker from "../../components/authoring/QuestionBankPicker";
import { useParams } from "react-router-dom";
import { checkStaleQuestions } from "../../services/client";

function blockKey(block) {
  return block.id || block._tempId;
}

function createNativeQuizQuestion() {
  const suffix = `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  const questionId = `q_${suffix}`;
  const optionA = `opt_${suffix}_1`;
  const optionB = `opt_${suffix}_2`;
  return {
    id: questionId,
    text: "",
    points: 10,
    options: [
      { id: optionA, text: "" },
      { id: optionB, text: "" },
    ],
    correct_option_id: optionA,
  };
}

// Sortable Block Component
function SortableBlock({
  block,
  isSelected,
  isHighlighted,
  onSelect,
  onChange,
  onDelete,
  onDuplicate,
  onOpenMedia,
  onOpenInspector,
  quizOptions = [],
  quizLoading = false,
  quizError = null,
  slug,
}) {
  const [bankPickerOpen, setBankPickerOpen] = useState(false);
  const [staleQuestions, setStaleQuestions] = useState({});
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: `block-${blockKey(block)}` });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    ...(isDragging ? { zIndex: 1 } : {}),
  };

  const settings = block.settings || {};
  const isLocked = Boolean(block.settings?.locked);

  // Stale questions check
  useEffect(() => {
    if (block.block_type === "quiz" && block.settings?.questions?.length > 0) {
      const bankRefs = block.settings.questions
        .filter(q => q.type === "bank_reference" && q.question_id && q.version_id)
        .map(q => ({ question_id: q.question_id, version_id: q.version_id }));
        
      if (bankRefs.length > 0) {
        checkStaleQuestions(bankRefs).then(data => {
          setStaleQuestions(data);
        }).catch(err => console.error("Failed to check stale questions", err));
      }
    }
  }, [block.block_type, block.settings?.questions]);

  const className = `builder-block ${isSelected ? "builder-block--selected" : ""} ${isDragging ? "builder-block--dragging" : ""} ${isHighlighted ? "builder-block--highlight" : ""}`;

  const handleContentChange = (e) => {
    onChange(blockKey(block), { content: e.target.value });
  };

  const handleSettingsChange = (key, value) => {
    onChange(blockKey(block), { settings: { ...settings, [key]: value } });
  };

  const handleQuizChange = (event) => {
    const selectedQuiz = quizOptions.find((quiz) => String(quiz.id) === event.target.value);
    onChange(blockKey(block), {
      settings: {
        ...settings,
        quiz_id: event.target.value ? Number(event.target.value) : "",
        quiz_title: selectedQuiz?.title || "",
        quiz_module_id: selectedQuiz?.module_id || null,
      },
    });
  };

  const updateQuizQuestion = (questionIndex, updates) => {
    const questions = [...(settings.questions || [])];
    questions[questionIndex] = { ...questions[questionIndex], ...updates };
    handleSettingsChange("questions", questions);
  };

  const updateQuizOption = (questionIndex, optionIndex, text) => {
    const questions = [...(settings.questions || [])];
    const question = { ...questions[questionIndex] };
    const options = [...(question.options || [])];
    options[optionIndex] = { ...options[optionIndex], text };
    question.options = options;
    questions[questionIndex] = question;
    handleSettingsChange("questions", questions);
  };

  const addQuizOption = (questionIndex) => {
    const questions = [...(settings.questions || [])];
    const question = { ...questions[questionIndex] };
    const optionId = `opt_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    question.options = [...(question.options || []), { id: optionId, text: "" }];
    questions[questionIndex] = question;
    handleSettingsChange("questions", questions);
  };

  const removeQuizOption = (questionIndex, optionIndex) => {
    const questions = [...(settings.questions || [])];
    const question = { ...questions[questionIndex] };
    const removedOption = question.options?.[optionIndex];
    const options = (question.options || []).filter((_, idx) => idx !== optionIndex);
    question.options = options;
    if (removedOption?.id === question.correct_option_id) {
      question.correct_option_id = options[0]?.id || "";
    }
    questions[questionIndex] = question;
    handleSettingsChange("questions", questions);
  };

  const inputRef = React.useRef(null);

  const handleContainerClick = (e) => {
    onSelect(block);
    const targetTag = e.target.tagName.toLowerCase();
    if (targetTag !== 'input' && targetTag !== 'textarea' && targetTag !== 'button' && targetTag !== 'svg' && targetTag !== 'path') {
      inputRef.current?.focus();
    }
  };

  return (
    <div 
      id={`editor-block-${blockKey(block)}`} 
      ref={setNodeRef} 
      style={style} 
      className={className} 
      onClick={handleContainerClick}
      onDoubleClick={() => {
        onSelect(block);
        if (onOpenInspector) onOpenInspector();
      }}
    >
      <div className="builder-block__header">
        <div 
          {...attributes} 
          {...listeners} 
          className="builder-block__drag"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="9" cy="5" r="1" />
            <circle cx="9" cy="12" r="1" />
            <circle cx="9" cy="19" r="1" />
            <circle cx="15" cy="5" r="1" />
            <circle cx="15" cy="12" r="1" />
            <circle cx="15" cy="19" r="1" />
          </svg>
          <Badge tone="neutral">{block.block_type.toUpperCase()}</Badge>
          {settings.hidden ? <Badge tone="warning">Hidden</Badge> : null}
          {isLocked ? <Badge tone="danger">Locked</Badge> : null}
        </div>
        <div className="builder-block__actions">
          <IconButton
            icon="settings"
            size="small"
            label="Block Settings"
            onClick={(event) => {
              event.stopPropagation();
              onSelect(block);
              if (onOpenInspector) onOpenInspector();
            }}
          />
          <IconButton
            icon="copy"
            size="small"
            label="Duplicate block"
            onClick={(event) => {
              event.stopPropagation();
              onDuplicate(blockKey(block));
            }}
          />
          <IconButton
            icon="trash"
            size="small"
            label="Delete block"
            disabled={isLocked}
            onClick={(event) => {
              event.stopPropagation();
              onDelete(blockKey(block));
            }}
          />
        </div>
      </div>

      <div style={{ paddingLeft: "24px" }}>
        {block.block_type === "heading" && (
          <input
            ref={inputRef}
            className="field__input"
            style={{ fontSize: "20px", fontWeight: 600, padding: "12px", border: "none", borderBottom: "2px solid var(--border-subtle)", borderRadius: 0 }}
            placeholder="Heading Title..."
            value={block.content || ""}
            onChange={handleContentChange}
            disabled={isLocked}
          />
        )}

        {(block.block_type === "text" || block.block_type === "paragraph") && (
          <textarea
            ref={inputRef}
            className="field__input"
            style={{ minHeight: "100px", resize: "vertical" }}
            placeholder="Enter text content..."
            value={block.content || ""}
            onChange={handleContentChange}
            disabled={isLocked}
          />
        )}

        {(block.block_type === "image" || block.block_type === "video" || block.block_type === "audio" || block.block_type === "pdf" || block.block_type === "scorm" || block.block_type === "h5p") && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ background: "var(--surface-sunken)", padding: "32px", textAlign: "center", borderRadius: "6px", border: "1px dashed var(--border-subtle)" }}>
              {block.media_asset_id || block.settings?.asset_id ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", alignItems: "center" }}>
                  <div style={{ color: "var(--success)", fontWeight: 500 }}>Media Attached</div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)", wordBreak: "break-all" }}>
                    {block.settings?.filename || `Asset #${block.media_asset_id || block.settings?.asset_id}`}
                  </div>
                  <Button tone="neutral" size="small" disabled={isLocked} onClick={() => onOpenMedia(blockKey(block), block.block_type.split("/")[0])}>Replace Media</Button>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px", alignItems: "center" }}>
                  <div style={{ color: "var(--text-secondary)" }}>No media selected</div>
                  <Button tone="primary" disabled={isLocked} onClick={() => onOpenMedia(blockKey(block), block.block_type.split("/")[0])}>Browse Library</Button>
                </div>
              )}
            </div>

            {block.block_type === "scorm" ? (
              <div style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                Attach a SCORM ZIP package from the Media Library.
              </div>
            ) : block.block_type === "h5p" ? (
              <div style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                Attach an H5P file (.h5p) from the Media Library.
              </div>
            ) : null}
          </div>
        )}

        {block.block_type === "embed" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ background: "var(--primary-bg)", padding: "16px", borderRadius: "6px", border: "1px solid var(--border-strong)" }}>
              <strong>Embedded Content</strong>
              <div style={{ marginTop: "4px", color: "var(--primary)", fontSize: "13px" }}>
                Add a URL for an external page, tool, or video embed.
              </div>
            </div>
            <input
              ref={inputRef}
              className="field__input"
              placeholder="Embed title..."
              value={block.content || ""}
              onChange={handleContentChange}
              disabled={isLocked}
            />
            <input
              className="field__input"
              placeholder="https://..."
              value={block.settings?.url || ""}
              onChange={(e) => handleSettingsChange("url", e.target.value)}
              disabled={isLocked}
            />
          </div>
        )}

        {block.block_type === "assignment" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ background: "var(--warning-bg)", padding: "16px", borderRadius: "6px", border: "1px solid var(--warning)" }}>
              <strong>Assignment</strong>
              <div style={{ marginTop: "4px", color: "var(--warning)", fontSize: "13px" }}>
                Add instructions, due date, and point value for learner submission work.
              </div>
            </div>
            <input
              ref={inputRef}
              className="field__input"
              placeholder="Assignment title..."
              value={block.content || ""}
              onChange={handleContentChange}
              disabled={isLocked}
            />
            <textarea
              className="field__input"
              style={{ minHeight: "100px", resize: "vertical" }}
              placeholder="Assignment instructions..."
              value={block.settings?.instructions || ""}
              onChange={(e) => handleSettingsChange("instructions", e.target.value)}
              disabled={isLocked}
            />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <input
                className="field__input"
                type="date"
                value={block.settings?.due_date || ""}
                onChange={(e) => handleSettingsChange("due_date", e.target.value)}
                disabled={isLocked}
              />
              <input
                className="field__input"
                type="number"
                min="0"
                placeholder="Points"
                value={block.settings?.points || ""}
                onChange={(e) => handleSettingsChange("points", e.target.value)}
                disabled={isLocked}
              />
            </div>
          </div>
        )}

        {block.block_type === "poll" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ background: "var(--surface-sunken)", padding: "16px", borderRadius: "6px", border: "1px solid var(--border-strong)" }}>
              <strong>Poll</strong>
              <div style={{ marginTop: "4px", color: "var(--text-secondary)", fontSize: "13px" }}>
                Ask a question and gather feedback.
              </div>
            </div>
            <textarea
              ref={inputRef}
              className="field__input"
              style={{ minHeight: "80px", resize: "vertical" }}
              placeholder="What would you like to ask?"
              value={block.settings?.question || ""}
              onChange={(e) => handleSettingsChange("question", e.target.value)}
              disabled={isLocked}
            />
            
            <div style={{ padding: "12px", border: "1px solid var(--border-subtle)", borderRadius: "6px" }}>
              <div style={{ fontWeight: 500, marginBottom: "8px", fontSize: "14px" }}>Options</div>
              {(block.settings?.options || []).map((opt, idx) => (
                <div key={opt.id} style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
                  <input
                    className="field__input"
                    placeholder={`Option ${idx + 1}`}
                    value={opt.text}
                    onChange={(e) => {
                      const newOpts = [...(block.settings.options || [])];
                      newOpts[idx].text = e.target.value;
                      handleSettingsChange("options", newOpts);
                    }}
                    disabled={isLocked}
                  />
                  <Button 
                    tone="destructive" 
                    size="small"
                    onClick={() => {
                      const newOpts = block.settings.options.filter((_, i) => i !== idx);
                      handleSettingsChange("options", newOpts);
                    }}
                    disabled={isLocked || (block.settings.options || []).length <= 1}
                  >
                    Remove
                  </Button>
                </div>
              ))}
              <Button 
                tone="neutral" 
                size="small" 
                onClick={() => {
                  const newOpts = [...(block.settings?.options || []), { id: `opt_${Date.now()}`, text: "" }];
                  handleSettingsChange("options", newOpts);
                }}
                disabled={isLocked}
              >
                + Add Option
              </Button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <label className="field" style={{ display: "flex", alignItems: "center", gap: "8px", flexDirection: "row", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={block.settings?.allow_multiple || false}
                  onChange={(e) => handleSettingsChange("allow_multiple", e.target.checked)}
                  disabled={isLocked}
                  style={{ width: "auto", margin: 0 }}
                />
                <span className="field__label" style={{ margin: 0 }}>Allow multiple selections</span>
              </label>

              <label className="field" style={{ display: "flex", alignItems: "center", gap: "8px", flexDirection: "row", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={block.settings?.anonymous_voting || false}
                  onChange={(e) => handleSettingsChange("anonymous_voting", e.target.checked)}
                  disabled={isLocked}
                  style={{ width: "auto", margin: 0 }}
                />
                <span className="field__label" style={{ margin: 0 }}>Anonymous voting</span>
              </label>

              <label className="field" style={{ display: "flex", alignItems: "center", gap: "8px", flexDirection: "row", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={block.settings?.allow_vote_change || false}
                  onChange={(e) => handleSettingsChange("allow_vote_change", e.target.checked)}
                  disabled={isLocked}
                  style={{ width: "auto", margin: 0 }}
                />
                <span className="field__label" style={{ margin: 0 }}>Allow vote change</span>
              </label>

              <label className="field" style={{ margin: 0 }}>
                <span className="field__label">Result Visibility</span>
                <select
                  className="field__input"
                  value={block.settings?.show_results || "after_vote"}
                  onChange={(e) => handleSettingsChange("show_results", e.target.value)}
                  disabled={isLocked}
                >
                  <option value="always">Always show</option>
                  <option value="after_vote">After voting</option>
                  <option value="never">Never show</option>
                </select>
              </label>
            </div>
          </div>
        )}

        {block.block_type === "flashcard" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ background: "var(--primary-bg)", padding: "16px", borderRadius: "6px", border: "1px solid var(--border-strong)" }}>
              <strong>Flashcards</strong>
              <div style={{ marginTop: "4px", color: "var(--primary)", fontSize: "13px" }}>
                Create interactive two-sided cards for learning and memorization.
              </div>
            </div>
            
            <div style={{ padding: "12px", border: "1px solid var(--border-subtle)", borderRadius: "6px", display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ fontWeight: 500, fontSize: "14px" }}>Cards</div>
              {(block.settings?.cards || []).map((card, idx) => (
                <div key={card.id} style={{ display: "flex", flexDirection: "column", gap: "8px", padding: "12px", background: "var(--surface-sunken)", border: "1px solid var(--border-subtle)", borderRadius: "6px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontWeight: 600, fontSize: "13px", color: "var(--text-secondary)" }}>
                    Card {idx + 1}
                    <Button 
                      tone="destructive" 
                      size="small"
                      onClick={() => {
                        const newCards = block.settings.cards.filter((_, i) => i !== idx);
                        handleSettingsChange("cards", newCards);
                      }}
                      disabled={isLocked || (block.settings.cards || []).length <= 1}
                    >
                      Remove
                    </Button>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <textarea
                      className="field__input"
                      style={{ minHeight: "90px", resize: "vertical" }}
                      placeholder="Front of card"
                      value={card.front_text || ""}
                      onChange={(e) => {
                        const newCards = [...(block.settings?.cards || [])];
                        newCards[idx] = { ...newCards[idx], front_text: e.target.value };
                        handleSettingsChange("cards", newCards);
                      }}
                      disabled={isLocked}
                    />
                    <textarea
                      className="field__input"
                      style={{ minHeight: "90px", resize: "vertical" }}
                      placeholder="Back of card"
                      value={card.back_text || ""}
                      onChange={(e) => {
                        const newCards = [...(block.settings?.cards || [])];
                        newCards[idx] = { ...newCards[idx], back_text: e.target.value };
                        handleSettingsChange("cards", newCards);
                      }}
                      disabled={isLocked}
                    />
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
                    handleSettingsChange("cards", newCards);
                  }}
                  disabled={isLocked}
                >
                  + Add Card
                </Button>
              </div>
            </div>
          </div>
        )}

        {block.block_type === "quiz_reference" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ background: "var(--success-bg)", padding: "16px", borderRadius: "6px", border: "1px solid var(--success)" }}>
              <strong>Quiz Reference</strong>
              <div style={{ marginTop: "4px", color: "var(--success)", fontSize: "13px" }}>
                Link this lesson block to a quiz module in this course.
              </div>
            </div>
            <select
              className="field__input"
              value={block.settings?.quiz_id || ""}
              onChange={handleQuizChange}
              disabled={isLocked || quizLoading || quizOptions.length === 0}
            >
              <option value="">
                {quizLoading ? "Loading quizzes..." : quizOptions.length ? "Select a quiz..." : "No quiz modules available"}
              </option>
              {quizOptions.map((quiz) => (
                <option key={quiz.id} value={quiz.id}>
                  {quiz.title} ({quiz.module_title})
                </option>
              ))}
            </select>
            {quizError ? (
              <div style={{ color: "var(--error)", fontSize: "13px" }}>{quizError}</div>
            ) : null}
            {!quizLoading && !quizError && quizOptions.length === 0 ? (
              <div style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                Create a module with type &quot;Quiz&quot; first, then return here to attach it.
              </div>
            ) : null}
          </div>
        )}

        {block.block_type === "quiz" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ background: "var(--primary-bg)", padding: "16px", borderRadius: "6px", border: "1px solid var(--border-strong)" }}>
              <strong>Native Quiz</strong>
              <div style={{ marginTop: "4px", color: "var(--primary)", fontSize: "13px" }}>
                Questions, scoring, and attempts are stored directly on this quiz block.
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <label className="field">
                <span className="field__label">Passing Score (%)</span>
                <input
                  className="field__input"
                  type="number"
                  min="0"
                  max="100"
                  value={settings.passing_score ?? 80}
                  onChange={(e) => handleSettingsChange("passing_score", Number(e.target.value))}
                  disabled={isLocked}
                />
              </label>
              <label className="field">
                <span className="field__label">Max Attempts (0 = infinite)</span>
                <input
                  className="field__input"
                  type="number"
                  min="0"
                  value={settings.max_attempts ?? 3}
                  onChange={(e) => handleSettingsChange("max_attempts", Number(e.target.value))}
                  disabled={isLocked}
                />
              </label>
            </div>

            {(settings.questions || []).map((question, qIndex) => (
              <div key={question.id} style={{ padding: "14px", border: "1px solid var(--border-subtle)", borderRadius: "8px", background: "var(--surface-sunken)", display: "flex", flexDirection: "column", gap: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px" }}>
                  <strong style={{ color: "var(--text-primary)" }}>Question {qIndex + 1}</strong>
                  <Button
                    tone="destructive"
                    size="small"
                    disabled={isLocked || (settings.questions || []).length <= 1}
                    onClick={() => handleSettingsChange("questions", (settings.questions || []).filter((_, idx) => idx !== qIndex))}
                  >
                    Remove
                  </Button>
                </div>

                {question.type === "bank_reference" ? (
                  <div style={{ padding: 12, background: "var(--surface-base)", border: "1px solid var(--border-subtle)", borderRadius: 4 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div style={{ flex: 1, paddingRight: 16 }}>
                        <div style={{ fontWeight: 500, marginBottom: 8 }}>
                          {question.snapshot?.question_text || `Question Bank Reference #${question.question_id}`}
                        </div>
                        <div style={{ display: "flex", gap: 12, fontSize: 13, color: "var(--text-secondary)" }}>
                          {question.snapshot?.question_type ? <span>Type: {question.snapshot.question_type}</span> : null}
                          {question.snapshot?.points ? <span>Points: {question.snapshot.points}</span> : null}
                        </div>
                        {staleQuestions[question.question_id]?.is_stale && (
                          <div style={{ marginTop: 8, display: "inline-flex", alignItems: "center", gap: 6, color: "var(--color-warn)", fontSize: 13 }}>
                            <span className="icon">⚠️</span>
                            Newer version available (v{staleQuestions[question.question_id].latest_version_id})
                          </div>
                        )}
                      </div>
                      <Badge tone="accent">Bank Ref v{question.version_id}</Badge>
                    </div>
                  </div>
                ) : (
                  <>
                    <textarea
                      className="field__input"
                      style={{ minHeight: "70px", resize: "vertical" }}
                      placeholder="Question text..."
                      value={question.text || ""}
                      onChange={(e) => updateQuizQuestion(qIndex, { text: e.target.value })}
                      disabled={isLocked}
                    />
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
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {(question.options || []).map((option, optionIndex) => (
                        <div key={option.id} style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: "8px", alignItems: "center" }}>
                          <input
                            type="radio"
                            name={`correct-${question.id}`}
                            checked={question.correct_option_id === option.id}
                            onChange={() => updateQuizQuestion(qIndex, { correct_option_id: option.id })}
                            disabled={isLocked}
                            aria-label={`Mark option ${optionIndex + 1} correct`}
                          />
                          <input
                            className="field__input"
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
                      <Button tone="neutral" size="small" disabled={isLocked} onClick={() => addQuizOption(qIndex)}>
                        + Add Option
                      </Button>
                    </div>
                  </>
                )}
              </div>
            ))}

            <div className="split-actions" style={{ justifyContent: "flex-start" }}>
              <Button
                tone="neutral"
                disabled={isLocked}
                onClick={() => handleSettingsChange("questions", [...(settings.questions || []), createNativeQuizQuestion()])}
              >
                + Add Native Question
              </Button>
              <Button
                tone="primary"
                disabled={isLocked}
                onClick={() => setBankPickerOpen(true)}
              >
                + Import from Bank
              </Button>
            </div>
            <QuestionBankPicker 
              open={bankPickerOpen} 
              onClose={() => setBankPickerOpen(false)} 
              slug={slug}
              onImport={(references) => {
                handleSettingsChange("questions", [...(settings.questions || []), ...references]);
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}


export function LessonBlockEditor({
  courseId,
  moduleId,
  moduleType = "page",
  activeBlock,
  highlightBlockId,
  onHighlightClear,
  onActiveBlockChange,
  onOpenInspector,
  onRegisterBlockSettingsUpdater,
  onSaveStateChange,
}) {
  const { showToast } = useToast();
  const { slug } = useParams();
  const [blocks, setBlocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [mediaModalOpen, setMediaModalOpen] = useState(false);
  const [activeMediaBlockId, setActiveMediaBlockId] = useState(null);
  const [mediaFilterType, setMediaFilterType] = useState(null);
  const [quizOptions] = useState([]);
  const [quizLoading] = useState(false);
  const [quizError] = useState(null);
  const [conflictInfo, setConflictInfo] = useState(null);
  const [validationErrors, setValidationErrors] = useState({});

  // Initialize sensors for dnd-kit
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const fetchBlocks = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/authoring/courses/${courseId}/modules/${moduleId}/blocks`);
      setBlocks(data.blocks || []);
      const errMap = data.errors ? validateBlocks(data.blocks) : {};
      setValidationErrors(errMap);
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to load blocks."), "error");
    } finally {
      setLoading(false);
    }
  }, [courseId, moduleId, showToast]);

  useEffect(() => {
    fetchBlocks();
  }, [fetchBlocks]);

  useEffect(() => {
    if (highlightBlockId && !loading) {
      const blockElement = document.getElementById(`editor-block-${highlightBlockId}`);
      if (blockElement) {
        blockElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Select the block too
        const blockToSelect = blocks.find((b) => blockKey(b) === highlightBlockId);
        if (blockToSelect && (!activeBlock || blockKey(activeBlock) !== highlightBlockId)) {
          onActiveBlockChange(blockToSelect);
        }
        
        // Add a temporary highlight effect
        blockElement.style.transition = "box-shadow 0.3s ease-in-out";
        blockElement.style.boxShadow = "0 0 0 4px rgba(239, 68, 68, 0.4)";
        setTimeout(() => {
          blockElement.style.boxShadow = "";
          if (onHighlightClear) onHighlightClear();
        }, 2000);
      }
    }
  }, [highlightBlockId, loading, blocks, activeBlock, onActiveBlockChange, onHighlightClear]);

  useEffect(() => {
    if (!moduleId) {
      setBlocks([]);
    }
    onActiveBlockChange?.(null);
  }, [moduleId, onActiveBlockChange]);

  useEffect(() => {
    if (!onRegisterBlockSettingsUpdater) return undefined;

    onRegisterBlockSettingsUpdater((idOrTempId, key, value) => {
      setBlocks((current) =>
        current.map((block) =>
          blockKey(block) === idOrTempId
            ? { ...block, settings: { ...(block.settings || {}), [key]: value } }
            : block
        )
      );
    });

    return () => onRegisterBlockSettingsUpdater(null);
  }, [onRegisterBlockSettingsUpdater]);

  useEffect(() => {
    if (!activeBlock) return;
    const latest = blocks.find((block) => blockKey(block) === blockKey(activeBlock));
    if (latest && latest !== activeBlock) {
      onActiveBlockChange?.(latest);
    }
  }, [blocks, activeBlock, onActiveBlockChange]);

  // Hook up Autosave — pass onBlocksSaved to backfill real DB ids onto new blocks
  const handleConflict = useCallback((errData, attemptedBlocks) => {
    setConflictInfo({
      detail: errData?.detail || errData?.message || "The server has a newer copy of this module.",
      attemptedBlocks: Array.isArray(attemptedBlocks) ? attemptedBlocks : [],
      happenedAt: new Date(),
    });
  }, []);

  // When autosave returns saved blocks with real IDs, merge them back so
  // subsequent saves update rows rather than re-inserting (duplicate prevention).
  const handleBlocksSaved = useCallback((savedBlocks) => {
    setBlocks(prev => prev.map(b => {
      if (b.id) return b; // already has a real id
      // Match by sort_order + block_type + module_id as a heuristic
      const match = savedBlocks.find(
        sb => !sb._matched && sb.module_id === b.module_id &&
              sb.block_type === b.block_type && sb.sort_order === b.sort_order
      );
      if (match) {
        match._matched = true; // prevent double-matching
        return { ...b, id: match.id, _tempId: undefined };
      }
      return b;
    }));
  }, []);

  const handleRecoverDraft = useCallback((draftBlocks) => {
    if (!Array.isArray(draftBlocks)) return;
    setBlocks(draftBlocks);
    onActiveBlockChange?.(null);
  }, [onActiveBlockChange]);

  const { saveState, lastSaved, pendingDraft, restoreDraft, discardDraft, clearConflict } = useAutosave({
    courseId,
    data: blocks,
    onConflict: handleConflict,
    onBlocksSaved: handleBlocksSaved,
    onRecoverDraft: handleRecoverDraft,
  });

  useEffect(() => {
    onSaveStateChange?.({ state: saveState, lastSaved });
  }, [saveState, lastSaved, onSaveStateChange]);

  // Validation
  const validation = useMemo(() => validateBlocks(blocks), [blocks]);

  const keepLocalAfterConflict = useCallback(() => {
    setConflictInfo(null);
    clearConflict();
  }, [clearConflict]);

  const reloadServerAfterConflict = useCallback(async () => {
    await fetchBlocks();
    setConflictInfo(null);
    clearConflict();
  }, [clearConflict, fetchBlocks]);

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    setBlocks((items) => {
      const oldIndex = items.findIndex((i) => `block-${i.id || i._tempId}` === active.id);
      const newIndex = items.findIndex((i) => `block-${i.id || i._tempId}` === over.id);
      
      const newItems = arrayMove(items, oldIndex, newIndex);
      // Update sort order
      return newItems.map((item, index) => ({ ...item, sort_order: index }));
    });
  };

  const addBlock = (type) => {
    let defaultSettings = {};
    if (type === "poll") {
      defaultSettings = {
        question: "",
        allow_multiple: false,
        anonymous_voting: false,
        show_results: "after_vote",
        allow_vote_change: false,
        options: [{ id: `opt_${Date.now()}`, text: "" }]
      };
    } else if (type === "flashcard") {
      defaultSettings = {
        completion_mode: "all_cards",
        randomize_order: false,
        cards: [{ id: `card_${Date.now()}`, front_text: "", back_text: "" }]
      };
    } else if (type === "resource_collection") {
      defaultSettings = {
        completion_mode: "view",
        resources: []
      };
    } else if (type === "quiz") {
      defaultSettings = {
        passing_score: 80,
        max_attempts: 3,
        questions: [createNativeQuizQuestion()]
      };
    }
    const newBlock = {
      _tempId: Date.now(),
      module_id: moduleId,
      block_type: type,
      content: "",
      settings: defaultSettings,
      sort_order: blocks.length,
      is_deleted: false,
    };
    setBlocks([...blocks, newBlock]);
  };

  const updateBlock = (idOrTempId, updates) => {
    setBlocks(blocks.map(b => (b.id === idOrTempId || b._tempId === idOrTempId) ? { ...b, ...updates } : b));
  };

  const selectBlock = (block) => {
    onActiveBlockChange?.(block);
  };

  const deleteBlock = (idOrTempId) => {
    setBlocks(blocks.map(b => (b.id === idOrTempId || b._tempId === idOrTempId) ? { ...b, is_deleted: true } : b));
  };

  const duplicateBlock = (idOrTempId) => {
    setBlocks((current) => {
      const sourceIndex = current.findIndex((block) => block.id === idOrTempId || block._tempId === idOrTempId);
      if (sourceIndex === -1) return current;

      const source = current[sourceIndex];
      const clone = {
        ...source,
        id: null,
        _tempId: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        settings: { ...(source.settings || {}) },
        is_deleted: false,
      };

      const next = [
        ...current.slice(0, sourceIndex + 1),
        clone,
        ...current.slice(sourceIndex + 1),
      ];

      return next.map((block, index) => ({ ...block, sort_order: index }));
    });
  };

  const handleOpenMedia = (blockId, filterType) => {
    setActiveMediaBlockId(blockId);
    setMediaFilterType(filterType);
    setMediaModalOpen(true);
  };

  const handleMediaSelected = (asset) => {
    if (activeMediaBlockId) {
      const block = blocks.find(b => b.id === activeMediaBlockId || b._tempId === activeMediaBlockId);
      if (block?.block_type === "resource_collection") {
        const currentResources = block.settings?.resources || [];
        updateBlock(activeMediaBlockId, {
          settings: {
            ...block.settings,
            resources: [...currentResources, {
              id: `res_${Date.now()}`,
              asset_id: asset.id,
              asset_version: asset.asset_version,
              title: asset.filename,
              description: asset.mime_type
            }]
          }
        });
      } else {
        updateBlock(activeMediaBlockId, {
          media_asset_id: asset.id,
          settings: {
            ...block.settings,
            url: asset.download_url,
            asset_id: asset.id,
            asset_version: asset.asset_version,
            filename: asset.filename,
            mime_type: asset.mime_type,
            metadata: asset.metadata || {},
          }
        });
      }
    }
    setMediaModalOpen(false);
  };

  if (!moduleId) {
    return null;
  }

  if (loading) return <LoadingState message="Loading module content..." />;
  if (error) return <div style={{ color: "red" }}>{error}</div>;

  const visibleBlocks = blocks.filter(b => !b.is_deleted);

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", paddingBottom: "100px" }}>
      {pendingDraft ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", marginBottom: "16px", padding: "14px 16px", background: "var(--warning-bg)", border: "1px solid var(--warning)", borderRadius: "8px" }}>
          <div>
            <div style={{ fontWeight: 700, color: "var(--warning)" }}>Unsaved local draft found</div>
            <div style={{ fontSize: "13px", color: "var(--warning)", marginTop: "2px" }}>
              Last cached {pendingDraft.updatedAt ? new Date(pendingDraft.updatedAt).toLocaleString() : "recently"}.
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <Button tone="neutral" onClick={discardDraft}>Discard</Button>
            <Button tone="primary" onClick={restoreDraft}>Restore Draft</Button>
          </div>
        </div>
      ) : null}

      {/* Validation & Save Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px", padding: "16px", background: "var(--surface-raised)", borderRadius: "8px", border: "1px solid var(--border-subtle)" }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: "16px" }}>Lesson Editor</div>
          <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "4px" }}>
            {saveState === "saving" && "Saving..."}
            {saveState === "idle" && lastSaved && `Last saved at ${lastSaved.toLocaleTimeString()}`}
            {saveState === "offline" && <span style={{ color: "var(--warning)" }}>Offline (Saved locally)</span>}
            {saveState === "conflict" && <span style={{ color: "var(--error)" }}>Conflict!</span>}
            {!lastSaved && saveState === "idle" && "All changes saved"}
          </div>
        </div>

        <div style={{ display: "flex", gap: "12px", flexDirection: "column", alignItems: "flex-end" }}>
          {!validation.isValid && (
            <div style={{ color: "var(--error)", fontSize: "12px", fontWeight: 500 }}>
              {validation.errors.length} validation error(s)
            </div>
          )}
          {validation.warnings.length > 0 && (
            <div style={{ color: "var(--warning)", fontSize: "12px" }}>
              {validation.warnings.length} warning(s)
            </div>
          )}
        </div>
      </div>

      {/* Editor Canvas */}
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={visibleBlocks.map(b => `block-${b.id || b._tempId}`)} strategy={verticalListSortingStrategy}>
          {visibleBlocks.map(block => (
            <SortableBlock
              key={`block-${block.id || block._tempId}`}
              block={block}
              isSelected={activeBlock ? blockKey(activeBlock) === blockKey(block) : false}
              isHighlighted={highlightBlockId === blockKey(block)}
              onSelect={selectBlock}
              onChange={updateBlock}
              onDelete={deleteBlock}
              onDuplicate={duplicateBlock}
              onOpenMedia={handleOpenMedia}
              onOpenInspector={onOpenInspector}
              quizOptions={quizOptions}
              quizLoading={quizLoading}
              quizError={quizError}
            />
          ))}
        </SortableContext>
      </DndContext>

      {visibleBlocks.length === 0 && (
        <div style={{ padding: "60px 20px", textAlign: "center", background: "var(--surface-sunken)", border: "2px dashed var(--border-subtle)", borderRadius: "8px", color: "var(--text-secondary)", marginBottom: "24px", display: "flex", flexDirection: "column", gap: "8px", alignItems: "center" }}>
          <div style={{ fontWeight: 600, fontSize: "16px", color: "var(--text-primary)" }}>
            {moduleType === "quiz" 
              ? "Your Quiz Module is empty" 
              : moduleType === "assignment"
              ? "Your Assignment Shell is empty"
              : moduleType === "resource"
              ? "Your Resource Module is empty"
              : "No content blocks yet"}
          </div>
          <div>
            {moduleType === "quiz" 
              ? "Add a Native Quiz block to begin building your assessment." 
              : moduleType === "assignment"
              ? "Add an Assignment block along with any instructional text or files."
              : moduleType === "resource"
              ? "Add Resource Collection blocks, PDFs, or media to build your resource center."
              : "Add one below to get started."}
          </div>
        </div>
      )}

      {/* Block Toolbar */}
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", justifyContent: "flex-start", padding: "16px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)", borderRadius: "8px" }}>
        <Button tone="neutral" onClick={() => addBlock("heading")}>+ Heading</Button>
        <Button tone="neutral" onClick={() => addBlock("text")}>+ Text</Button>
        <Button tone="neutral" onClick={() => addBlock("image")}>+ Image</Button>
        <Button tone="neutral" onClick={() => addBlock("video")}>+ Video</Button>
        <Button tone="neutral" onClick={() => addBlock("audio")}>+ Audio</Button>
        <Button tone="neutral" onClick={() => addBlock("pdf")}>+ PDF</Button>
        <Button tone="neutral" onClick={() => addBlock("scorm")}>+ SCORM</Button>
        <Button tone="neutral" onClick={() => addBlock("h5p")}>+ H5P</Button>
        <Button tone="neutral" onClick={() => addBlock("assignment")}>+ Assignment</Button>
        <Button tone="neutral" onClick={() => addBlock("poll")}>+ Poll</Button>
        <Button tone="neutral" onClick={() => addBlock("flashcard")}>+ Flashcard</Button>
        <Button tone="neutral" onClick={() => addBlock("resource_collection")}>+ Resources</Button>
        <Button tone="neutral" onClick={() => addBlock("embed")}>+ Embed</Button>
        <Button tone="neutral" onClick={() => addBlock("quiz")}>+ Quiz</Button>
      </div>

      {/* Media Library Modal */}
      {mediaModalOpen && (
        <MediaLibrary
          open={mediaModalOpen}
          onClose={() => setMediaModalOpen(false)}
          onSelect={handleMediaSelected}
          filterType={mediaFilterType}
        />
      )}

      <Modal
        open={Boolean(conflictInfo)}
        onClose={keepLocalAfterConflict}
        title="Autosave Conflict"
        description="Another saved version exists for this module."
        width={520}
        footer={
          <>
            <Button tone="neutral" onClick={keepLocalAfterConflict}>Keep Local Draft</Button>
            <Button tone="primary" onClick={reloadServerAfterConflict}>Reload Server Copy</Button>
          </>
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
          <p style={{ margin: 0 }}>
            {conflictInfo?.detail}
          </p>
          <div style={{ background: "var(--surface-sunken)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "12px" }}>
            <div style={{ fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Local draft</div>
            <div style={{ fontSize: "13px" }}>
              {conflictInfo?.attemptedBlocks?.filter((block) => !block.is_deleted).length || 0} active block(s) were kept in local cache.
            </div>
            {conflictInfo?.happenedAt ? (
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                Conflict detected at {conflictInfo.happenedAt.toLocaleTimeString()}.
              </div>
            ) : null}
          </div>
        </div>
      </Modal>
    </div>
  );
}
