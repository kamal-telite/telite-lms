import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Badge, LoadingState, ErrorState } from "../../components/common/ui";
import { api, getErrorMessage } from "../../services/client";
import { BlockRenderer } from "../../components/player/BlockRenderer";

function flattenModules(sections = []) {
  return sections.flatMap((section) =>
    (section.modules || []).map((module) => ({
      ...module,
      section_id: section.id,
      section_title: section.title,
    }))
  );
}

export function CoursePreviewPanel({ courseId, courseName, sections, activeModuleId }) {
  const [previewActiveModuleId, setPreviewActiveModuleId] = useState(activeModuleId || null);
  const [blocks, setBlocks] = useState([]);
  const [loadingBlocks, setLoadingBlocks] = useState(false);
  const [error, setError] = useState(null);

  const modules = useMemo(() => flattenModules(sections || []), [sections]);
  const activeModule = useMemo(
    () => modules.find((module) => module.id === previewActiveModuleId) || null,
    [modules, previewActiveModuleId]
  );

  // Sync preview module with editor module
  useEffect(() => {
    if (activeModuleId && activeModuleId !== previewActiveModuleId) {
      setPreviewActiveModuleId(activeModuleId);
    }
  }, [activeModuleId, previewActiveModuleId]);

  const loadBlocks = useCallback(async () => {
    if (!courseId || !previewActiveModuleId) {
      setBlocks([]);
      return;
    }

    setLoadingBlocks(true);
    try {
      const { data } = await api.get(`/authoring/courses/${courseId}/modules/${previewActiveModuleId}/blocks`);
      setBlocks(data.blocks || []);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load module preview."));
    } finally {
      setLoadingBlocks(false);
    }
  }, [courseId, previewActiveModuleId]);

  useEffect(() => {
    loadBlocks();
  }, [loadBlocks]);

  return (
    <div className="builder-preview">
      <div className="builder-preview__header">
        <div>
          <div style={{ fontWeight: 700, color: "var(--color-text-primary)" }}>Live Learner Preview</div>
          <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", marginTop: "2px" }}>
            Rendering current builder structure as learner view
          </div>
        </div>
        <Badge tone="neutral">Read-only</Badge>
      </div>

      <div className="builder-preview__body">
        <aside className="builder-preview__sidebar">
          <div className="builder-preview__sidebar-header">
            <div style={{ fontWeight: 700, color: "var(--color-text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", minWidth: 0 }}>
              {courseName}
            </div>
            <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", marginTop: "4px" }}>
              {modules.length} module(s)
            </div>
          </div>
          <div className="builder-preview__sidebar-body">
            {modules.map((module, index) => {
              const isActive = module.id === previewActiveModuleId;
              return (
                <button
                  key={module.id}
                  type="button"
                  onClick={() => setPreviewActiveModuleId(module.id)}
                  className={`builder-preview__module-item ${isActive ? 'builder-preview__module-item--active' : ''}`}
                >
                  <span className="builder-preview__module-number">
                    {index + 1}
                  </span>
                  <span className="builder-preview__module-content">
                    <span className="builder-preview__module-title">
                      {module.title}
                    </span>
                    <span className="builder-preview__module-section">
                      {module.section_title || "Course modules"}
                    </span>
                  </span>
                </button>
              );
            })}
            {modules.length === 0 ? (
              <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--text-muted)", background: "var(--surface)", border: "1px dashed var(--border)", borderRadius: "8px" }}>
                Nothing to preview yet. Add a module to see the learner experience.
              </div>
            ) : null}
          </div>
        </aside>

        <main className="builder-preview__content">
          <header className="builder-preview__content-header">
            <div style={{ color: "var(--color-text-secondary)", fontSize: "12px", fontWeight: 700, textTransform: "uppercase", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", minWidth: 0 }}>
              {activeModule?.section_title || "Course modules"}
            </div>
            <h3 style={{ margin: "4px 0 0", color: "var(--color-text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", minWidth: 0 }}>{activeModule?.title || "Select a module"}</h3>
          </header>

          <div className="builder-preview__content-body">
            <div className="builder-preview__content-inner">
              {loadingBlocks ? (
                <LoadingState title="Loading module blocks..." />
              ) : activeModule ? (
                blocks.length > 0 ? (
                  <BlockRenderer content={blocks} />
                ) : (
                  <div className="builder-preview__empty">
                    This module has no visible blocks yet.
                  </div>
                )
              ) : (
                <div className="builder-preview__empty">
                  Select a module from the preview sidebar.
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
