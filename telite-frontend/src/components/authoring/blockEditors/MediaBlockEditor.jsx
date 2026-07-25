import React from "react";
import { Button } from "../../common/ui";
import ImagePreview from "../ImagePreview";

export function MediaBlockEditor({ block, isLocked, onSettingsChange, onOpenMedia }) {
  const mediaType = block.block_type.split("/")[0];
  const assetAttached = Boolean(block.media_asset_id || block.settings?.asset_id);
  const blockId = block.id || block._tempId;

  return (
    <div className="block-editor">
      <div className={`block-upload ${assetAttached ? "block-upload--attached" : ""}`}>
        {assetAttached ? (
          <>
            <div className="block-upload__title">Media attached</div>
            <div className="block-upload__meta">
              {block.settings?.filename || `Asset #${block.media_asset_id || block.settings?.asset_id}`}
            </div>
            <Button tone="neutral" size="small" disabled={isLocked} onClick={() => onOpenMedia(blockId, mediaType)}>
              Replace Media
            </Button>
          </>
        ) : (
          <>
            <div className="block-upload__title">No media selected</div>
            <div className="block-upload__meta">Choose a file from the media library</div>
            <Button tone="primary" disabled={isLocked} onClick={() => onOpenMedia(blockId, mediaType)}>
              Browse Library
            </Button>
          </>
        )}
      </div>

      {block.block_type === "image" && (block.settings?.url || block.media_asset_id) && (
        <div className="block-editor__section">
          <div className="block-editor__section-title">Preview</div>
          <ImagePreview settings={block.settings || {}} />
        </div>
      )}

      {block.block_type === "scorm" ? (
        <p className="block-editor__meta m-0">Attach a SCORM ZIP package from the Media Library.</p>
      ) : block.block_type === "h5p" ? (
        <p className="block-editor__meta m-0">Attach an H5P file (.h5p) from the Media Library.</p>
      ) : null}
    </div>
  );
}
