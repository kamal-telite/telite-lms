import React, { useState, useEffect, useCallback, useRef } from "react";
import { Modal, Button, IconButton, Badge, LoadingState, ErrorState, useToast } from "../../components/common/ui";
import { api, getErrorMessage } from "../../services/client";
import { MediaUsageDrawer } from "./MediaUsageDrawer";

export function MediaLibrary({ open, onClose, onSelect, filterType = null }) {
  const { showToast } = useToast();
  const fileInputRef = useRef(null);

  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [folderFilter, setFolderFilter] = useState("all");
  const [tagFilter, setTagFilter] = useState("all");
  const [folders, setFolders] = useState([]);
  const [tags, setTags] = useState([]);
  const [uploading, setUploading] = useState(false);
  
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [editTarget, setEditTarget] = useState(null);
  const [editFolder, setEditFolder] = useState("");
  const [editTags, setEditTags] = useState("");
  const [replaceTarget, setReplaceTarget] = useState(null);
  const replaceInputRef = useRef(null);

  // Usage tracking state
  const [usageTarget, setUsageTarget] = useState(null);
  const [usageData, setUsageData] = useState([]);
  const [usageLoading, setUsageLoading] = useState(false);
  const [replaceWarningTarget, setReplaceWarningTarget] = useState(null);

  const fetchAssets = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        limit: 100,
        search: search.trim() || undefined,
      };
      if (filterType) {
        params.type = filterType;
      } else if (typeFilter !== "all") {
        params.type = typeFilter;
      }
      if (folderFilter !== "all") {
        params.folder = folderFilter;
      }
      if (tagFilter !== "all") {
        params.tag = tagFilter;
      }

      const { data } = await api.get("/authoring/media", { params });
      setAssets(data.assets || []);
      setFolders(data.folders || []);
      setTags(data.tags || []);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load media assets."));
    } finally {
      setLoading(false);
    }
  }, [filterType, folderFilter, search, tagFilter, typeFilter]);

  useEffect(() => {
    if (open) {
      const timer = window.setTimeout(fetchAssets, search ? 250 : 0);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [open, fetchAssets, search]);

  const fetchUsage = async (assetId) => {
    setUsageLoading(true);
    try {
      const { data } = await api.get(`/authoring/media/${assetId}/usage`);
      setUsageData(data.usage || []);
    } catch (err) {
      showToast("Failed to fetch asset usage.", "error");
    } finally {
      setUsageLoading(false);
    }
  };

  const handleUpload = async (file) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post("/authoring/media/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      showToast("Media uploaded successfully.", "success");
      if (data.asset) {
        setAssets((current) => [data.asset, ...current]);
      } else {
        fetchAssets();
      }
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to upload media."), "error");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (e, asset) => {
    e.stopPropagation();
    if (!asset.can_delete) {
      setUsageTarget({ ...asset, isDeleteAttempt: true });
      fetchUsage(asset.id);
      return;
    }
    setDeleteTarget(asset);
  };

  const openEdit = (e, asset) => {
    e.stopPropagation();
    setEditTarget(asset);
    setEditFolder(asset.folder || "");
    setEditTags((asset.tags || []).join(", "));
  };

  const saveMetadata = async () => {
    if (!editTarget) return;
    try {
      const tags = editTags
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean);
      const { data } = await api.patch(`/authoring/media/${editTarget.id}`, {
        folder: editFolder.trim() || null,
        tags,
      });
      showToast("Media metadata updated.", "success");
      setAssets((current) => current.map((asset) => asset.id === editTarget.id ? data.asset : asset));
      setEditTarget(null);
      fetchAssets();
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to update media metadata."), "error");
    }
  };

  const openReplace = (e, asset) => {
    e.stopPropagation();
    if (asset.used_by_blocks > 1) {
      setReplaceWarningTarget(asset);
    } else {
      proceedWithReplace(asset);
    }
  };

  const proceedWithReplace = (asset) => {
    setReplaceWarningTarget(null);
    setReplaceTarget(asset);
    if (replaceInputRef.current) {
      replaceInputRef.current.value = "";
    }
    replaceInputRef.current?.click();
  };

  const handleReplace = async (file) => {
    if (!replaceTarget || !file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post(`/authoring/media/${replaceTarget.id}/replace`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      showToast("Media replaced successfully.", "success");
      setAssets((current) => current.map((asset) => asset.id === replaceTarget.id ? data.asset : asset));
      setReplaceTarget(null);
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to replace media."), "error");
    } finally {
      setUploading(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/authoring/media/${deleteTarget.id}`);
      showToast("Asset deleted.", "warning");
      setAssets((current) => current.filter((a) => a.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to delete asset."), "error");
    }
  };

  const formatSize = (bytes = 0) => `${(bytes / 1024 / 1024).toFixed(2)} MB`;

  const renderPreview = (asset) => {
    if (asset.mime_type.startsWith("image/")) {
      return (
        <img
          src={asset.download_url}
          alt={asset.filename}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      );
    }
    if (asset.mime_type.startsWith("video/")) {
      return (
        <video
          src={asset.download_url}
          muted
          preload="metadata"
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      );
    }
    if (asset.mime_type.startsWith("audio/")) {
      return <span style={{ color: "#475569", fontWeight: 700 }}>AUDIO</span>;
    }
    if (asset.mime_type === "application/pdf") {
      return <span style={{ color: "#475569", fontWeight: 700 }}>PDF</span>;
    }
    return <span style={{ color: "#475569", fontWeight: 700 }}>File</span>;
  };

  return (
    <Modal open={open} onClose={onClose} title="Media Library" width="800px">
      <div style={{ display: "flex", gap: "16px", marginBottom: "20px" }}>
        <input
          className="field__input"
          placeholder="Search media..."
          style={{ flex: 1 }}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Button
          tone="primary"
          icon="upload"
          disabled={uploading}
          onClick={() => fileInputRef.current?.click()}
        >
          {uploading ? "Uploading..." : "Upload Media"}
        </Button>
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: "none" }}
          onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
        />
        <input
          type="file"
          ref={replaceInputRef}
          style={{ display: "none" }}
          onChange={(e) => e.target.files?.[0] && handleReplace(e.target.files[0])}
        />
      </div>

      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: "16px", alignItems: "center" }}>
        {!filterType ? (
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {[
              ["all", "All"],
              ["image", "Images"],
              ["video", "Videos"],
              ["audio", "Audio"],
              ["pdf", "PDFs"],
              ["other", "Other"],
            ].map(([value, label]) => (
              <Button
                 key={value}
                 tone={typeFilter === value ? "primary" : "neutral"}
                 size="small"
                 onClick={() => setTypeFilter(value)}
               >
                 {label}
               </Button>
            ))}
          </div>
        ) : null}
        <select className="field__input" style={{ width: "160px" }} value={folderFilter} onChange={(e) => setFolderFilter(e.target.value)}>
          <option value="all">All folders</option>
          {folders.map((folder) => (
            <option key={folder} value={folder}>{folder}</option>
          ))}
        </select>
        <select className="field__input" style={{ width: "140px" }} value={tagFilter} onChange={(e) => setTagFilter(e.target.value)}>
          <option value="all">All tags</option>
          {tags.map((tag) => (
            <option key={tag} value={tag}>{tag}</option>
          ))}
        </select>
      </div>

      <div style={{ minHeight: "400px", maxHeight: "60vh", overflowY: "auto", background: "#f8fafc", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
        {loading ? (
          <LoadingState message="Loading media..." />
        ) : error ? (
          <ErrorState body={error} />
        ) : assets.length === 0 ? (
          <div style={{ textAlign: "center", color: "#64748b", marginTop: "100px" }}>
            No media found. Upload an asset to get started.
          </div>
        ) : (
          <div className="grid-3" style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "16px" }}>
            {assets.map((asset) => (
              <div
                key={asset.id}
                style={{
                  background: "#fff",
                  border: "1px solid #cbd5e1",
                  borderRadius: "8px",
                  overflow: "hidden",
                  transition: "all 0.2s",
                }}
              >
                <div style={{ height: "120px", background: "#e2e8f0", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
                  {renderPreview(asset)}
                </div>
                <div style={{ padding: "12px", fontSize: "13px" }}>
                  <div style={{ fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={asset.filename}>
                    {asset.filename}
                  </div>
                  <div style={{ color: "#64748b", marginTop: "4px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span>{formatSize(asset.size_bytes)}</span>
                    <Badge tone="neutral">v{asset.asset_version}</Badge>
                  </div>
                  {(asset.folder || asset.tags?.length) ? (
                    <div style={{ marginTop: "6px", color: "#475569", fontSize: "12px" }}>
                      {asset.folder ? <span>{asset.folder}</span> : null}
                      {asset.folder && asset.tags?.length ? <span> · </span> : null}
                      {asset.tags?.length ? <span>{asset.tags.join(", ")}</span> : null}
                    </div>
                  ) : null}
                  {asset.used_by_blocks ? (
                    <div style={{ marginTop: "6px", color: "#0f172a", fontSize: "12px", fontWeight: 500, display: "flex", gap: "4px", cursor: "pointer" }} onClick={(e) => { e.stopPropagation(); setUsageTarget(asset); fetchUsage(asset.id); }}>
                      <span style={{ textDecoration: "underline" }}>Used in {asset.used_by_blocks} block(s)</span>
                    </div>
                  ) : (
                    <div style={{ marginTop: "6px", color: "#64748b", fontSize: "12px" }}>
                      Not attached
                    </div>
                  )}
                  <div style={{ marginTop: "8px", display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
                    <Button tone="primary" onClick={() => onSelect(asset)}>Select</Button>
                    <Button tone="neutral" onClick={() => window.open(asset.download_url, "_blank", "noopener,noreferrer")}>Preview</Button>
                    <Button tone="neutral" onClick={(e) => openEdit(e, asset)}>Edit</Button>
                    <Button tone="neutral" disabled={uploading} onClick={(e) => openReplace(e, asset)}>Replace</Button>
                    <IconButton
                      icon="trash"
                      size="small"
                      label="Delete asset"
                      onClick={(e) => handleDelete(e, asset)}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <Modal
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        title="Delete Media"
        width={420}
        footer={
          <>
            <Button tone="neutral" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button tone="danger" onClick={confirmDelete}>Delete</Button>
          </>
        }
      >
        <p style={{ margin: 0, color: "#475569", lineHeight: 1.5 }}>
          Delete {deleteTarget?.filename}? This removes it from the media library.
        </p>
      </Modal>

      <Modal
        open={Boolean(usageTarget) && !deleteTarget}
        onClose={() => setUsageTarget(null)}
        title="Cannot Delete Media"
        width={480}
        footer={
          <Button tone="primary" onClick={() => setUsageTarget(null)}>Acknowledge</Button>
        }
      >
        <p style={{ margin: "0 0 16px", color: "#475569", lineHeight: 1.5 }}>
          <strong>{usageTarget?.filename}</strong> cannot be deleted because it is currently used in {usageTarget?.used_by_blocks} location(s).
        </p>
        <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
          <p style={{ margin: "0 0 8px", fontWeight: 600, fontSize: "13px" }}>Please remove it from these blocks first:</p>
          <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "13px", color: "#475569" }}>
            {usageData.map((u, i) => (
              <li key={i}>{u.course_title} → {u.section_title} → {u.module_title}</li>
            ))}
          </ul>
        </div>
      </Modal>

      <MediaUsageDrawer
        open={Boolean(usageTarget) && deleteTarget === null && !usageTarget?.isDeleteAttempt}
        onClose={() => setUsageTarget(null)}
        asset={usageTarget}
        usageData={usageData}
        loading={usageLoading}
      />

      <Modal
        open={Boolean(editTarget)}
        onClose={() => setEditTarget(null)}
        title="Edit Media Metadata"
        width={480}
        footer={
          <>
            <Button tone="neutral" onClick={() => setEditTarget(null)}>Cancel</Button>
            <Button tone="primary" onClick={saveMetadata}>Save</Button>
          </>
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <label className="field">
            <span className="field__label">Folder</span>
            <input className="field__input" value={editFolder} onChange={(e) => setEditFolder(e.target.value)} placeholder="e.g. onboarding" />
          </label>
          <label className="field">
            <span className="field__label">Tags</span>
            <input className="field__input" value={editTags} onChange={(e) => setEditTags(e.target.value)} placeholder="video, intro, compliance" />
          </label>
        </div>
      </Modal>

      <Modal 
        open={Boolean(replaceWarningTarget)} 
        onClose={() => setReplaceWarningTarget(null)} 
        title="Replace Multiple Uses" 
        width={420} 
        footer={
          <>
            <Button tone="neutral" onClick={() => setReplaceWarningTarget(null)}>Cancel</Button>
            <Button tone="primary" onClick={() => proceedWithReplace(replaceWarningTarget)}>Replace Everywhere</Button>
          </>
        }
      >
        <p style={{ margin: 0, color: "#475569", lineHeight: 1.5 }}>
          <strong>{replaceWarningTarget?.filename}</strong> is used in {replaceWarningTarget?.used_by_blocks} lesson blocks. If you replace this file, it will be updated across all of those locations immediately.
        </p>
      </Modal>
    </Modal>
  );
}
