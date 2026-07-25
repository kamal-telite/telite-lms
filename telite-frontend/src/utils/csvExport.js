// CSV Export Utility
export function downloadCSV(rows, headers, filename) {
  const csv = [headers, ...rows].map(r => 
    r.map(c => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')
  ).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
