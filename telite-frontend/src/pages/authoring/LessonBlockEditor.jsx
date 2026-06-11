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
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Button, IconButton, Badge, LoadingState, Modal } from "../../components/common/ui";
import { api, getErrorMessage } from "../../services/client";
import { useAutosave } from "../../hooks/useAutosave";
import { validateBlocks } from "../../services/validationEngine";
import { MediaLibrary } from "./MediaLibrary";

function blockKey(block) {
  return block.id || block._tempId;
}

// Sortable Block Component
function SortableBlock({
  block,
  isSelected,
  onSelect,
  onChange,
  onDelete,
  onDuplicate,
  onOpenMedia,
  quizOptions = [],
  quizLoading = false,
  quizError = null,
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: `block-${blockKey(block)}` });

  const settings = block.settings || {};
  const isLocked = Boolean(settings.locked);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    background: "#fff",
    border: `1px solid ${isSelected ? "#2563eb" : "#e2e8f0"}`,
    borderRadius: "8px",
    padding: "16px",
    marginBottom: "16px",
    opacity: isDragging ? 0.5 : 1,
    boxShadow: isDragging ? "0 8px 24px rgba(0,0,0,0.1)" : isSelected ? "0 0 0 3px rgba(37, 99, 235, 0.12)" : "0 1px 3px rgba(0,0,0,0.05)",
    position: "relative",
    zIndex: isDragging ? 1 : 0,
  };

  const handleContentChange = (e) => {
    onChange(blockKey(block), { content: e.target.value });
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

  return (
    <div id={`editor-block-${blockKey(block)}`} ref={setNodeRef} style={style} onClick={() => onSelect(block)}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
        <div 
          {...attributes} 
          {...listeners} 
          style={{ cursor: "grab", color: "#94a3b8", display: "flex", alignItems: "center", gap: "8px" }}
        >
          <span style={{ fontSize: "16px" }}>⋮⋮</span>
          <Badge tone="neutral">{block.block_type.toUpperCase()}</Badge>
          {settings.hidden ? <Badge tone="warning">Hidden</Badge> : null}
          {isLocked ? <Badge tone="danger">Locked</Badge> : null}
        </div>
        <div style={{ display: "flex", gap: "6px" }}>
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

      <div style={{ paddingLeft: "24px" }}>
        {block.block_type === "heading" && (
          <input
            className="field__input"
            style={{ fontSize: "20px", fontWeight: 600, padding: "12px", border: "none", borderBottom: "2px solid #e2e8f0", borderRadius: 0 }}
            placeholder="Heading Title..."
            value={block.content || ""}
            onChange={handleContentChange}
            disabled={isLocked}
          />
        )}

        {(block.block_type === "text" || block.block_type === "paragraph") && (
          <textarea
            className="field__input"
            style={{ minHeight: "100px", resize: "vertical" }}
            placeholder="Enter text content..."
            value={block.content || ""}
            onChange={handleContentChange}
            disabled={isLocked}
          />
        )}

        {(block.block_type === "image" || block.block_type === "video" || block.block_type === "audio" || block.block_type === "pdf" || block.block_type === "scorm") && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ background: "#f8fafc", padding: "32px", textAlign: "center", borderRadius: "6px", border: "1px dashed #cbd5e1" }}>
              {block.media_asset_id || block.settings?.asset_id || block.settings?.url ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", alignItems: "center" }}>
                  <div style={{ color: "#059669", fontWeight: 500 }}>Media Attached</div>
                  <div style={{ fontSize: "12px", color: "#64748b", wordBreak: "break-all" }}>
                    {block.settings?.filename || block.settings?.url || `Asset #${block.media_asset_id || block.settings?.asset_id}`}
                  </div>
                  <Button tone="neutral" size="small" disabled={isLocked} onClick={() => onOpenMedia(blockKey(block), block.block_type.split("/")[0])}>Replace Media</Button>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px", alignItems: "center" }}>
                  <div style={{ color: "#64748b" }}>No media selected</div>
                  <Button tone="primary" disabled={isLocked} onClick={() => onOpenMedia(blockKey(block), block.block_type.split("/")[0])}>Browse Library</Button>
                </div>
              )}
            </div>
            <input
              className="field__input"
              placeholder={block.block_type === "scorm" ? "SCORM package URL..." : `${block.block_type} URL...`}
              value={block.settings?.url || ""}
              onChange={(e) => handleSettingsChange("url", e.target.value)}
              disabled={isLocked}
            />
            {block.block_type === "scorm" ? (
              <div style={{ color: "#64748b", fontSize: "13px" }}>
                Attach a SCORM ZIP package from the Media Library.
              </div>
            ) : null}
          </div>
        )}

        {block.block_type === "embed" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ background: "#eff6ff", padding: "16px", borderRadius: "6px", border: "1px solid #bfdbfe" }}>
              <strong>Embedded Content</strong>
              <div style={{ marginTop: "4px", color: "#1d4ed8", fontSize: "13px" }}>
                Add a URL for an external page, tool, or video embed.
              </div>
            </div>
            <input
              className="field__input"
              placeholder="Embed title..."
              value={block.content || ""}
              onChange={handleContentChange}
              disabled={isLocked}
            />
            <input
              className="field__input"
              placeholder="https://..."
              value={block.settings?.url || ""}
              onChange={(e) => handleSettingsChange("url", e.target.value)}
              disabled={isLocked}
            />
          </div>
        )}

        {block.block_type === "assignment" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ background: "#fefce8", padding: "16px", borderRadius: "6px", border: "1px solid #fde68a" }}>
              <strong>Assignment</strong>
              <div style={{ marginTop: "4px", color: "#854d0e", fontSize: "13px" }}>
                Add instructions, due date, and point value for learner submission work.
              </div>
            </div>
            <input
              className="field__input"
              placeholder="Assignment title..."
              value={block.content || ""}
              onChange={handleContentChange}
              disabled={isLocked}
            />
            <textarea
              className="field__input"
              style={{ minHeight: "100px", resize: "vertical" }}
              placeholder="Assignment instructions..."
              value={block.settings?.instructions || ""}
              onChange={(e) => handleSettingsChange("instructions", e.target.value)}
              disabled={isLocked}
            />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <input
                className="field__input"
                type="date"
                value={block.settings?.due_date || ""}
                onChange={(e) => handleSettingsChange("due_date", e.target.value)}
                disabled={isLocked}
              />
              <input
                className="field__input"
                type="number"
                min="0"
                placeholder="Points"
                value={block.settings?.points || ""}
                onChange={(e) => handleSettingsChange("points", e.target.value)}
                disabled={isLocked}
              />
            </div>
          </div>
        )}

        {block.block_type === "quiz_reference" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ background: "#f0fdf4", padding: "16px", borderRadius: "6px", border: "1px solid #bbf7d0" }}>
              <strong>Quiz Reference</strong>
              <div style={{ marginTop: "4px", color: "#166534", fontSize: "13px" }}>
                Link this lesson block to a quiz module in this course.
              </div>
            </div>
            <select
              className="field__input"
              value={block.settings?.quiz_id || ""}
              onChange={handleQuizChange}
              disabled={isLocked || quizLoading || quizOptions.length === 0}
            >
              <option value="">
                {quizLoading ? "Loading quizzes..." : quizOptions.length ? "Select a quiz..." : "No quiz modules available"}
              </option>
              {quizOptions.map((quiz) => (
                <option key={quiz.id} value={quiz.id}>
                  {quiz.title} ({quiz.module_title})
                </option>
              ))}
            </select>
            {quizError ? (
              <div style={{ color: "#b91c1c", fontSize: "13px" }}>{quizError}</div>
            ) : null}
            {!quizLoading && !quizError && quizOptions.length === 0 ? (
              <div style={{ color: "#64748b", fontSize: "13px" }}>
                Create a module with type "Quiz" first, then return here to attach it.
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}


export function LessonBlockEditor({
  courseId,
  moduleId,
  activeBlock,
  highlightBlockId,
  onHighlightClear,
  onActiveBlockChange,
  onRegisterBlockSettingsUpdater,
  onSaveStateChange,
}) {
  const { showToast } = useToast();
  const [blocks, setBlocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [mediaModalOpen, setMediaModalOpen] = useState(false);
  const [activeMediaBlockId, setActiveMediaBlockId] = useState(null);
  const [mediaFilterType, setMediaFilterType] = useState(null);
  const [quizOptions, setQuizOptions] = useState([]);
  const [quizLoading, setQuizLoading] = useState(false);
  const [quizError, setQuizError] = useState(null);
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

  const fetchQuizzes = useCallback(async () => {
    if (!courseId) {
      setQuizOptions([]);
      return;
    }

    setQuizLoading(true);
    try {
      const { data } = await api.get(`/authoring/courses/${courseId}/quizzes`);
      setQuizOptions(data.quizzes || []);
      setQuizError(null);
    } catch (err) {
      setQuizError(getErrorMessage(err, "Failed to load quiz choices."));
    } finally {
      setQuizLoading(false);
    }
  }, [courseId]);

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
    if (moduleId) {
      fetchQuizzes();
    } else {
      setBlocks([]);
    }
    onActiveBlockChange?.(null);
  }, [moduleId, fetchQuizzes, onActiveBlockChange]);

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
    const newBlock = {
      _tempId: Date.now(),
      module_id: moduleId,
      block_type: type,
      content: "",
      settings: {},
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
    setMediaFilterType(filterType === "pdf" ? "application/pdf" : filterType);
    setMediaModalOpen(true);
  };

  const handleMediaSelected = (asset) => {
    if (activeMediaBlockId) {
      updateBlock(activeMediaBlockId, {
        media_asset_id: asset.id,
        settings: {
          url: asset.download_url,
          asset_id: asset.id,
          asset_version: asset.asset_version,
          filename: asset.filename,
          mime_type: asset.mime_type,
        }
      });
    }
    setMediaModalOpen(false);
  };

  if (!moduleId) {
    return null;
  }

  if (loading) return <LoadingState message="Loading module content..." />;
  if (error) return <div style={{ color: "red" }}>{error}</div>;

  const visibleBlocks = blocks.filter(b => !b.is_deleted);

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", paddingBottom: "100px" }}>
      {pendingDraft ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", marginBottom: "16px", padding: "14px 16px", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "8px" }}>
          <div>
            <div style={{ fontWeight: 700, color: "#92400e" }}>Unsaved local draft found</div>
            <div style={{ fontSize: "13px", color: "#92400e", marginTop: "2px" }}>
              Last cached {pendingDraft.updatedAt ? new Date(pendingDraft.updatedAt).toLocaleString() : "recently"}.
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <Button tone="neutral" onClick={discardDraft}>Discard</Button>
            <Button tone="primary" onClick={restoreDraft}>Restore Draft</Button>
          </div>
        </div>
      ) : null}

      {/* Validation & Save Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px", padding: "16px", background: "#fff", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: "16px" }}>Lesson Editor</div>
          <div style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>
            {saveState === "saving" && "Saving..."}
            {saveState === "idle" && lastSaved && `Last saved at ${lastSaved.toLocaleTimeString()}`}
            {saveState === "offline" && <span style={{ color: "#d97706" }}>Offline (Saved locally)</span>}
            {saveState === "conflict" && <span style={{ color: "#ef4444" }}>Conflict!</span>}
            {!lastSaved && saveState === "idle" && "All changes saved"}
          </div>
        </div>

        <div style={{ display: "flex", gap: "12px", flexDirection: "column", alignItems: "flex-end" }}>
          {!validation.isValid && (
            <div style={{ color: "#ef4444", fontSize: "12px", fontWeight: 500 }}>
              {validation.errors.length} validation error(s)
            </div>
          )}
          {validation.warnings.length > 0 && (
            <div style={{ color: "#d97706", fontSize: "12px" }}>
              {validation.warnings.length} warning(s)
            </div>
          )}
        </div>
      </div>

      {/* Editor Canvas */}
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={visibleBlocks.map(b => `block-${b.id || b._tempId}`)} strategy={verticalListSortingStrategy}>
          {visibleBlocks.map(block => (
            <SortableBlock
              key={`block-${block.id || block._tempId}`}
              block={block}
              isSelected={activeBlock ? blockKey(activeBlock) === blockKey(block) : false}
              onSelect={selectBlock}
              onChange={updateBlock}
              onDelete={deleteBlock}
              onDuplicate={duplicateBlock}
              onOpenMedia={handleOpenMedia}
              quizOptions={quizOptions}
              quizLoading={quizLoading}
              quizError={quizError}
            />
          ))}
        </SortableContext>
      </DndContext>

      {visibleBlocks.length === 0 && (
        <div style={{ padding: "60px 20px", textAlign: "center", background: "#f8fafc", border: "2px dashed #cbd5e1", borderRadius: "8px", color: "#64748b", marginBottom: "24px" }}>
          No content blocks yet. Add one below to get started.
        </div>
      )}

      {/* Block Toolbar */}
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", padding: "16px", background: "#fff", border: "1px solid #e2e8f0", borderRadius: "8px" }}>
        <Button tone="neutral" onClick={() => addBlock("heading")}>+ Heading</Button>
        <Button tone="neutral" onClick={() => addBlock("text")}>+ Text</Button>
        <Button tone="neutral" onClick={() => addBlock("image")}>+ Image</Button>
        <Button tone="neutral" onClick={() => addBlock("video")}>+ Video</Button>
        <Button tone="neutral" onClick={() => addBlock("audio")}>+ Audio</Button>
        <Button tone="neutral" onClick={() => addBlock("pdf")}>+ PDF</Button>
        <Button tone="neutral" onClick={() => addBlock("scorm")}>+ SCORM</Button>
        <Button tone="neutral" onClick={() => addBlock("assignment")}>+ Assignment</Button>
        <Button tone="neutral" onClick={() => addBlock("embed")}>+ Embed</Button>
        <Button tone="neutral" onClick={() => addBlock("quiz_reference")}>+ Quiz</Button>
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
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", color: "#475569", lineHeight: 1.5 }}>
          <p style={{ margin: 0 }}>
            {conflictInfo?.detail}
          </p>
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
            <div style={{ fontWeight: 700, color: "#334155", marginBottom: "4px" }}>Local draft</div>
            <div style={{ fontSize: "13px" }}>
              {conflictInfo?.attemptedBlocks?.filter((block) => !block.is_deleted).length || 0} active block(s) were kept in local cache.
            </div>
            {conflictInfo?.happenedAt ? (
              <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
                Conflict detected at {conflictInfo.happenedAt.toLocaleTimeString()}.
              </div>
            ) : null}
          </div>
        </div>
      </Modal>
    </div>
  );
}
