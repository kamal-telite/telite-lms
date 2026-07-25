import React from "react";
import { Button } from "../../common/ui";

export function ResourceCollectionBlockEditor({ block, isLocked, onSettingsChange }) {
  const resources = block.settings?.resources || [];

  return (
    <div className="block-editor">
      <div className="block-editor__hint">
        <div className="block-editor__hint-title">Resource collection</div>
        <div className="block-editor__hint-text">
          Add media and documents to your resource collection.
        </div>
      </div>

      {resources.length === 0 ? (
        <div className="block-upload">
          <div className="block-upload__title">No resources yet</div>
          <div className="block-upload__meta">Add items to build this collection</div>
        </div>
      ) : (
        <div className="block-editor" style={{ gap: 8 }}>
          {resources.map((resource, idx) => (
            <div key={resource.id} className="block-card">
              <div className="block-card__header">
                <div style={{ minWidth: 0 }}>
                  <div className="block-card__title" style={{ color: "var(--color-text-primary)" }}>
                    {resource.title || `Resource ${idx + 1}`}
                  </div>
                  <div className="block-editor__meta">
                    {resource.description || "No description provided."}
                  </div>
                </div>
                <Button
                  tone="destructive"
                  size="small"
                  disabled={isLocked}
                  onClick={() => {
                    const newResources = (block.settings?.resources || []).filter((_, i) => i !== idx);
                    onSettingsChange("resources", newResources);
                  }}
                >
                  Remove
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div>
        <Button
          tone="neutral"
          size="small"
          onClick={() => {
            const newResources = [
              ...(block.settings?.resources || []),
              { id: `res_${Date.now()}`, title: "New Resource", description: "", asset_id: null },
            ];
            onSettingsChange("resources", newResources);
          }}
          disabled={isLocked}
        >
          + Add Resource
        </Button>
      </div>
    </div>
  );
}
