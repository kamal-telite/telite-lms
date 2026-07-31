import React, { useState, useEffect } from 'react';
import { Badge, Button } from "../common/ui";
import { 
  DndContext, 
  closestCorners, 
  KeyboardSensor, 
  PointerSensor, 
  useSensor, 
  useSensors 
} from "@dnd-kit/core";
import { 
  SortableContext, 
  sortableKeyboardCoordinates, 
  useSortable, 
  verticalListSortingStrategy,
  arrayMove
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

function SortableTaskCard({ task, onEdit, onDelete }) {
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id, data: task });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const isComplete = task.status === "approved" || task.status === "completed";

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`task-kanban-card ${isDragging ? "is-dragging" : ""}`}
      {...attributes}
      {...listeners}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "var(--space-8)" }}>
        <div>
          <div className="row-title" style={{ textDecoration: isComplete ? "line-through" : "none" }}>{task.title}</div>
          <div className="row-subtitle" style={{ marginTop: 4 }}>{task.assigned_label}</div>
          <div className="row-subtitle" style={{ marginTop: 2 }}>Due {task.due_at || "soon"}</div>
        </div>
        <div className="task-kanban-card__actions" onPointerDown={(e) => e.stopPropagation()}>
          {onEdit ? (
            <button
              onClick={() => onEdit(task)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}
              type="button"
            >
              ✏️
            </button>
          ) : null}
          {onDelete ? (
            <button
              onClick={() => setConfirmingDelete(true)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}
              type="button"
            >
              🗑️
            </button>
          ) : null}
        </div>
      </div>

      {onDelete && confirmingDelete ? (
        <div style={{ marginTop: 10 }} onPointerDown={(e) => e.stopPropagation()}>
          <div className="inline-confirm">
            <span>Delete this task?</span>
            <div className="split-actions">
              <Button tone="danger" onClick={() => onDelete(task.id)}>
                Delete
              </Button>
              <Button tone="ghost" onClick={() => setConfirmingDelete(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="task-kanban-card__footer">
        <Badge tone={task.status === "submitted" ? "brand" : task.status === "in_progress" ? "warn" : isComplete ? "success" : "neutral"}>
          {task.status === "submitted" ? "Submitted" : task.status === "in_progress" ? "In Progress" : isComplete ? "Completed" : "Assigned"}
        </Badge>
        <span className="mono muted" style={{ fontSize: 10 }}>{task.due_at || 'soon'}</span>
      </div>
    </div>
  );
}

function TaskColumn({ id, title, tasks, onEdit, onDelete }) {
  return (
    <div className="task-kanban-column">
      <div className="task-kanban-column__header">
        <span className="task-kanban-column__title">{title}</span>
        <span className="task-status-card__count">{tasks.length}</span>
      </div>
      <SortableContext id={id} items={tasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
        <div className="task-kanban-column__list">
          {tasks.map(t => <SortableTaskCard key={t.id} task={t} onEdit={onEdit} onDelete={onDelete} />)}
          {tasks.length === 0 && <div className="task-status-card__empty">No tasks here.</div>}
        </div>
      </SortableContext>
    </div>
  );
}

export function TaskBoardKanban({ allTasks, onTaskStatusChange, onEdit, onDelete }) {
  const [columns, setColumns] = useState({
    pending: [],
    in_progress: [],
    submitted: [],
    completed: []
  });

  useEffect(() => {
    const tasks = allTasks || [];
    setColumns({
      pending: tasks.filter(t => !t.status || t.status === "assigned" || t.status === "pending" || t.status === "revision_requested"),
      in_progress: tasks.filter(t => t.status === "in_progress"),
      submitted: tasks.filter(t => t.status === "submitted"),
      completed: tasks.filter(t => t.status === "approved" || t.status === "completed")
    });
  }, [allTasks]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  function handleDragOver(event) {
    const { active, over } = event;
    if (!over) return;
    
    const activeId = active.id;
    const overId = over.id;
    
    if (activeId === overId) return;

    const activeContainer = active.data.current?.sortable?.containerId;
    const overContainer = over.data.current?.sortable?.containerId || over.id;

    if (!activeContainer || !overContainer || activeContainer === overContainer) {
      return;
    }

    // Backend rule: Admins can ONLY review tasks that are 'submitted'.
    if (activeContainer !== "submitted") {
      return; // UI rollback (won't update state)
    }
    // Also, admins can only move to 'approved' (completed) or 'revision_requested' (pending).
    if (overContainer !== "completed" && overContainer !== "pending") {
      return; // Disallow dragging to in_progress
    }

    setColumns((prev) => {
      const activeItems = [...prev[activeContainer]];
      const overItems = [...prev[overContainer]];
      
      const activeIndex = activeItems.findIndex(t => t.id === activeId);
      const overIndex = overItems.findIndex(t => t.id === overId);
      
      let newIndex = overIndex >= 0 ? overIndex : overItems.length;

      const item = activeItems[activeIndex];
      activeItems.splice(activeIndex, 1);
      
      const updatedItem = { ...item, status: overContainer };
      overItems.splice(newIndex, 0, updatedItem);

      return {
        ...prev,
        [activeContainer]: activeItems,
        [overContainer]: overItems
      };
    });
  }

  function handleDragEnd(event) {
    const { active, over } = event;
    if (!over) return;
    
    const activeContainer = active.data.current?.sortable?.containerId;
    const overContainer = over.data.current?.sortable?.containerId || over.id;

    if (activeContainer && overContainer && activeContainer !== overContainer) {
       // Validate again on drop
       if (activeContainer !== "submitted" || (overContainer !== "completed" && overContainer !== "pending")) {
         // showToast("Admins can only evaluate submitted tasks.", "error"); // Toast handled by parent if needed, but here we just revert
         setColumns((prev) => ({ ...prev })); // Force re-render to snap back
         return;
       }
       onTaskStatusChange(active.id, overContainer);
    } else if (activeContainer && overContainer && activeContainer === overContainer) {
       const activeIndex = columns[activeContainer].findIndex(t => t.id === active.id);
       const overIndex = columns[overContainer].findIndex(t => t.id === over.id);
       if (activeIndex !== overIndex) {
         setColumns((prev) => ({
           ...prev,
           [activeContainer]: arrayMove(prev[activeContainer], activeIndex, overIndex)
         }));
       }
    }
  }

  return (
    <DndContext 
      sensors={sensors} 
      collisionDetection={closestCorners} 
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="task-kanban-grid">
        <TaskColumn id="pending" title="To Do" tasks={columns.pending} onEdit={onEdit} onDelete={onDelete} />
        <TaskColumn id="in_progress" title="In Progress" tasks={columns.in_progress} onEdit={onEdit} onDelete={onDelete} />
        <TaskColumn id="submitted" title="Submitted" tasks={columns.submitted} onEdit={onEdit} onDelete={onDelete} />
        <TaskColumn id="completed" title="Done" tasks={columns.completed} onEdit={onEdit} onDelete={onDelete} />
      </div>
    </DndContext>
  );
}
