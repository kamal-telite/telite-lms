import React, { useCallback } from 'react';
import { Button } from '../../common/ui';

export default function CsvUploader({ onFileSelect, onDownloadTemplate, disabled }) {
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    if (disabled) return;
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'text/csv') {
      onFileSelect(file);
    } else {
      alert("Please upload a valid CSV file.");
    }
  }, [disabled, onFileSelect]);

  const handleDragOver = (e) => e.preventDefault();

  const handleFileInput = (e) => {
    const file = e.target.files[0];
    if (file) {
      onFileSelect(file);
    }
  };

  return (
    <div className="csv-uploader">
      <div 
        className={`drop-zone ${disabled ? 'disabled' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        style={{
          border: '2px dashed #ccc',
          borderRadius: '8px',
          padding: '40px',
          textAlign: 'center',
          backgroundColor: '#fafafa',
          cursor: disabled ? 'not-allowed' : 'pointer'
        }}
      >
        <p>Drag and drop your CSV file here, or click to select</p>
        <input 
          type="file" 
          accept=".csv" 
          onChange={handleFileInput} 
          disabled={disabled}
          style={{ display: 'none' }}
          id="csv-file-upload"
        />
        <label htmlFor="csv-file-upload">
          <Button variant="secondary" as="span" disabled={disabled} style={{ marginTop: '10px' }}>
            Browse Files
          </Button>
        </label>
      </div>
      <div style={{ marginTop: '16px', textAlign: 'center' }}>
        <button onClick={onDownloadTemplate} className="btn btn-ghost">
          Download CSV Template
        </button>
      </div>
    </div>
  );
}

