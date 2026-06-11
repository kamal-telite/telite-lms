import React, { useState, useEffect } from "react";
import { PageHeader, Card, LoadingState, ErrorState, Button, useToast } from "../../../components/common/ui";
import { api, getErrorMessage } from "../../../services/client";

export function PermissionMatrix() {
  const { showToast } = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  
  // Local state to track modifications
  const [matrix, setMatrix] = useState({});

  useEffect(() => {
    fetchMatrix();
  }, []);

  const fetchMatrix = async () => {
    setLoading(true);
    try {
      const res = await api.get("/authoring/permissions");
      setData(res.data);
      setMatrix(res.data.matrix);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load permission matrix"));
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = (role, capability) => {
    setMatrix(prev => ({
      ...prev,
      [role]: {
        ...prev[role],
        [capability]: !prev[role][capability]
      }
    }));
  };

  const saveChanges = async () => {
    setSaving(true);
    try {
      const updates = data.roles.map(role => ({
        role: role,
        updates: matrix[role]
      }));
      await api.put("/authoring/permissions", updates);
      setData(prev => ({ ...prev, matrix: JSON.parse(JSON.stringify(matrix)) }));
      showToast("Permissions updated. Note: Affected users may need to log out and back in.", "success");
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to save permissions"), "error");
    } finally {
      setSaving(false);
    }
  };
  
  const formatKey = (key) => {
    return key.replace("authoring.", "").replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
  };
  
  const formatRole = (role) => {
    return role.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
  };

  if (loading) return <LoadingState message="Loading permission matrix..." />;
  if (error) return <ErrorState body={error} />;
  if (!data) return null;

  const hasChanges = JSON.stringify(matrix) !== JSON.stringify(data.matrix);

  return (
    <div style={{ maxWidth: "1000px", margin: "0 auto", padding: "24px" }}>
      <PageHeader 
        title="Permission Matrix" 
        subtitle="Manage authoring capabilities per role."
        actions={
          <Button tone="primary" onClick={saveChanges} disabled={!hasChanges || saving}>
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        }
      />
      
      <Card style={{ overflowX: "auto", marginTop: "24px", padding: 0 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px", textAlign: "left" }}>
          <thead>
            <tr>
              <th style={{ padding: "16px", borderBottom: "2px solid #e2e8f0", background: "#f8fafc", color: "#475569", fontWeight: 600 }}>Capability</th>
              {data.roles.map(role => (
                <th key={role} style={{ padding: "16px", borderBottom: "2px solid #e2e8f0", background: "#f8fafc", color: "#475569", fontWeight: 600, textAlign: "center" }}>
                  {formatRole(role)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.capabilities.map(cap => (
              <tr key={cap} style={{ borderBottom: "1px solid #e2e8f0" }}>
                <td style={{ padding: "16px", color: "#0f172a", fontWeight: 500 }}>
                  {formatKey(cap)}
                </td>
                {data.roles.map(role => (
                  <td key={role} style={{ padding: "16px", textAlign: "center" }}>
                    <input 
                      type="checkbox" 
                      checked={matrix[role][cap]} 
                      onChange={() => handleToggle(role, cap)}
                      style={{ width: "18px", height: "18px", cursor: "pointer", accentColor: "#0f172a" }}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {hasChanges && (
        <div style={{ marginTop: "16px", padding: "12px", background: "#eff6ff", color: "#1e40af", borderRadius: "6px", fontSize: "13px" }}>
          <strong>Unsaved changes:</strong> Permissions are evaluated directly from user sessions, so affected users may need to log out and back in after saving for these changes to take effect.
        </div>
      )}
    </div>
  );
}
