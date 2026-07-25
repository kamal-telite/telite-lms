import { Button, Panel, Badge, EmptyState } from "../../common/ui";
import { formatDateTime, titleize } from "../../../utils/formatters";

/**
 * TasksSection - Task management with submission tracking
 */
export function TasksSection({
  tasks,
  taskFilter,
  onFilterChange,
  submissionDrafts,
  onDraftChange,
  startingTaskId,
  submittingTaskId,
  onStartTask,
  onSubmitTask,
}) {
  return (
    <section id="section-tasks" className="learner-tasks-section">
      <Panel title="Task Management" subtitle="Your assigned projects and assessments">
        <div className="learner-tasks__filter-row">
          {["all", "assigned", "in_progress", "submitted", "approved", "revision_requested"].map(
            (f) => {
              const isActive = taskFilter === f;
              return (
                <label
                  key={f}
                  className={`task-filter-chip learner-tasks__filter-chip${isActive ? " is-active" : ""}`}
                >
                  <input
                    type="radio"
                    checked={isActive}
                    onChange={() => onFilterChange(f)}
                    style={{
                      position: "absolute",
                      opacity: 0,
                      pointerEvents: "none",
                      width: 0,
                      height: 0,
                    }}
                  />
                  {titleize(f)}
                </label>
              );
            }
          )}
        </div>

        <div className="grid-2 learner-tasks__grid">
          {tasks
            .filter((t) =>
              taskFilter === "all" ? true : t.status === taskFilter
            )
            .map((task) => {
              const draft = submissionDrafts[task.id] || {};
              const canStart =
                task.status === "assigned" ||
                task.status === "revision_requested";
              const canSubmit =
                task.status === "in_progress" ||
                task.status === "revision_requested";
              const tone =
                task.status === "approved"
                  ? "success"
                  : task.status === "submitted"
                  ? "brand"
                  : task.status === "revision_requested"
                  ? "danger"
                  : "warn";

              return (
                <div className="soft-card learner-tasks__card" key={task.id}>
                  <div className="split-actions learner-tasks__card-header">
                    <div className="learner-tasks__card-copy">
                      <div className="row-title learner-tasks__card-title">
                        {task.title}
                      </div>
                      <div className="row-subtitle learner-tasks__card-meta">
                        Assigned by: {task.assigned_by_name || "Category Admin"}
                      </div>
                      <div className="row-subtitle learner-tasks__card-meta">
                        Due: {formatDateTime(task.due_at)}
                      </div>
                    </div>
                    <Badge tone={tone}>{titleize(task.status)}</Badge>
                  </div>
                  <p className="muted learner-tasks__card-instructions">
                    {task.instructions || "No additional instructions."}
                  </p>
                  {canSubmit ? (
                    <div className="form-stack learner-tasks__form-stack">
                      <textarea
                        className="field__input learner-tasks__field"
                        rows={3}
                        placeholder="Submission notes"
                        value={draft.submission_notes || ""}
                        onChange={(event) =>
                          onDraftChange(task.id, {
                            ...draft,
                            submission_notes: event.target.value,
                          })
                        }
                      />
                      <input
                        className="field__input learner-tasks__field"
                        placeholder="Github URL or external link"
                        value={draft.external_url || ""}
                        onChange={(event) =>
                          onDraftChange(task.id, {
                            ...draft,
                            external_url: event.target.value,
                          })
                        }
                      />
                    </div>
                  ) : null}
                  <div className="split-actions learner-tasks__card-actions">
                    {canStart ? (
                      <Button
                        size="small"
                        tone="primary"
                        onClick={() => onStartTask(task.id)}
                        disabled={startingTaskId === task.id}
                      >
                        {startingTaskId === task.id ? "Starting..." : "Start Task"}
                      </Button>
                    ) : null}
                    {canSubmit ? (
                      <Button
                        size="small"
                        tone="primary"
                        onClick={() => onSubmitTask(task.id)}
                        disabled={submittingTaskId === task.id}
                      >
                        {submittingTaskId === task.id
                          ? "Submitting..."
                          : "Submit Task"}
                      </Button>
                    ) : null}
                    {task.status === "submitted" ? (
                      <span className="muted learner-tasks__status-text">Awaiting review</span>
                    ) : null}
                    {task.status === "approved" ? (
                      <span className="muted learner-tasks__status-text learner-tasks__status-text--approved">Approved</span>
                    ) : null}
                  </div>
                </div>
              );
            })}
        </div>

        {tasks.filter((t) =>
          taskFilter === "all" ? true : t.status === taskFilter
        ).length === 0 && (
          <div 
            style={{ 
              display: "flex", 
              flexDirection: "column", 
              alignItems: "center", 
              justifyContent: "center", 
              padding: "64px 24px",
              textAlign: "center"
            }}
          >
            <div 
              style={{ 
                width: "64px", 
                height: "64px", 
                borderRadius: "50%", 
                background: "var(--primary-bg, rgba(70,72,212,0.08))", 
                display: "flex", 
                alignItems: "center", 
                justifyContent: "center",
                marginBottom: "18px",
                color: "var(--primary, #4648d4)"
              }}
            >
              {/* Modern inline task check representation */}
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="9" y1="9" x2="15" y2="9" />
                <line x1="9" y1="13" x2="15" y2="13" />
                <line x1="9" y1="17" x2="13" y2="17" />
              </svg>
            </div>
            <h3 style={{ fontSize: "18px", fontWeight: 700, margin: "0 0 8px 0", color: "var(--text-primary)" }}>
              No Tasks Assigned Yet
            </h3>
            <p style={{ fontSize: "14px", color: "var(--text-secondary)", maxWidth: "420px", margin: 0, lineHeight: 1.5 }}>
              Tasks assigned by your instructor or category administrator will appear here once available.
            </p>
          </div>
        )}
      </Panel>
    </section>
  );
}
