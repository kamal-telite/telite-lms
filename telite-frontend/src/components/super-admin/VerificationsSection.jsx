import { Panel, Badge, Button, IconButton } from "../../components/common/ui";
import { titleize } from "../../utils/formatters";

export default function VerificationsSection({ 
  verifications, 
  bulkFile, 
  bulkLoading, 
  bulkResult, 
  setBulkFile, 
  handleBulkUpload, 
  handleVerification 
}) {
  return (
    <section id="section-verifications">
      <Panel
        id="section-verifications"
        title="Signup Verifications"
        subtitle="Approve or reject new user accounts"
        action={
          <div className="split-actions">
            <input 
              type="file" 
              id="bulk-verif-input" 
              style={{ display: 'none' }} 
              onChange={(e) => setBulkFile(e.target.files[0])}
            />
            {bulkFile && <span className="row-subtitle">{bulkFile.name}</span>}
            <Button 
              tone="ghost" 
              size="small" 
              onClick={() => document.getElementById('bulk-verif-input').click()}
            >
              {bulkFile ? "Change File" : "Select Bulk File"}
            </Button>
            <Button 
              tone="primary" 
              size="small" 
              disabled={!bulkFile || bulkLoading}
              loading={bulkLoading}
              onClick={handleBulkUpload}
            >
              Bulk Upload
            </Button>
          </div>
        }
      >
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Org / Role</th>
                <th>Details</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {verifications.map((v) => (
                <tr key={v.id}>
                  <td>
                    <div className="row-title">{v.full_name}</div>
                    <div className="row-subtitle">{v.email}</div>
                  </td>
                  <td>
                    <div className="row-title">{v.organization_name}</div>
                    <Badge tone="brand">{titleize(v.signup_role)}</Badge>
                  </td>
                  <td>
                    <div className="row-subtitle">ID: {v.id_number || 'N/A'}</div>
                    <div className="row-subtitle">{v.program} {v.branch ? `(${v.branch})` : ''}</div>
                  </td>
                  <td>
                    <Badge tone={v.domain_type === 'official' ? 'success' : 'warn'}>
                      {v.company_domain}
                    </Badge>
                  </td>
                  <td>
                    <div className="split-actions">
                      <IconButton label="Approve" icon="check" onClick={() => handleVerification(v.id, 'approve')} />
                      <IconButton label="Reject" icon="close" onClick={() => handleVerification(v.id, 'reject')} />
                    </div>
                  </td>
                </tr>
              ))}
              {verifications.length === 0 && (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '32px 0' }}>
                    <div className="row-subtitle">No pending verifications</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {bulkResult && (
          <div className="soft-card" style={{ marginTop: 16 }}>
            <div className="row-title">Bulk Result: {bulkResult.approved_count} approved, {bulkResult.ignored_count} ignored</div>
          </div>
        )}
      </Panel>
    </section>
  );
}
