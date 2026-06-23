import React, { useState, useMemo } from 'react';
import { Badge } from '../../common/ui'; // Assume these exist, or fallback to plain css

export default function ValidationPreviewTable({ rows }) {
  const [filter, setFilter] = useState('all'); // 'all', 'invalid', 'new_users', 'existing_users'

  const filteredRows = useMemo(() => {
    if (filter === 'invalid') return rows.filter(r => !r.is_valid);
    if (filter === 'new_users') return rows.filter(r => r.is_new_user);
    if (filter === 'existing_users') return rows.filter(r => !r.is_new_user);
    return rows;
  }, [rows, filter]);

  const invalidCount = rows.filter(r => !r.is_valid).length;
  const newCount = rows.filter(r => r.is_new_user).length;
  const existingCount = rows.length - newCount;

  return (
    <div className="validation-preview">
      <div className="filter-controls" style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
        <button onClick={() => setFilter('all')} className={filter === 'all' ? 'active' : ''}>
          All ({rows.length})
        </button>
        <button onClick={() => setFilter('invalid')} className={filter === 'invalid' ? 'active' : ''}>
          Invalid ({invalidCount})
        </button>
        <button onClick={() => setFilter('new_users')} className={filter === 'new_users' ? 'active' : ''}>
          New Users ({newCount})
        </button>
        <button onClick={() => setFilter('existing_users')} className={filter === 'existing_users' ? 'active' : ''}>
          Existing Users ({existingCount})
        </button>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Status</th>
              <th>User</th>
              <th>Course ID</th>
              <th>Account Type</th>
              <th>Errors</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((row, idx) => (
              <tr key={idx} style={{ backgroundColor: row.is_valid ? 'inherit' : '#fff0f0' }}>
                <td>
                  {row.is_valid ? <span style={{color: 'green'}}>Valid</span> : <span style={{color: 'red'}}>Invalid</span>}
                </td>
                <td>
                  <div>{row.full_name}</div>
                  <div style={{ fontSize: '0.85em', color: '#666' }}>{row.email}</div>
                </td>
                <td>{row.course_id}</td>
                <td>
                  {row.is_new_user ? <Badge color="blue">New User</Badge> : <Badge color="gray">Existing User</Badge>}
                </td>
                <td>
                  {row.errors.length > 0 ? (
                    <ul style={{ color: 'red', margin: 0, paddingLeft: '16px' }}>
                      {row.errors.map((err, i) => <li key={i}>{err}</li>)}
                    </ul>
                  ) : '-'}
                </td>
              </tr>
            ))}
            {filteredRows.length === 0 && (
              <tr><td colSpan="5" style={{textAlign: 'center'}}>No rows match the selected filter.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

