import React from "react";
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
import { IconButton } from "../../components/common/ui";
import { api } from "../../services/client";

// Sortable Module Item
function SortableModule({ module, isActive, onClick }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: `mod-${module.id}` });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    padding: "8px 12px",
    margin: "4px 0",
    background: isActive ? "#eff6ff" : "#fff",
    border: `1px solid ${isActive ? "#bfdbfe" : "#e2e8f0"}`,
    borderRadius: "6px",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    cursor: "pointer",
    opacity: isDragging ? 0.5 : 1,
    boxShadow: isDragging ? "0 4px 12px rgba(0,0,0,0.1)" : "none",
    position: "relative",
    zIndex: isDragging ? 1 : 0,
  };

  return (
    <div ref={setNodeRef} style={style} onClick={() => onClick(module.id)}>
      <div 
        {...attributes} 
        {...listeners} 
        style={{ cursor: "grab", color: "#94a3b8", display: "flex", alignItems: "center" }}
        onClick={(e) => e.stopPropagation()}
      >
        ⋮⋮
      </div>
      <div style={{ flex: 1, fontSize: "13px", color: isActive ? "#1e3a8a" : "#334155", fontWeight: isActive ? 500 : 400 }}>
        {module.title}
      </div>
    </div>
  );
}

// Section Container
function SyllabusSection({ section, modules, activeModuleId, onSelectModule, onAddModule }) {
  return (
    <div style={{ marginBottom: "24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
        <div style={{ fontWeight: 600, fontSize: "14px", color: "#0f172a" }}>
          {section.title}
        </div>
        <IconButton icon="plus" size="small" label={`Add module to ${section.title}`} onClick={() => onAddModule(section)} />
      </div>
      
      <SortableContext 
        items={modules.map(m => `mod-${m.id}`)}
        strategy={verticalListSortingStrategy}
      >
        <div style={{ minHeight: "10px" }}>
          {modules.map((module) => (
            <SortableModule 
              key={module.id} 
              module={module} 
              isActive={activeModuleId === module.id}
              onClick={onSelectModule}
            />
          ))}
          {modules.length === 0 && (
            <div style={{ padding: "12px", background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: "6px", fontSize: "12px", color: "#64748b", textAlign: "center" }}>
              No modules in this section.
            </div>
          )}
        </div>
      </SortableContext>
    </div>
  );
}

export function SyllabusTree({ courseId, sections, setSections, activeModuleId, onSelectModule, onAddModule }) {
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

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    
    if (!over || active.id === over.id) return;

    // For Stage 1, we only handle reordering within the same section easily, 
    // or moving across sections if we find the parent.
    // To keep it simple, we'll find source and dest modules.
    const activeId = parseInt(active.id.split("-")[1], 10);
    const overId = parseInt(over.id.split("-")[1], 10);

    let sourceSectionIndex = -1;
    let destSectionIndex = -1;
    let sourceModuleIndex = -1;
    let destModuleIndex = -1;

    sections.forEach((sec, sIdx) => {
      const mIdxA = sec.modules.findIndex(m => m.id === activeId);
      if (mIdxA > -1) {
        sourceSectionIndex = sIdx;
        sourceModuleIndex = mIdxA;
      }
      const mIdxO = sec.modules.findIndex(m => m.id === overId);
      if (mIdxO > -1) {
        destSectionIndex = sIdx;
        destModuleIndex = mIdxO;
      }
    });

    if (sourceSectionIndex === -1 || destSectionIndex === -1) return;

    const newSections = [...sections];

    if (sourceSectionIndex === destSectionIndex) {
      // Reorder within same section
      const section = newSections[sourceSectionIndex];
      const newModules = arrayMove(section.modules, sourceModuleIndex, destModuleIndex);
      
      // Update sort order optimistically
      newModules.forEach((m, idx) => { m.sort_order = idx; });
      newSections[sourceSectionIndex] = { ...section, modules: newModules };
      
      setSections(newSections);

      // Save to backend
      try {
        await api.put(`/authoring/courses/${courseId}/structure`, {
          updates: [
            {
              section_id: section.id,
              modules: newModules.map(m => ({ module_id: m.id, sort_order: m.sort_order }))
            }
          ]
        });
      } catch (err) {
        console.error("Failed to save structure", err);
        // We should really rollback here, but ignoring for stage 1 mock
      }
    } else {
      // Move to different section — immutable copy to avoid React state mutation
      const newSourceSection = {
        ...newSections[sourceSectionIndex],
        modules: [...newSections[sourceSectionIndex].modules],
      };
      const newDestSection = {
        ...newSections[destSectionIndex],
        modules: [...newSections[destSectionIndex].modules],
      };

      const [movedModule] = newSourceSection.modules.splice(sourceModuleIndex, 1);
      const updatedMovedModule = {
        ...movedModule,
        section_id: newDestSection.id || null,
        section: newDestSection.sort_order ?? 0,
      };
      newDestSection.modules.splice(destModuleIndex, 0, updatedMovedModule);

      // Update sort orders
      newSourceSection.modules.forEach((m, idx) => { m.sort_order = idx; });
      newDestSection.modules.forEach((m, idx) => { m.sort_order = idx; });

      newSections[sourceSectionIndex] = newSourceSection;
      newSections[destSectionIndex] = newDestSection;

      setSections(newSections);
      
      // Save to backend
      try {
        await api.put(`/authoring/courses/${courseId}/structure`, {
          updates: [
            {
              section_id: newSourceSection.id,
              modules: newSourceSection.modules.map(m => ({ module_id: m.id, sort_order: m.sort_order }))
            },
            {
              section_id: newDestSection.id,
              modules: newDestSection.modules.map(m => ({ module_id: m.id, sort_order: m.sort_order }))
            }
          ]
        });
      } catch (err) {
        console.error("Failed to save structure across sections", err);
      }
    }
  };

  return (
    <DndContext 
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      {sections.map((section) => (
        <SyllabusSection 
          key={section.id} 
          section={section} 
          modules={section.modules || []} 
          activeModuleId={activeModuleId}
          onSelectModule={onSelectModule}
          onAddModule={onAddModule}
        />
      ))}
      {sections.length === 0 && (
        <div style={{ color: "#64748b", fontSize: "14px", textAlign: "center", marginTop: "20px" }}>
          No sections yet.
        </div>
      )}
    </DndContext>
  );
}
