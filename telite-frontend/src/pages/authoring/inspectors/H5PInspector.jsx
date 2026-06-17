import React from "react";
import { Button, Badge } from "../../../components/common/ui";

export default function H5PInspector({ settings, disabled }) {
  const metadata = settings?.metadata || {};
  const assetId = settings?.asset_id;
  const assetVersion = settings?.asset_version || metadata.asset_version || 1;
  const title = metadata.title || settings?.filename || "H5P Activity";
  const mainLibrary = metadata.mainLibrary || "Unknown H5P content type";
  const language = metadata.language || "Not specified";

  const previewActivity = () => {
    if (!assetId) return;
    const src = `/api/v1/player/h5p/${assetId}/versions/${assetVersion}`;
    const playerUrl = `/h5p/index.html?src=${encodeURIComponent(src)}`;
    window.open(playerUrl, "_blank", "noopener,noreferrer");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
        <Badge tone="primary">H5P</Badge>
        <Badge tone="neutral">v{assetVersion}</Badge>
      </div>

      <div className="inspector-row">
        <span className="inspector-row__label">Activity Name</span>
        <span className="inspector-row__value">{title}</span>
      </div>
      <div className="inspector-row">
        <span className="inspector-row__label">Content Type</span>
        <span className="inspector-row__value">{mainLibrary}</span>
      </div>
      <div className="inspector-row">
        <span className="inspector-row__label">Language</span>
        <span className="inspector-row__value">{language}</span>
      </div>
      <div className="inspector-row">
        <span className="inspector-row__label">Asset ID</span>
        <span className="inspector-row__value">{assetId || "Not selected"}</span>
      </div>
      <div className="inspector-row">
        <span className="inspector-row__label">Filename</span>
        <span className="inspector-row__value">{settings?.filename || "Not selected"}</span>
      </div>

      <Button tone="neutral" disabled={disabled || !assetId} onClick={previewActivity}>
        Preview Activity
      </Button>
    </div>
  );
}
