import React from "react";

export function QuizReferenceBlockEditor({ block, isLocked, onQuizChange, quizOptions, quizLoading, quizError }) {
  return (
    <div className="block-editor">
      <div className="block-editor__hint">
        <div className="block-editor__hint-title">Quiz reference</div>
        <div className="block-editor__hint-text">
          Link this lesson block to a quiz module in this course.
        </div>
      </div>
      <label className="field">
        <span className="field__label">Quiz module</span>
        <select
          className="field__input"
          value={block.settings?.quiz_id || ""}
          onChange={onQuizChange}
          disabled={isLocked || quizLoading || quizOptions.length === 0}
        >
          <option value="">
            {quizLoading ? "Loading quizzes…" : quizOptions.length ? "Select a quiz…" : "No quiz modules available"}
          </option>
          {quizOptions.map((quiz) => (
            <option key={quiz.id} value={quiz.id}>
              {quiz.title} ({quiz.module_title})
            </option>
          ))}
        </select>
      </label>
      {quizError ? (
        <div className="block-editor__meta" style={{ color: "var(--error)" }}>{quizError}</div>
      ) : null}
      {!quizLoading && !quizError && quizOptions.length === 0 ? (
        <div className="block-editor__meta">
          Create a module with type &quot;Quiz&quot; first, then return here to attach it.
        </div>
      ) : null}
    </div>
  );
}
