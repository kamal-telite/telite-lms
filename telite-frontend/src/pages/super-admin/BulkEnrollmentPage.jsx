import React, { useState } from 'react';
import CsvUploader from '../../components/dashboard/enrollments/CsvUploader';
import ValidationPreviewTable from '../../components/dashboard/enrollments/ValidationPreviewTable';
import ExecutionResultsTable from '../../components/dashboard/enrollments/ExecutionResultsTable';
import { previewBulkEnrollments, executeBulkEnrollments } from '../../services/client';
import { useToast } from '../../components/common/ui'; // Assuming useToast exists in telite
import { Button } from '../../components/common/ui';

export default function BulkEnrollmentPage() {
  const [step, setStep] = useState(1); // 1: Upload, 2: Preview, 3: Results
  const [loading, setLoading] = useState(false);
  const [previewData, setPreviewData] = useState([]);
  const [executionResult, setExecutionResult] = useState(null);
  const { showToast } = useToast();

  const handleDownloadTemplate = () => {
    const csvContent = "email,full_name,course_id\nuser@example.com,John Doe,course-slug-123\n";
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = "bulk_enrollment_template.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleFileSelect = async (file) => {
    setLoading(true);
    try {
      const result = await previewBulkEnrollments(file);
      setPreviewData(result.preview || []);
      setStep(2);
      showToast("CSV parsed successfully", "success");
    } catch (err) {
      showToast(err.message || "Failed to parse CSV", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    const validRows = previewData.filter(r => r.is_valid);
    if (validRows.length === 0) {
      showToast("No valid rows to execute", "error");
      return;
    }
    
    setLoading(true);
    try {
      const result = await executeBulkEnrollments(validRows);
      setExecutionResult(result);
      setStep(3);
      showToast("Bulk enrollment completed", "success");
    } catch (err) {
      showToast(err.message || "Execution failed", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setPreviewData([]);
    setExecutionResult(null);
    setStep(1);
  };

  const hasInvalidRows = previewData.some(r => !r.is_valid);
  const validRowCount = previewData.filter(r => r.is_valid).length;

  return (
    <div className="bulk-enrollment-page container" style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto' }}>
      <header style={{ marginBottom: '24px' }}>
        <h1 style={{ margin: 0 }}>Bulk Enrollment</h1>
        <p style={{ color: '#666', marginTop: '8px' }}>Enroll up to 1000 users across multiple courses simultaneously.</p>
      </header>

      {/* Progress Indicator */}
      <div className="steps" style={{ display: 'flex', gap: '20px', marginBottom: '32px', borderBottom: '1px solid #ddd', paddingBottom: '16px' }}>
        <div style={{ fontWeight: step >= 1 ? 'bold' : 'normal', color: step >= 1 ? '#000' : '#999' }}>1. Upload</div>
        <div style={{ fontWeight: step >= 2 ? 'bold' : 'normal', color: step >= 2 ? '#000' : '#999' }}>2. Validate</div>
        <div style={{ fontWeight: step >= 3 ? 'bold' : 'normal', color: step >= 3 ? '#000' : '#999' }}>3. Execute</div>
      </div>

      {loading && <div className="loading-spinner">Loading...</div>}

      {!loading && step === 1 && (
        <CsvUploader 
          onFileSelect={handleFileSelect} 
          onDownloadTemplate={handleDownloadTemplate} 
          disabled={loading}
        />
      )}

      {!loading && step === 2 && (
        <div className="preview-section">
          {hasInvalidRows && (
            <div className="alert alert-warning" style={{ backgroundColor: '#fffbeb', padding: '16px', borderRadius: '8px', marginBottom: '20px', border: '1px solid #fef3c7' }}>
              <strong>Warning:</strong> Some rows are invalid and will be skipped during execution.
            </div>
          )}
          
          <ValidationPreviewTable rows={previewData} />
          
          <div className="actions" style={{ marginTop: '24px', display: 'flex', gap: '16px', justifyContent: 'space-between' }}>
            <Button variant="outline" onClick={handleReset}>Cancel</Button>
            <Button 
              onClick={handleExecute} 
              disabled={validRowCount === 0}
            >
              Execute {validRowCount} Valid Enrollments
            </Button>
          </div>
        </div>
      )}

      {!loading && step === 3 && (
        <ExecutionResultsTable 
          result={executionResult} 
          onReset={handleReset} 
        />
      )}
    </div>
  );
}

