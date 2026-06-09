import React, { useState, useEffect, useCallback } from "react";
import { api, getErrorMessage } from "../../services/client";
import { Button, Badge, LoadingState, ErrorState, useToast } from "../../components/common/ui";

export function VersionHistoryPanel({ courseId, currentVersion, onVersionChanged }) {
  const { showToast } = useToast();
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchVersions = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/authoring/publishing/courses/${courseId}/versions`);
      setVersions(data.versions || []);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load version history."));
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    if (courseId) fetchVersions();
  }, [courseId, fetchVersions]);

  const handleCreateVersion = async () => {
    try {
      const { data } = await api.post(`/authoring/publishing/courses/${courseId}/versions`, {
        parent_version_id: currentVersion?.id
      });
      showToast(`Created Version ${data.version.version_number}`, "success");
      fetchVersions();
      if (onVersionChanged) onVersionChanged(data.version);
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to create version."), "error");
    }
  };

  const handleRollback = async (versionId) => {
    if (!window.confirm("Are you sure you want to rollback to this version? Unsaved draft changes will be lost.")) return;
    
    try {
      const { data } = await api.post(`/authoring/publishing/courses/${courseId}/versions/${versionId}/rollback`);
      showToast(data.message, "warning");
      fetchVersions();
      if (onVersionChanged) onVersionChanged(); // Trigger reload of structure
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to rollback version."), "error");
    }
  };

  if (loading && versions.length === 0) return <LoadingState message="Loading versions..." />;
  if (error) return <ErrorState message={error} />;

  return (
    <div style={{ padding: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <h3 style={{ margin: 0, fontSize: "16px" }}>Version History</h3>
        <Button tone="neutral" size="small" onClick={handleCreateVersion}>Snapshot Current</Button>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {versions.map(v => (
          <div key={v.id} style={{ padding: "16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 600 }}>v{v.version_number}</div>
              <Badge tone={v.status === "published" ? "success" : v.status === "review" ? "warning" : "neutral"}>
                {v.status.toUpperCase()}
              </Badge>
            </div>
            
            <div style={{ fontSize: "12px", color: "#64748b", marginTop: "8px" }}>
              Created: {new Date(v.created_at).toLocaleString()}
            </div>

            {v.status === "published" && v.published_at && (
              <div style={{ fontSize: "12px", color: "#059669", marginTop: "4px" }}>
                Published: {new Date(v.published_at).toLocaleString()}
              </div>
            )}

            <div style={{ marginTop: "12px", display: "flex", gap: "8px" }}>
              {currentVersion?.id !== v.id && (
                <Button tone="neutral" size="small" onClick={() => handleRollback(v.id)}>Rollback to this</Button>
              )}
            </div>
          </div>
        ))}
        {versions.length === 0 && (
          <div style={{ color: "#64748b", fontSize: "14px" }}>No versions tracked yet.</div>
        )}
      </div>
    </div>
  );
}
