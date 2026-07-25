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
} from "@dnd-kit/sortable";
import { Button, IconButton, Badge, LoadingState, Modal, useToast } from "../../components/common/ui";
import { api, getErrorMessage } from "../../services/client";
import { useAutosave } from "../../hooks/useAutosave";
import { validateBlocks } from "../../services/validationEngine";
import { MediaLibrary } from "./MediaLibrary";
import { useParams } from "react-router-dom";
import { SortableBlock } from "../../components/authoring/SortableBlock";
import { blockKey, createNativeQuizQuestion, getDefaultBlockSettings } from "../../components/authoring/utils/blockEditorUtils";

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
    const defaultSettings = getDefaultBlockSettings(type);
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
  if (error) return <div className="text-red-600">{error}</div>;

  const visibleBlocks = blocks.filter(b => !b.is_deleted);

  const blockPickerItems = [
    {
      type: "heading",
      label: "Heading",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M6 4v16" /><path d="M18 4v16" /><path d="M6 12h12" />
        </svg>
      ),
    },
    {
      type: "text",
      label: "Text",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M4 7V5h16v2" /><path d="M9 19h6" /><path d="M12 5v14" />
        </svg>
      ),
    },
    {
      type: "image",
      label: "Image",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><path d="m21 15-5-5L5 21" />
        </svg>
      ),
    },
    {
      type: "video",
      label: "Video",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="2" y="6" width="14" height="12" rx="2" /><path d="m22 8-6 4 6 4V8Z" />
        </svg>
      ),
    },
    {
      type: "audio",
      label: "Audio",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" />
        </svg>
      ),
    },
    {
      type: "pdf",
      label: "PDF",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" /><path d="M14 2v6h6" /><path d="M10 13h4" /><path d="M10 17h4" />
        </svg>
      ),
    },
    {
      type: "scorm",
      label: "SCORM",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
        </svg>
      ),
    },
    {
      type: "h5p",
      label: "H5P",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2" /><path d="M12 22V12" /><path d="m22 8.5-10 6.5L2 8.5" />
        </svg>
      ),
    },
    {
      type: "assignment",
      label: "Assignment",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
        </svg>
      ),
    },
    {
      type: "poll",
      label: "Poll",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M18 20V10" /><path d="M12 20V4" /><path d="M6 20v-6" />
        </svg>
      ),
    },
    {
      type: "flashcard",
      label: "Flashcard",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="2" y="6" width="14" height="12" rx="2" /><path d="M22 8v10a2 2 0 0 1-2 2H8" />
        </svg>
      ),
    },
    {
      type: "resource_collection",
      label: "Resources",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2Z" />
        </svg>
      ),
    },
    {
      type: "embed",
      label: "Embed",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="m16 18 6-6-6-6" /><path d="m8 6-6 6 6 6" />
        </svg>
      ),
    },
    {
      type: "quiz",
      label: "Quiz",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /><path d="M12 17h.01" />
        </svg>
      ),
    },
  ];

  return (
    <div className="builder-editor-canvas">
      {pendingDraft ? (
        <div className="mb-4 flex items-center justify-between gap-4 rounded-xl border border-(--warning) bg-(--warning-bg) px-4 py-3">
          <div>
            <div className="font-semibold text-(--warning)">Unsaved local draft found</div>
            <div className="mt-1 text-sm text-(--warning)">
              Last cached {pendingDraft.updatedAt ? new Date(pendingDraft.updatedAt).toLocaleString() : "recently"}.
            </div>
          </div>
          <div className="flex gap-2">
            <Button tone="neutral" onClick={discardDraft}>Discard</Button>
            <Button tone="primary" onClick={restoreDraft}>Restore Draft</Button>
          </div>
        </div>
      ) : null}

      <div className="builder-lesson-header">
        <div>
          <div className="builder-lesson-header__title">Lesson Editor</div>
          <div className="builder-lesson-header__meta">
            {saveState === "saving" && "Saving…"}
            {saveState === "idle" && lastSaved && `Last saved at ${lastSaved.toLocaleTimeString()}`}
            {saveState === "offline" && <span className="text-(--warning)">Offline (Saved locally)</span>}
            {saveState === "conflict" && <span className="text-(--error)">Conflict!</span>}
            {!lastSaved && saveState === "idle" && "All changes saved"}
          </div>
        </div>

        <div className="flex flex-col items-end gap-1">
          {!validation.isValid && (
            <div className="text-(--error) text-xs font-semibold">
              {validation.errors.length} validation error(s)
            </div>
          )}
          {validation.warnings.length > 0 && (
            <div className="text-(--warning) text-xs">
              {validation.warnings.length} warning(s)
            </div>
          )}
        </div>
      </div>

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
        <div className="builder-empty-blocks">
          <div className="builder-empty-blocks__title">
            {moduleType === "quiz"
              ? "Your Quiz Module is empty"
              : moduleType === "assignment"
              ? "Your Assignment Shell is empty"
              : moduleType === "resource"
              ? "Your Resource Module is empty"
              : "No content blocks yet"}
          </div>
          <div className="builder-empty-blocks__text">
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

      <div className="block-picker">
        <div className="block-picker__header">
          <div className="block-picker__title">Add content</div>
          <div className="block-picker__subtitle">Choose a block type</div>
        </div>
        <div className="block-picker__grid">
          {blockPickerItems.map((item) => (
            <button
              key={item.type}
              type="button"
              className="block-picker__item"
              onClick={() => addBlock(item.type)}
            >
              <span className="block-picker__icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </div>
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
        <div className="flex flex-col gap-3 text-(--text-secondary) leading-6">
          <p className="m-0">
            {conflictInfo?.detail}
          </p>
          <div className="rounded-xl border border-(--border-subtle) bg-(--surface-sunken) p-3">
            <div className="mb-1 font-semibold text-(--text-primary)">Local draft</div>
            <div className="text-sm">
              {conflictInfo?.attemptedBlocks?.filter((block) => !block.is_deleted).length || 0} active block(s) were kept in local cache.
            </div>
            {conflictInfo?.happenedAt ? (
              <div className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>
                Conflict detected at {conflictInfo.happenedAt.toLocaleTimeString()}.
              </div>
            ) : null}
          </div>
        </div>
      </Modal>
    </div>
  );
}
