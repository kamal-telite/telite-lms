import React, { useState, useEffect, useCallback } from "react";
import { api, getErrorMessage } from "../../services/client";
import { Button, Badge, LoadingState, ErrorState, Modal, useToast } from "../../components/common/ui";
import { VersionDiffViewer } from "./VersionDiffViewer";

export function VersionHistoryPanel({ courseId, currentVersion, onVersionChanged }) {
  const { showToast } = useToast();
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [rollbackTarget, setRollbackTarget] = useState(null);
  const [rollingBack, setRollingBack] = useState(false);
  const [compareBase, setCompareBase] = useState(null);
  const [compareResult, setCompareResult] = useState(null);
  const [comparing, setComparing] = useState(false);

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
    setRollingBack(true);
    try {
      const { data } = await api.post(`/authoring/publishing/courses/${courseId}/versions/${versionId}/rollback`);
      showToast(data.message, "warning");
      setRollbackTarget(null);
      fetchVersions();
      if (onVersionChanged) onVersionChanged(); // Trigger reload of structure
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to rollback version."), "error");
    } finally {
      setRollingBack(false);
    }
  };

  const handleCompare = async (targetVersion) => {
    if (!compareBase) {
      setCompareBase(targetVersion);
      showToast(`Selected v${targetVersion.version_number} as compare base.`, "info");
      return;
    }

    if (compareBase.id === targetVersion.id) {
      setCompareBase(null);
      setCompareResult(null);
      return;
    }

    const left = compareBase.version_number < targetVersion.version_number ? compareBase : targetVersion;
    const right = compareBase.version_number < targetVersion.version_number ? targetVersion : compareBase;

    setComparing(true);
    try {
      const { data } = await api.get(
        `/authoring/publishing/courses/${courseId}/versions/${left.id}/compare/${right.id}`
      );
      setCompareResult(data);
      setCompareBase(null);
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to compare versions."), "error");
    } finally {
      setComparing(false);
    }
  };

  const handleCompareWithCurrent = async (version) => {
    setComparing(true);
    try {
      const { data } = await api.get(
        `/authoring/publishing/courses/${courseId}/versions/${version.id}/compare/current`
      );
      setCompareResult(data);
      setCompareBase(null);
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to compare with current draft."), "error");
    } finally {
      setComparing(false);
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

      {compareBase ? (
        <div style={{ padding: "10px 12px", borderRadius: "8px", border: "1px solid #bfdbfe", background: "#eff6ff", color: "#1e3a8a", fontSize: "13px", marginBottom: "12px" }}>
          Comparing from v{compareBase.version_number}. Select another version to view differences.
        </div>
      ) : null}

      {compareResult ? (
        <div style={{ padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0", background: "#fff", marginBottom: "12px", width: "800px", maxWidth: "100%", position: "absolute", zIndex: 10, left: "-500px", top: "100px", maxHeight: "80vh", overflowY: "auto", boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.1)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center", position: "sticky", top: 0, background: "#fff", paddingBottom: "12px", borderBottom: "1px solid #e2e8f0", zIndex: 11 }}>
            <div>
              <div style={{ fontWeight: 700, color: "#0f172a", fontSize: "16px" }}>
                Diff: v{compareResult.left_version.version_number} → {compareResult.right_version.version_number === "Draft" ? "Live Draft" : `v${compareResult.right_version.version_number}`}
              </div>
              <div style={{ color: "#64748b", fontSize: "12px", marginTop: "2px" }}>Detailed change breakdown</div>
            </div>
            <Button tone="neutral" onClick={() => setCompareResult(null)}>Close Diff</Button>
          </div>
          
          <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
            <VersionDiffViewer diffResult={compareResult} />
          </div>
        </div>
      ) : null}

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

            {v.snapshot_summary ? (
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "10px" }}>
                <Badge tone="neutral">{v.snapshot_summary.sections} sections</Badge>
                <Badge tone="neutral">{v.snapshot_summary.modules} modules</Badge>
                <Badge tone="neutral">{v.snapshot_summary.blocks} blocks</Badge>
              </div>
            ) : null}

            <div style={{ marginTop: "12px", display: "flex", flexWrap: "wrap", gap: "8px" }}>
              <Button tone={compareBase?.id === v.id ? "primary" : "neutral"} size="small" disabled={comparing} onClick={() => handleCompare(v)}>
                {compareBase?.id === v.id ? "Base selected" : "Compare"}
              </Button>
              <Button tone="neutral" size="small" disabled={comparing} onClick={() => handleCompareWithCurrent(v)}>
                Vs Draft
              </Button>
              {currentVersion?.id !== v.id && (
                <Button tone="neutral" size="small" onClick={() => setRollbackTarget(v)}>Rollback to this</Button>
              )}
            </div>
          </div>
        ))}
        {versions.length === 0 && (
          <div style={{ color: "#64748b", fontSize: "14px" }}>No versions tracked yet.</div>
        )}
      </div>

      <Modal
        open={Boolean(rollbackTarget)}
        onClose={() => setRollbackTarget(null)}
        title="Rollback Course"
        width={460}
        footer={
          <>
            <Button tone="neutral" onClick={() => setRollbackTarget(null)}>Cancel</Button>
            <Button tone="danger" disabled={rollingBack} onClick={() => handleRollback(rollbackTarget.id)}>
              {rollingBack ? "Restoring..." : `Rollback to v${rollbackTarget?.version_number}`}
            </Button>
          </>
        }
      >
        <p style={{ margin: 0, color: "#475569", lineHeight: 1.5 }}>
          This will replace the current draft structure with the selected version snapshot. Current sections,
          modules, and blocks will be archived and a restored draft will be created.
        </p>
        {rollbackTarget?.snapshot_summary ? (
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "14px" }}>
            <Badge tone="neutral">{rollbackTarget.snapshot_summary.sections} sections</Badge>
            <Badge tone="neutral">{rollbackTarget.snapshot_summary.modules} modules</Badge>
            <Badge tone="neutral">{rollbackTarget.snapshot_summary.blocks} blocks</Badge>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
