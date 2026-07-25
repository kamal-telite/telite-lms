import React, { useState, useEffect } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { IconButton, Badge } from "../common/ui";
import { HeadingBlockEditor } from "./blockEditors/HeadingBlockEditor";
import { TextBlockEditor } from "./blockEditors/TextBlockEditor";
import { MediaBlockEditor } from "./blockEditors/MediaBlockEditor";
import { EmbedBlockEditor } from "./blockEditors/EmbedBlockEditor";
import { AssignmentBlockEditor } from "./blockEditors/AssignmentBlockEditor";
import { PollBlockEditor } from "./blockEditors/PollBlockEditor";
import { FlashcardBlockEditor } from "./blockEditors/FlashcardBlockEditor";
import { ResourceCollectionBlockEditor } from "./blockEditors/ResourceCollectionBlockEditor";
import { QuizReferenceBlockEditor } from "./blockEditors/QuizReferenceBlockEditor";
import { NativeQuizBlockEditor } from "./blockEditors/NativeQuizBlockEditor";
import { checkStaleQuestions } from "../../services/client";
import { blockKey, createNativeQuizQuestion } from "./utils/blockEditorUtils";

const BLOCK_META = {
  heading: { label: "Heading", title: "Section heading" },
  text: { label: "Text", title: "Rich text content" },
  paragraph: { label: "Text", title: "Rich text content" },
  image: { label: "Image", title: "Image media" },
  video: { label: "Video", title: "Video media" },
  audio: { label: "Audio", title: "Audio media" },
  pdf: { label: "PDF", title: "PDF document" },
  scorm: { label: "SCORM", title: "SCORM package" },
  h5p: { label: "H5P", title: "H5P interactive" },
  embed: { label: "Embed", title: "External embed" },
  assignment: { label: "Assignment", title: "Learner assignment" },
  poll: { label: "Poll", title: "Poll question" },
  flashcard: { label: "Flashcard", title: "Flashcard set" },
  resource_collection: { label: "Resources", title: "Resource collection" },
  quiz_reference: { label: "Quiz", title: "Quiz reference" },
  quiz: { label: "Quiz", title: "Native quiz" },
};

export function SortableBlock({
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
  const meta = BLOCK_META[block.block_type] || {
    label: block.block_type,
    title: block.block_type,
  };

  useEffect(() => {
    if (block.block_type === "quiz" && block.settings?.questions?.length > 0) {
      const bankRefs = block.settings.questions
        .filter((q) => q.type === "bank_reference" && q.question_id && q.version_id)
        .map((q) => ({ question_id: q.question_id, version_id: q.version_id }));

      if (bankRefs.length > 0) {
        checkStaleQuestions(bankRefs)
          .then((data) => {
            setStaleQuestions(data);
          })
          .catch((err) => console.error("Failed to check stale questions", err));
      }
    }
  }, [block.block_type, block.settings?.questions]);

  const className = `builder-block ${isSelected ? "builder-block--selected" : ""} ${isDragging ? "builder-block--dragging" : ""} ${isHighlighted ? "builder-block--highlight" : ""}`;

  const handleContentChange = (e) => {
    const nextContent = typeof e?.target?.value === "string" ? e.target.value : "";
    onChange(blockKey(block), { content: nextContent });
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
    if (targetTag !== "input" && targetTag !== "textarea" && targetTag !== "button" && targetTag !== "svg" && targetTag !== "path") {
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
        <div className="builder-block__header-left">
          <div {...attributes} {...listeners} className="builder-block__drag" title="Drag to reorder" aria-label="Drag to reorder">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="9" cy="5" r="1" />
              <circle cx="9" cy="12" r="1" />
              <circle cx="9" cy="19" r="1" />
              <circle cx="15" cy="5" r="1" />
              <circle cx="15" cy="12" r="1" />
              <circle cx="15" cy="19" r="1" />
            </svg>
          </div>
          <span className="builder-block__type-badge">{meta.label}</span>
          <span className="builder-block__title">{meta.title}</span>
          <div className="builder-block__status-badges">
            {settings.hidden ? <Badge tone="warning">Hidden</Badge> : null}
            {isLocked ? <Badge tone="danger">Locked</Badge> : null}
          </div>
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

      <div className="builder-block__body">
        {block.block_type === "heading" && (
          <HeadingBlockEditor
            block={block}
            isLocked={isLocked}
            onChange={(value) => handleContentChange({ target: { value } })}
          />
        )}

        {(block.block_type === "text" || block.block_type === "paragraph") && (
          <TextBlockEditor
            block={block}
            isLocked={isLocked}
            onChange={(value) => handleContentChange({ target: { value } })}
          />
        )}

        {(block.block_type === "image" || block.block_type === "video" || block.block_type === "audio" || block.block_type === "pdf" || block.block_type === "scorm" || block.block_type === "h5p") && (
          <MediaBlockEditor
            block={block}
            isLocked={isLocked}
            onSettingsChange={handleSettingsChange}
            onOpenMedia={onOpenMedia}
          />
        )}

        {block.block_type === "embed" && (
          <EmbedBlockEditor
            block={block}
            isLocked={isLocked}
            onContentChange={(value) => handleContentChange({ target: { value } })}
            onSettingsChange={handleSettingsChange}
          />
        )}

        {block.block_type === "assignment" && (
          <AssignmentBlockEditor
            block={block}
            isLocked={isLocked}
            onContentChange={(value) => handleContentChange({ target: { value } })}
            onSettingsChange={handleSettingsChange}
          />
        )}

        {block.block_type === "poll" && (
          <PollBlockEditor
            block={block}
            isLocked={isLocked}
            onSettingsChange={handleSettingsChange}
          />
        )}

        {block.block_type === "flashcard" && (
          <FlashcardBlockEditor
            block={block}
            isLocked={isLocked}
            onSettingsChange={handleSettingsChange}
          />
        )}

        {block.block_type === "resource_collection" && (
          <ResourceCollectionBlockEditor
            block={block}
            isLocked={isLocked}
            onSettingsChange={handleSettingsChange}
          />
        )}

        {block.block_type === "quiz_reference" && (
          <QuizReferenceBlockEditor
            block={block}
            isLocked={isLocked}
            onQuizChange={handleQuizChange}
            quizOptions={quizOptions}
            quizLoading={quizLoading}
            quizError={quizError}
          />
        )}

        {block.block_type === "quiz" && (
          <NativeQuizBlockEditor
            block={block}
            isLocked={isLocked}
            settings={settings}
            onSettingsChange={handleSettingsChange}
            updateQuizQuestion={updateQuizQuestion}
            updateQuizOption={updateQuizOption}
            addQuizOption={addQuizOption}
            removeQuizOption={removeQuizOption}
            createNativeQuizQuestion={createNativeQuizQuestion}
            bankPickerOpen={bankPickerOpen}
            setBankPickerOpen={setBankPickerOpen}
            slug={slug}
            staleQuestions={staleQuestions}
            quizOptions={quizOptions}
            quizLoading={quizLoading}
            quizError={quizError}
          />
        )}
      </div>
    </div>
  );
}
