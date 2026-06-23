import React from 'react';
import { Button } from '../../common/ui';

export default function ExecutionResultsTable({ result, onReset }) {
  if (!result) return null;

  const { success_count, failure_count, errors } = result;

  const handleDownloadCsv = () => {
    if (!errors || errors.length === 0) return;
    const header = "Row,Email,Course ID,Error\n";
    const csvContent = errors.map(err => `"${err.row}","${err.email}","${err.course_id}","${err.error}"`).join("\n");
    const blob = new Blob([header + csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = "bulk_enrollment_errors.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="execution-results">
      <div className="summary-cards" style={{ display: 'flex', gap: '20px', marginBottom: '20px' }}>
        <div className="card" style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', flex: 1, textAlign: 'center', backgroundColor: '#f0fdf4' }}>
          <h3 style={{ margin: 0, color: '#166534' }}>Successful</h3>
          <p style={{ fontSize: '2em', margin: '10px 0 0 0', color: '#15803d' }}>{success_count}</p>
        </div>
        <div className="card" style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', flex: 1, textAlign: 'center', backgroundColor: '#fef2f2' }}>
          <h3 style={{ margin: 0, color: '#991b1b' }}>Failed</h3>
          <p style={{ fontSize: '2em', margin: '10px 0 0 0', color: '#b91c1c' }}>{failure_count}</p>
        </div>
      </div>

      {errors && errors.length > 0 && (
        <div className="error-details">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h4 style={{ margin: 0 }}>Error Details</h4>
            <Button variant="outline" onClick={handleDownloadCsv}>Download Errors CSV</Button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Row</th>
                  <th>Email</th>
                  <th>Course ID</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {errors.map((err, idx) => (
                  <tr key={idx}>
                    <td>{err.row}</td>
                    <td>{err.email}</td>
                    <td>{err.course_id}</td>
                    <td style={{ color: 'red' }}>{err.error}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div style={{ marginTop: '20px', textAlign: 'center' }}>
        <Button onClick={onReset}>Upload Another CSV</Button>
      </div>
    </div>
  );
}

