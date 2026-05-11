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
    opacity: isDragging ? 0.5 : 1,
    cursor: "grab",
    background: "var(--surface)", 
    padding: 12, 
    borderRadius: 8, 
    marginBottom: 8, 
    boxShadow: isDragging ? "0 4px 12px rgba(0,0,0,0.15)" : "0 1px 3px rgba(0,0,0,0.1)",
    textDecoration: task.status === "completed" ? "line-through" : "none",
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div className="row-title" style={{textDecoration: task.status === "completed" ? "line-through" : "none"}}>{task.title}</div>
          <div className="row-subtitle" style={{ marginTop: 4 }}>{task.assigned_label}</div>
        </div>
        <div style={{ display: "flex", gap: 4 }} onPointerDown={(e) => e.stopPropagation()}>
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

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
        <Badge tone={task.status === "in_progress" ? "warn" : task.status === "completed" ? "success" : "neutral"}>
          {task.status === "in_progress" ? "In Progress" : task.status === "completed" ? "Done" : "To Do"}
        </Badge>
        <span className="mono muted" style={{ fontSize: 10 }}>{task.due_at || 'soon'}</span>
      </div>
    </div>
  );
}

function TaskColumn({ id, title, tasks, onEdit, onDelete }) {
  return (
    <div className="soft-card" style={{ background: "var(--surface-alt)", display: "flex", flexDirection: "column", minHeight: 300 }}>
      <div className="row-title" style={{ marginBottom: 12 }}>{title} ({tasks.length})</div>
      <SortableContext id={id} items={tasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
        <div style={{ flex: 1 }}>
          {tasks.map(t => <SortableTaskCard key={t.id} task={t} onEdit={onEdit} onDelete={onDelete} />)}
          {tasks.length === 0 && <div className="muted" style={{ fontSize: 12, textAlign: "center", padding: 16 }}>No tasks here.</div>}
        </div>
      </SortableContext>
    </div>
  );
}

export function TaskBoardKanban({ allTasks, onTaskStatusChange, onEdit, onDelete }) {
  const [columns, setColumns] = useState({
    pending: [],
    in_progress: [],
    completed: []
  });

  useEffect(() => {
    setColumns({
      pending: allTasks.filter(t => !t.status || t.status === "pending"),
      in_progress: allTasks.filter(t => t.status === "in_progress"),
      completed: allTasks.filter(t => t.status === "completed")
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
      <div className="grid-3">
        <TaskColumn id="pending" title="📋 To Do" tasks={columns.pending} onEdit={onEdit} onDelete={onDelete} />
        <TaskColumn id="in_progress" title="🔄 In Progress" tasks={columns.in_progress} onEdit={onEdit} onDelete={onDelete} />
        <TaskColumn id="completed" title="✅ Done" tasks={columns.completed} onEdit={onEdit} onDelete={onDelete} />
      </div>
    </DndContext>
  );
}
