import React, { useEffect, useState } from "react";
import {
  DndContext,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Badge, Button, IconButton } from "../common/ui";
import { Icon } from "../common/icons";

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

  return (
    <div
      ref={setNodeRef}
      className={`kanban-task-card ${isDragging ? "is-dragging" : ""} ${task.status === "completed" ? "is-complete" : ""}`}
      style={style}
      {...attributes}
      {...listeners}
    >
      <div className="kanban-task-card__header">
        <div>
          <div className="row-title kanban-task-card__title">{task.title}</div>
          <div className="row-subtitle kanban-task-card__assignee">{task.assigned_label}</div>
        </div>
        <div className="kanban-task-card__actions" onPointerDown={(event) => event.stopPropagation()}>
          {onEdit ? (
            <IconButton label="Edit task" icon="pencil" size="sm" onClick={() => onEdit(task)} />
          ) : null}
          {onDelete ? (
            <IconButton label="Delete task" icon="trash" size="sm" onClick={() => setConfirmingDelete(true)} />
          ) : null}
        </div>
      </div>

      {onDelete && confirmingDelete ? (
        <div className="kanban-task-card__confirm" onPointerDown={(event) => event.stopPropagation()}>
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

      <div className="kanban-task-card__meta">
        <Badge tone={task.status === "in_progress" ? "warn" : task.status === "completed" ? "success" : "neutral"}>
          {task.status === "in_progress" ? "In Progress" : task.status === "completed" ? "Done" : "To Do"}
        </Badge>
        <span className="mono muted kanban-task-card__date">{task.due_at || "soon"}</span>
      </div>
    </div>
  );
}

function TaskColumn({ id, title, icon, tasks, onEdit, onDelete }) {
  return (
    <div className="soft-card kanban-column">
      <div className="row-title kanban-column__title">
        <Icon name={icon} size={14} />
        <span>{title} ({tasks.length})</span>
      </div>
      <SortableContext id={id} items={tasks.map((task) => task.id)} strategy={verticalListSortingStrategy}>
        <div className="kanban-column__body">
          {tasks.map((task) => (
            <SortableTaskCard key={task.id} task={task} onEdit={onEdit} onDelete={onDelete} />
          ))}
          {tasks.length === 0 ? <div className="kanban-column__empty">No tasks here.</div> : null}
        </div>
      </SortableContext>
    </div>
  );
}

export function TaskBoardKanban({ allTasks, onTaskStatusChange, onEdit, onDelete }) {
  const [columns, setColumns] = useState({
    pending: [],
    in_progress: [],
    completed: [],
  });

  useEffect(() => {
    setColumns({
      pending: allTasks.filter((task) => !task.status || task.status === "pending"),
      in_progress: allTasks.filter((task) => task.status === "in_progress"),
      completed: allTasks.filter((task) => task.status === "completed"),
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

    setColumns((prev) => {
      const activeItems = [...prev[activeContainer]];
      const overItems = [...prev[overContainer]];

      const activeIndex = activeItems.findIndex((task) => task.id === activeId);
      const overIndex = overItems.findIndex((task) => task.id === overId);

      const newIndex = overIndex >= 0 ? overIndex : overItems.length;

      const item = activeItems[activeIndex];
      activeItems.splice(activeIndex, 1);

      const updatedItem = { ...item, status: overContainer };
      overItems.splice(newIndex, 0, updatedItem);

      return {
        ...prev,
        [activeContainer]: activeItems,
        [overContainer]: overItems,
      };
    });
  }

  function handleDragEnd(event) {
    const { active, over } = event;
    if (!over) return;

    const activeContainer = active.data.current?.sortable?.containerId;
    const overContainer = over.data.current?.sortable?.containerId || over.id;

    if (activeContainer && overContainer && activeContainer !== overContainer) {
      onTaskStatusChange(active.id, overContainer);
    } else if (activeContainer && overContainer && activeContainer === overContainer) {
      const activeIndex = columns[activeContainer].findIndex((task) => task.id === active.id);
      const overIndex = columns[overContainer].findIndex((task) => task.id === over.id);
      if (activeIndex !== overIndex) {
        setColumns((prev) => ({
          ...prev,
          [activeContainer]: arrayMove(prev[activeContainer], activeIndex, overIndex),
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
      <div className="grid-3">
        <TaskColumn id="pending" title="To Do" icon="task" tasks={columns.pending} onEdit={onEdit} onDelete={onDelete} />
        <TaskColumn id="in_progress" title="In Progress" icon="reports" tasks={columns.in_progress} onEdit={onEdit} onDelete={onDelete} />
        <TaskColumn id="completed" title="Done" icon="check" tasks={columns.completed} onEdit={onEdit} onDelete={onDelete} />
      </div>
    </DndContext>
  );
}
