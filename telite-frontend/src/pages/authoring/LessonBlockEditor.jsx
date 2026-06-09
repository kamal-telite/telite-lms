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
import { Button, IconButton, Badge, LoadingState } from "../../components/common/ui";
import { api, getErrorMessage } from "../../services/client";
import { useAutosave } from "../../hooks/useAutosave";
import { validateBlocks } from "../../services/validationEngine";
import { MediaLibrary } from "./MediaLibrary";

// Sortable Block Component
function SortableBlock({ block, onChange, onDelete, onDuplicate, onOpenMedia }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: `block-${block.id || block._tempId}` });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    padding: "16px",
    marginBottom: "16px",
    opacity: isDragging ? 0.5 : 1,
    boxShadow: isDragging ? "0 8px 24px rgba(0,0,0,0.1)" : "0 1px 3px rgba(0,0,0,0.05)",
    position: "relative",
    zIndex: isDragging ? 1 : 0,
  };

  const handleContentChange = (e) => {
    onChange(block.id || block._tempId, { content: e.target.value });
  };

  const handleSettingsChange = (key, value) => {
    onChange(block.id || block._tempId, { settings: { ...block.settings, [key]: value } });
  };

  return (
    <div ref={setNodeRef} style={style}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
        <div 
          {...attributes} 
          {...listeners} 
          style={{ cursor: "grab", color: "#94a3b8", display: "flex", alignItems: "center", gap: "8px" }}
        >
          <span style={{ fontSize: "16px" }}>⋮⋮</span>
          <Badge tone="neutral">{block.block_type.toUpperCase()}</Badge>
        </div>
        <div style={{ display: "flex", gap: "6px" }}>
          <IconButton icon="copy" size="small" label="Duplicate block" onClick={() => onDuplicate(block.id || block._tempId)} />
          <IconButton icon="trash" size="small" label="Delete block" onClick={() => onDelete(block.id || block._tempId)} />
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
          />
        )}

        {(block.block_type === "text" || block.block_type === "paragraph") && (
          <textarea
            className="field__input"
            style={{ minHeight: "100px", resize: "vertical" }}
            placeholder="Enter text content..."
            value={block.content || ""}
            onChange={handleContentChange}
          />
        )}

        {(block.block_type === "image" || block.block_type === "video" || block.block_type === "pdf") && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ background: "#f8fafc", padding: "32px", textAlign: "center", borderRadius: "6px", border: "1px dashed #cbd5e1" }}>
              {block.media_asset_id || block.settings?.asset_id || block.settings?.url ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", alignItems: "center" }}>
                  <div style={{ color: "#059669", fontWeight: 500 }}>Media Attached</div>
                  <div style={{ fontSize: "12px", color: "#64748b", wordBreak: "break-all" }}>
                    {block.settings?.filename || block.settings?.url || `Asset #${block.media_asset_id || block.settings?.asset_id}`}
                  </div>
                  <Button tone="neutral" size="small" onClick={() => onOpenMedia(block.id || block._tempId, block.block_type.split("/")[0])}>Replace Media</Button>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px", alignItems: "center" }}>
                  <div style={{ color: "#64748b" }}>No media selected</div>
                  <Button tone="primary" onClick={() => onOpenMedia(block.id || block._tempId, block.block_type.split("/")[0])}>Browse Library</Button>
                </div>
              )}
            </div>
            <input
              className="field__input"
              placeholder={`${block.block_type} URL...`}
              value={block.settings?.url || ""}
              onChange={(e) => handleSettingsChange("url", e.target.value)}
            />
          </div>
        )}

        {block.block_type === "quiz_reference" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ background: "#f0fdf4", padding: "16px", borderRadius: "6px", border: "1px solid #bbf7d0" }}>
              <strong>Quiz Block</strong>
            </div>
            <input
              className="field__input"
              placeholder="Quiz ID reference..."
              value={block.settings?.quiz_id || ""}
              onChange={(e) => handleSettingsChange("quiz_id", e.target.value)}
            />
          </div>
        )}
      </div>
    </div>
  );
}


export function LessonBlockEditor({ courseId, moduleId }) {
  const [blocks, setBlocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [mediaModalOpen, setMediaModalOpen] = useState(false);
  const [activeMediaBlockId, setActiveMediaBlockId] = useState(null);
  const [mediaFilterType, setMediaFilterType] = useState(null);

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
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load blocks for this module."));
    } finally {
      setLoading(false);
    }
  }, [courseId, moduleId]);

  useEffect(() => {
    if (moduleId) {
      fetchBlocks();
    } else {
      setBlocks([]);
    }
  }, [moduleId, fetchBlocks]);

  // Hook up Autosave — pass onBlocksSaved to backfill real DB ids onto new blocks
  const handleConflict = useCallback((errData) => {
    console.warn("Optimistic concurrency conflict!", errData);
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

  const { saveState, lastSaved } = useAutosave({
    courseId,
    data: blocks,
    onConflict: handleConflict,
    onBlocksSaved: handleBlocksSaved,
  });

  // Validation
  const validation = useMemo(() => validateBlocks(blocks), [blocks]);

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
              onChange={updateBlock}
              onDelete={deleteBlock}
              onDuplicate={duplicateBlock}
              onOpenMedia={handleOpenMedia}
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
        <Button tone="neutral" onClick={() => addBlock("pdf")}>+ PDF</Button>
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
    </div>
  );
}
