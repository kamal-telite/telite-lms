import React, { useState } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { IconButton, useToast } from "../../components/common/ui";
import { api, getErrorMessage } from "../../services/client";

// Sortable Module Item
function SortableModule({ module, isActive, onClick, onRename, onDuplicate, onDelete, canEdit }) {
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
      {canEdit && (
        <>
          <IconButton
            icon="pencil"
            label={`Rename ${module.title}`}
            onClick={(event) => {
              event.stopPropagation();
              onRename(module);
            }}
          />
          <IconButton
            icon="copy"
            label={`Duplicate ${module.title}`}
            onClick={(event) => {
              event.stopPropagation();
              onDuplicate(module);
            }}
          />
          <IconButton
            icon="trash"
            label={`Delete ${module.title}`}
            onClick={(event) => {
              event.stopPropagation();
              onDelete(module);
            }}
          />
        </>
      )}
    </div>
  );
}

// Section Container
function SyllabusSection({
  section,
  modules,
  activeModuleId,
  isCollapsed,
  onToggleCollapsed,
  onSelectModule,
  onAddModule,
  onRenameSection,
  onDuplicateSection,
  onDeleteSection,
  onRenameModule,
  onDuplicateModule,
  onDeleteModule,
  canEdit,
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: `sec-${section.id}` });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    marginBottom: "24px",
    borderRadius: "8px",
    opacity: isDragging ? 0.5 : 1,
    boxShadow: isDragging ? "0 4px 12px rgba(0,0,0,0.1)" : "none",
    position: "relative",
    zIndex: isDragging ? 1 : 0,
    background: "#fff",
  };

  return (
    <div ref={setNodeRef} style={style}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", minWidth: 0 }}>
          <span {...attributes} {...listeners} style={{ cursor: "grab", color: "#94a3b8", padding: "4px" }}>⋮⋮</span>
          <IconButton
            icon={isCollapsed ? "chevronRight" : "chevronDown"}
            label={isCollapsed ? `Expand ${section.title}` : `Collapse ${section.title}`}
            onClick={() => onToggleCollapsed(section.id)}
          />
          <div style={{ fontWeight: 600, fontSize: "14px", color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {section.title}
          </div>
        </div>
        <div style={{ display: "flex", gap: "4px" }}>
          {canEdit && (
            <>
              <IconButton icon="pencil" size="small" label={`Rename ${section.title}`} onClick={() => onRenameSection(section)} />
              <IconButton icon="copy" size="small" label={`Duplicate ${section.title}`} onClick={() => onDuplicateSection(section)} />
              <IconButton icon="trash" size="small" label={`Delete ${section.title}`} onClick={() => onDeleteSection(section)} />
              <IconButton icon="plus" size="small" label={`Add module to ${section.title}`} onClick={() => onAddModule(section)} />
            </>
          )}
        </div>
      </div>
      
      {!isCollapsed && (
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
                onRename={onRenameModule}
                onDuplicate={onDuplicateModule}
                onDelete={onDeleteModule}
                canEdit={canEdit}
              />
            ))}
            {modules.length === 0 && (
              <div style={{ padding: "12px", background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: "6px", fontSize: "12px", color: "#64748b", textAlign: "center" }}>
                No modules in this section.
              </div>
            )}
          </div>
        </SortableContext>
      )}
    </div>
  );
}

