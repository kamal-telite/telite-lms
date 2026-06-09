import React, { useState, useEffect, useCallback, useRef } from "react";
import { Modal, Button, IconButton, Badge, LoadingState, ErrorState, useToast } from "../../components/common/ui";
import { api, getErrorMessage } from "../../services/client";

export function MediaLibrary({ open, onClose, onSelect, filterType = null }) {
  const { showToast } = useToast();
  const fileInputRef = useRef(null);
  
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [uploading, setUploading] = useState(false);

  const fetchAssets = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/authoring/media");
      setAssets(data.assets || []);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load media assets."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      fetchAssets();
    }
  }, [open, fetchAssets]);

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

  const handleDelete = async (e, assetId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this asset?")) return;
    
    try {
      await api.delete(`/authoring/media/${assetId}`);
      showToast("Asset deleted.", "warning");
      setAssets(assets.filter(a => a.id !== assetId));
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to delete asset."), "error");
    }
  };

  const filteredAssets = assets.filter(a => {
    if (search && !a.filename.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterType && !a.mime_type.startsWith(filterType)) return false;
    return true;
  });

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
      </div>

      <div style={{ minHeight: "400px", maxHeight: "60vh", overflowY: "auto", background: "#f8fafc", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
        {loading ? (
          <LoadingState message="Loading media..." />
        ) : error ? (
          <ErrorState body={error} />
        ) : filteredAssets.length === 0 ? (
          <div style={{ textAlign: "center", color: "#64748b", marginTop: "100px" }}>
            No media found. Upload an asset to get started.
          </div>
        ) : (
          <div className="grid-3" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}>
            {filteredAssets.map(asset => (
              <div 
                key={asset.id} 
                style={{ 
                  background: "#fff", 
                  border: "1px solid #cbd5e1", 
                  borderRadius: "8px", 
                  overflow: "hidden",
                  cursor: "pointer",
                  transition: "all 0.2s"
                }}
                onClick={() => onSelect(asset)}
              >
                <div style={{ height: "120px", background: "#e2e8f0", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
                  {asset.mime_type.startsWith("image/") ? (
                    <img src={asset.download_url} alt={asset.filename} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  ) : asset.mime_type.startsWith("video/") ? (
                    <span style={{ fontSize: "32px" }}>🎥</span>
                  ) : (
                    <span style={{ fontSize: "32px" }}>📄</span>
                  )}
                </div>
                <div style={{ padding: "12px", fontSize: "13px" }}>
                  <div style={{ fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={asset.filename}>
                    {asset.filename}
                  </div>
                  <div style={{ color: "#64748b", marginTop: "4px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span>{(asset.size_bytes / 1024 / 1024).toFixed(2)} MB</span>
                    <Badge tone="neutral">v{asset.asset_version}</Badge>
                  </div>
                  <div style={{ marginTop: "8px", display: "flex", justifyContent: "flex-end" }}>
                    <IconButton icon="trash" size="small" onClick={(e) => handleDelete(e, asset.id)} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}
