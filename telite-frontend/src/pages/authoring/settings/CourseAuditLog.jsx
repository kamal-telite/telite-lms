import React, { useState, useEffect } from "react";
import { Modal, Button, LoadingState, ErrorState, Badge } from "../../../components/common/ui";
import { api, getErrorMessage } from "../../../services/client";

function DiffViewer({ beforeObj, afterObj }) {
  return (
    <div style={{ display: 'flex', gap: '16px', marginTop: '16px' }}>
      <div style={{ flex: 1, background: '#fef2f2', padding: '12px', borderRadius: '4px', overflowX: 'auto', fontSize: '12px', fontFamily: 'monospace' }}>
        <strong>Before:</strong>
        <pre style={{ margin: '8px 0 0 0', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{JSON.stringify(beforeObj, null, 2)}</pre>
      </div>
      <div style={{ flex: 1, background: '#f0fdf4', padding: '12px', borderRadius: '4px', overflowX: 'auto', fontSize: '12px', fontFamily: 'monospace' }}>
        <strong>After:</strong>
        <pre style={{ margin: '8px 0 0 0', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{JSON.stringify(afterObj, null, 2)}</pre>
      </div>
    </div>
  );
}

export function AuditLogModal({ courseId, open, onClose }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedLogId, setExpandedLogId] = useState(null);

  useEffect(() => {
    if (open && courseId) {
      fetchLogs();
    }
  }, [open, courseId]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/authoring/courses/${courseId}/audit-logs`);
      setLogs(res.data.audit_logs);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load audit logs"));
    } finally {
      setLoading(false);
    }
  };

  const getActionColor = (action) => {
    if (action === 'create') return 'success';
    if (action === 'delete') return 'danger';
    return 'accent';
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Course Audit Log"
      width={900}
      footer={<Button tone="neutral" onClick={onClose}>Close</Button>}
    >
      {loading ? <LoadingState message="Loading logs..." /> : 
       error ? <ErrorState body={error} /> : 
       logs.length === 0 ? <div style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>No audit logs found for this course.</div> :
       (
         <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
           <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
             <thead>
               <tr>
                 <th style={{ padding: '12px', borderBottom: '2px solid #e2e8f0', background: '#f8fafc', color: '#475569' }}>Date</th>
                 <th style={{ padding: '12px', borderBottom: '2px solid #e2e8f0', background: '#f8fafc', color: '#475569' }}>User</th>
                 <th style={{ padding: '12px', borderBottom: '2px solid #e2e8f0', background: '#f8fafc', color: '#475569' }}>Entity</th>
                 <th style={{ padding: '12px', borderBottom: '2px solid #e2e8f0', background: '#f8fafc', color: '#475569' }}>Action</th>
                 <th style={{ padding: '12px', borderBottom: '2px solid #e2e8f0', background: '#f8fafc', color: '#475569' }}>Changes</th>
               </tr>
             </thead>
             <tbody>
               {logs.map(log => (
                 <React.Fragment key={log.id}>
                   <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
                     <td style={{ padding: '12px', whiteSpace: 'nowrap' }}>{new Date(log.created_at).toLocaleString()}</td>
                     <td style={{ padding: '12px' }}>{log.user_id}</td>
                     <td style={{ padding: '12px' }}>{log.entity_type} ({log.entity_id})</td>
                     <td style={{ padding: '12px' }}>
                       <Badge tone={getActionColor(log.action)}>{log.action.toUpperCase()}</Badge>
                     </td>
                     <td style={{ padding: '12px' }}>
                       {(log.before_json || log.after_json) && (
                         <Button tone="neutral" onClick={() => setExpandedLogId(expandedLogId === log.id ? null : log.id)}>
                           {expandedLogId === log.id ? "Hide Diff" : "View Diff"}
                         </Button>
                       )}
                     </td>
                   </tr>
                   {expandedLogId === log.id && (
                     <tr>
                       <td colSpan={5} style={{ padding: '16px', background: '#f8fafc', borderBottom: '2px solid #cbd5e1' }}>
                         <DiffViewer beforeObj={log.before_json} afterObj={log.after_json} />
                       </td>
                     </tr>
                   )}
                 </React.Fragment>
               ))}
             </tbody>
           </table>
         </div>
       )
      }
    </Modal>
  );
}