export function SyllabusTree({
  courseId,
  sections,
  setSections,
  activeModuleId,
  onSelectModule,
  onAddModule,
  onRenameSection,
  onDuplicateSection,
  onDeleteSection,
  onRenameModule,
  onDuplicateModule,
  onDeleteModule,
  canEdit = true,
}) {
  const [collapsedSections, setCollapsedSections] = useState(() => new Set());
  const { showToast } = useToast();

  const toggleCollapsed = (sectionId) => {
    setCollapsedSections((current) => {
      const next = new Set(current);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  };

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

    // Handle section reordering
    if (String(active.id).startsWith("sec-") && String(over.id).startsWith("sec-")) {
      const activeId = parseInt(active.id.split("-")[1], 10);
      const overId = parseInt(over.id.split("-")[1], 10);
      
      const oldIndex = sections.findIndex(s => s.id === activeId);
      const newIndex = sections.findIndex(s => s.id === overId);
      
      if (oldIndex !== -1 && newIndex !== -1) {
        const newSections = arrayMove(sections, oldIndex, newIndex);
        newSections.forEach((s, idx) => { s.sort_order = idx; });
        setSections(newSections);

        try {
          await api.put(`/authoring/courses/${courseId}/structure`, {
            updates: newSections.map(s => ({
              section_id: s.id,
              sort_order: s.sort_order,
              modules: (s.modules || []).map(m => ({ module_id: m.id, sort_order: m.sort_order }))
            }))
          });
          showToast("Section order saved.", "success");
        } catch (err) {
          setSections(sections);
          showToast(getErrorMessage(err, "Failed to save section order."), "error");
        }
      }
      return;
    }

    // Handle module reordering
    if (!String(active.id).startsWith("mod-")) return;

    const activeId = parseInt(active.id.split("-")[1], 10);
    const overId = String(over.id).startsWith("mod-") ? parseInt(over.id.split("-")[1], 10) : null;

    let sourceSectionIndex = -1;
    let destSectionIndex = -1;
    let sourceModuleIndex = -1;
    let destModuleIndex = -1;

    sections.forEach((sec, sIdx) => {
      const sectionModules = sec.modules || [];
      const mIdxA = sectionModules.findIndex(m => m.id === activeId);
      if (mIdxA > -1) {
        sourceSectionIndex = sIdx;
        sourceModuleIndex = mIdxA;
      }
      if (overId !== null) {
        const mIdxO = sectionModules.findIndex(m => m.id === overId);
        if (mIdxO > -1) {
          destSectionIndex = sIdx;
          destModuleIndex = mIdxO;
        }
      }
    });

    if (String(over.id).startsWith("sec-")) {
      const sectionId = parseInt(over.id.split("-")[1], 10);
      destSectionIndex = sections.findIndex((sec) => sec.id === sectionId);
      destModuleIndex = sections[destSectionIndex]?.modules?.length || 0;
    }

    if (sourceSectionIndex === -1 || destSectionIndex === -1) return;

    const previousSections = sections.map((section) => ({
      ...section,
      modules: (section.modules || []).map((module) => ({ ...module })),
    }));
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
        showToast("Module order saved.", "success");
      } catch (err) {
        setSections(previousSections);
        showToast(getErrorMessage(err, "Failed to save module order. Reverted to previous order."), "error");
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
        showToast("Module moved.", "success");
      } catch (err) {
        setSections(previousSections);
        showToast(getErrorMessage(err, "Failed to move module. Reverted to previous section."), "error");
      }
    }
  };

  return (
    <DndContext 
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <SortableContext
        items={sections.map(s => `sec-${s.id}`)}
        strategy={verticalListSortingStrategy}
      >
        {sections.map((section) => (
          <SyllabusSection 
            key={section.id} 
            section={section} 
            modules={section.modules || []} 
            activeModuleId={activeModuleId}
            isCollapsed={collapsedSections.has(section.id)}
            onToggleCollapsed={toggleCollapsed}
            onSelectModule={onSelectModule}
            onAddModule={onAddModule}
            onRenameSection={onRenameSection}
            onDuplicateSection={onDuplicateSection}
            onDeleteSection={onDeleteSection}
            onRenameModule={onRenameModule}
            onDuplicateModule={onDuplicateModule}
            onDeleteModule={onDeleteModule}
            canEdit={canEdit}
          />
        ))}
      </SortableContext>
      {sections.length === 0 && (
        <div style={{ color: "#64748b", fontSize: "14px", textAlign: "center", marginTop: "20px" }}>
          No sections yet.
        </div>
      )}
    </DndContext>
  );
}
