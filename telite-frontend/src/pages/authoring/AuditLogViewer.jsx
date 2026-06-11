import React, { useState, useEffect, useCallback } from "react";
import { api, getErrorMessage } from "../../services/client";
import { LoadingState, ErrorState, Select, Button, Badge } from "../../components/common/ui";
import { formatDateTime } from "../../utils/formatters";
import "./AuditLogViewer.css";

const ACTION_OPTIONS = [
  { value: "", label: "All Actions" },
  { value: "create", label: "Created" },
  { value: "update", label: "Updated" },
  { value: "delete", label: "Deleted" },
  { value: "published", label: "Published" },
  { value: "rollback", label: "Rolled Back" }
];

const ENTITY_OPTIONS = [
  { value: "", label: "All Entities" },
  { value: "course", label: "Course" },
  { value: "section", label: "Section" },
  { value: "module", label: "Module" },
  { value: "block", label: "Block" },
  { value: "media", label: "Media" },
  { value: "version", label: "Version" }
];

const DATE_OPTIONS = [
  { value: "", label: "All Time" },
  { value: "24h", label: "Last 24h" },
  { value: "7d", label: "Last 7d" },
  { value: "30d", label: "Last 30d" }
];

function timeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);
  let interval = seconds / 31536000;
  if (interval > 1) return Math.floor(interval) + " years ago";
  interval = seconds / 2592000;
  if (interval > 1) return Math.floor(interval) + " months ago";
  interval = seconds / 86400;
  if (interval > 1) return Math.floor(interval) + " days ago";
  interval = seconds / 3600;
  if (interval > 1) return Math.floor(interval) + " hours ago";
  interval = seconds / 60;
  if (interval > 1) return Math.floor(interval) + " minutes ago";
  return Math.floor(seconds) + " seconds ago";
}

export function AuditLogViewer({ courseId }) {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [exporting, setExporting] = useState(false);
  
  // Filters
  const [userFilter, setUserFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [dateFilter, setDateFilter] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // Expanded state
  const [expandedRowId, setExpandedRowId] = useState(null);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        course_id: courseId,
        page,
        page_size: pageSize
      };
      
      if (userFilter) params.user_id = userFilter;
      if (actionFilter) params.action = actionFilter;
      if (entityFilter) params.entity_type = entityFilter;
      
      if (dateFilter) {
        const now = new Date();
        if (dateFilter === "24h") {
          now.setHours(now.getHours() - 24);
        } else if (dateFilter === "7d") {
          now.setDate(now.getDate() - 7);
        } else if (dateFilter === "30d") {
          now.setDate(now.getDate() - 30);
        }
        params.start_date = now.toISOString();
      }

      const { data } = await api.get("/api/v1/audit-logs", { params });
      setLogs(data.items || []);
      setTotal(data.total || 0);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load audit logs"));
    } finally {
      setLoading(false);
    }
  }, [courseId, page, userFilter, actionFilter, entityFilter, dateFilter]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const params = { course_id: courseId };
      if (userFilter) params.user_id = userFilter;
      if (actionFilter) params.action = actionFilter;
      if (entityFilter) params.entity_type = entityFilter;
      
      if (dateFilter) {
        const now = new Date();
        if (dateFilter === "24h") now.setHours(now.getHours() - 24);
        else if (dateFilter === "7d") now.setDate(now.getDate() - 7);
        else if (dateFilter === "30d") now.setDate(now.getDate() - 30);
        params.start_date = now.toISOString();
      }

      const response = await api.get("/api/v1/audit-logs/export", { 
        params, 
        responseType: 'blob' 
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `audit_logs_${courseId}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error("Export failed", err);
    } finally {
      setExporting(false);
    }
  };

  const toggleRow = (id) => {
    setExpandedRowId(prev => prev === id ? null : id);
  };

  const renderDiff = (log) => {
    if (!log.before_json && !log.after_json) {
      return <div className="audit-diff-empty">No payload changes recorded.</div>;
    }
    
    return (
      <div className="audit-diff-container">
        <div className="audit-diff-pane audit-diff-before">
          <strong>Before</strong>
          <pre>{log.before_json ? JSON.stringify(log.before_json, null, 2) : "Empty"}</pre>
        </div>
        <div className="audit-diff-pane audit-diff-after">
          <strong>After</strong>
          <pre>{log.after_json ? JSON.stringify(log.after_json, null, 2) : "Empty"}</pre>
        </div>
      </div>
    );
  };

  return (
    <div className="audit-viewer">
      <div className="audit-viewer-header">
        <h3>Audit Trail</h3>
        <Button 
          tone="neutral" 
          onClick={handleExport} 
          disabled={exporting || logs.length === 0}
        >
          {exporting ? "Exporting..." : "Export CSV"}
        </Button>
      </div>

      <div className="audit-viewer-filters">
        <div className="filter-group">
          <label>User ID</label>
          <input 
            type="text" 
            placeholder="Filter by user..." 
            value={userFilter} 
            onChange={e => setUserFilter(e.target.value)}
            onBlur={() => setPage(1)}
          />
        </div>
        <div className="filter-group">
          <label>Action</label>
          <Select 
            value={actionFilter} 
            onChange={e => { setActionFilter(e.target.value); setPage(1); }}
            options={ACTION_OPTIONS}
          />
        </div>
        <div className="filter-group">
          <label>Entity</label>
          <Select 
            value={entityFilter} 
            onChange={e => { setEntityFilter(e.target.value); setPage(1); }}
            options={ENTITY_OPTIONS}
          />
        </div>
        <div className="filter-group">
          <label>Date</label>
          <Select 
            value={dateFilter} 
            onChange={e => { setDateFilter(e.target.value); setPage(1); }}
            options={DATE_OPTIONS}
          />
        </div>
      </div>

      <div className="audit-viewer-content">
        {loading ? (
          <LoadingState message="Loading audit logs..." />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchLogs} />
        ) : logs.length === 0 ? (
          <div className="audit-empty-state">No audit logs found matching your filters.</div>
        ) : (
          <div className="audit-list">
            {logs.map((log) => (
              <div 
                key={log.id} 
                className={`audit-row ${expandedRowId === log.id ? "expanded" : ""}`}
              >
                <div className="audit-row-summary" onClick={() => toggleRow(log.id)}>
                  <div className="audit-row-actor">
                    <strong>{log.actor_name}</strong>
                  </div>
                  <div className="audit-row-action">
                    <span>{log.summary}</span>
                    <Badge>{log.entity_type}</Badge>
                  </div>
                  <div className="audit-row-time">
                    {timeAgo(new Date(log.created_at))}
                  </div>
                </div>
                {expandedRowId === log.id && (
                  <div className="audit-row-details">
                    <div className="audit-meta">
                      <span><strong>ID:</strong> {log.id}</span>
                      <span><strong>Date:</strong> {formatDateTime(log.created_at)}</span>
                      <span><strong>Action:</strong> {log.action}</span>
                      <span><strong>Entity ID:</strong> {log.entity_id}</span>
                    </div>
                    {renderDiff(log)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {total > pageSize && (
        <div className="audit-pagination">
          <Button 
            tone="neutral" 
            disabled={page === 1} 
            onClick={() => setPage(p => p - 1)}
          >
            Previous
          </Button>
          <span>Page {page} of {Math.ceil(total / pageSize)}</span>
          <Button 
            tone="neutral" 
            disabled={page >= Math.ceil(total / pageSize)} 
            onClick={() => setPage(p => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
