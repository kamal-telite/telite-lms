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
function SortableModule({ 
  module, 
  moduleIndex,
  isActive, 
  onClick, 
  onRename, 
  onDuplicate, 
  onDelete, 
  canEdit,
  validationResults = [],
}) {
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
    ...(isDragging ? { zIndex: 1 } : {}),
  };

  const className = `syllabus-module ${isActive ? "syllabus-module--active" : ""} ${isDragging ? "syllabus-module--dragging" : ""}`;

  // Find module errors/warnings
  const errors = (validationResults || []).filter(r => r.fix_target?.module_id === module.id && r.severity === "error");
  const warnings = (validationResults || []).filter(r => r.fix_target?.module_id === module.id && r.severity === "warning");

  const hasErrors = errors.length > 0;
  const hasWarnings = warnings.length > 0;
  const isDraft = module.status === "draft";
  const isCompleted = !isDraft && !hasErrors;

  return (
    <div ref={setNodeRef} style={style} className={className} onClick={() => onClick(module.id)}>
      <div 
        {...attributes} 
        {...listeners} 
        className="syllabus-module__drag"
        onClick={(e) => e.stopPropagation()}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="9" cy="5" r="1" />
          <circle cx="9" cy="12" r="1" />
          <circle cx="9" cy="19" r="1" />
          <circle cx="15" cy="5" r="1" />
          <circle cx="15" cy="12" r="1" />
          <circle cx="15" cy="19" r="1" />
        </svg>
      </div>
      <div className="syllabus-module__icon">
        {module.module_type === "quiz" ? (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" />
            <path d="m9 12 2 2 4-4" />
          </svg>
        ) : module.module_type === "assignment" ? (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
            <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        )}
      </div>
      <div className="syllabus-module__content-wrapper">
        <div className="syllabus-module__label">
          Module {moduleIndex}
        </div>
        <div className="syllabus-module__title">
          {module.title}
        </div>
        <div className="syllabus-module__info">
          {module.block_count || 0} {module.block_count === 1 ? "Block" : "Blocks"}
          {module.module_type && ` • ${module.module_type.toUpperCase()}`}
        </div>
      </div>
      <div className="syllabus-module__meta">
        {isDraft && <span className="syllabus-badge syllabus-badge--draft">Draft</span>}
        {isCompleted && <span className="syllabus-badge syllabus-badge--completed">✓</span>}
        {hasErrors && <span className="syllabus-indicator syllabus-indicator--error" title={`${errors.length} validation errors`} />}
        {hasWarnings && !hasErrors && <span className="syllabus-indicator syllabus-indicator--warning" title={`${warnings.length} warnings`} />}
      </div>
      {canEdit && (
        <div className="syllabus-module__actions">
          <IconButton
            icon="pencil"
            size="small"
            label={`Rename ${module.title}`}
            onClick={(event) => {
              event.stopPropagation();
              onRename(module);
            }}
          />
          <IconButton
            icon="copy"
            size="small"
            label={`Duplicate ${module.title}`}
            onClick={(event) => {
              event.stopPropagation();
              onDuplicate(module);
            }}
          />
          <IconButton
            icon="trash"
            size="small"
            label={`Delete ${module.title}`}
            onClick={(event) => {
              event.stopPropagation();
              onDelete(module);
            }}
          />
        </div>
      )}
    </div>
  );
}

// Section Container
function SyllabusSection({
  section,
  sectionIndex,
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
  validationResults = [],
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
    ...(isDragging ? { opacity: 0.5, boxShadow: "var(--shadow-lg)", zIndex: 1 } : {}),
  };

  return (
    <div ref={setNodeRef} style={style} className="syllabus-section">
      <div className="syllabus-section__header">
        <div className="syllabus-section__title">
          <span {...attributes} {...listeners} className="syllabus-module__drag" style={{ padding: "4px" }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="9" cy="5" r="1" />
              <circle cx="9" cy="12" r="1" />
              <circle cx="9" cy="19" r="1" />
              <circle cx="15" cy="5" r="1" />
              <circle cx="15" cy="12" r="1" />
              <circle cx="15" cy="19" r="1" />
            </svg>
          </span>
          <IconButton
            icon={isCollapsed ? "chevronRight" : "chevronDown"}
            size="small"
            label={isCollapsed ? `Expand ${section.title}` : `Collapse ${section.title}`}
            onClick={() => onToggleCollapsed(section.id)}
          />
          <div className="syllabus-section__details">
            <div className="syllabus-section__label">
              {section.id === 0 ? "Course modules" : `Section ${sectionIndex}`}
            </div>
            <div className="syllabus-section__name">
              {section.title}
            </div>
            <div className="syllabus-section__meta-info">
              {modules.length} {modules.length === 1 ? "Module" : "Modules"}
              {section.minimum_time_seconds > 0 && ` • Min ${Math.round(section.minimum_time_seconds / 60)}m`}
            </div>
          </div>
        </div>
        <div className="syllabus-section__actions">
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
          <div style={{ minHeight: "10px" }} className="syllabus-section__modules">
            {modules
              .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
              .map((module, mIdx) => (
              <SortableModule
                key={module.id}
                module={module}
                moduleIndex={mIdx + 1}
                isActive={activeModuleId === module.id}
                onClick={onSelectModule}
                onRename={onRenameModule}
                onDuplicate={onDuplicateModule}
                onDelete={onDeleteModule}
                canEdit={canEdit}
                validationResults={validationResults}
              />
            ))}
            {modules.length === 0 && (
              <div className="syllabus-empty">
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
  validationResults = [],
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
        {sections
          .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
          .map((section) => {
            const sortedSections = [...sections]
              .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
              .filter(s => s.id !== 0);
            const sectionIndex = section.id === 0 ? null : sortedSections.findIndex(s => s.id === section.id) + 1;
            
            return (
              <SyllabusSection 
                key={section.id} 
                section={section} 
                sectionIndex={sectionIndex}
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
                validationResults={validationResults}
              />
            );
          })}
      </SortableContext>
      {sections.length === 0 && (
        <div style={{ color: "var(--text-secondary)", fontSize: "14px", textAlign: "center", marginTop: "20px" }}>
          No sections yet.
        </div>
      )}
    </DndContext>
  );
}
