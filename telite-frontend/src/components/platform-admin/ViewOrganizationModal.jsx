import { createPortal } from "react-dom";

export default function ViewOrganizationModal({ org, onClose }) {
  if (!org) return null;
  const isCollege = org.type?.toLowerCase() === 'college';
  const isActive = org.status === 'active';
  
  return createPortal(
    <div className="overlay" onClick={onClose} style={{zIndex: 200}}>
      <div className="modal modal-md" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <div style={{display: 'flex', alignItems: 'center', gap: '12px'}}>
            <div className="org-icon" style={{width: '40px', height: '40px', background: isCollege ? 'var(--primary-lt)' : '#ECFDF5', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
              <span className="material-symbols-outlined" style={{color: isCollege ? 'var(--primary)' : '#059669', fontSize: '24px'}}>
                {isCollege ? 'account_balance' : 'business'}
              </span>
            </div>
            <div>
              <div className="modal-title">{org.name}</div>
              <div className="modal-sub">ID: {org.id} &bull; <a href={`https://${org.domain}`} target="_blank" rel="noreferrer" style={{color: 'var(--primary)'}}>{org.domain}</a></div>
            </div>
          </div>
          <button className="modal-close" onClick={onClose}><span className="material-symbols-outlined">close</span></button>
        </div>
        
        <div className="modal-body" style={{padding: '20px'}}>
          <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px'}}>
            <div className="info-block">
              <div style={{fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', textTransform: 'uppercase', marginBottom: '4px'}}>Status</div>
              <div><span className={`status-dot ${org.status?.toLowerCase()}`}>{isActive ? 'Active' : 'Suspended'}</span></div>
            </div>
            <div className="info-block">
              <div style={{fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', textTransform: 'uppercase', marginBottom: '4px'}}>Type</div>
              <div><span className={`badge ${isCollege ? 'badge-indigo' : 'badge-gray'}`}>{org.type?.toUpperCase()}</span></div>
            </div>
            <div className="info-block">
              <div style={{fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', textTransform: 'uppercase', marginBottom: '4px'}}>Total Users</div>
              <div style={{fontSize: '14px', fontWeight: 600, fontFamily: 'var(--fm)'}}>{org.user_count || 0}</div>
            </div>
            <div className="info-block">
              <div style={{fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', textTransform: 'uppercase', marginBottom: '4px'}}>Registered On</div>
              <div style={{fontSize: '14px'}}>{org.created_at ? org.created_at.split('T')[0] : 'N/A'}</div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>,
    document.body
  );
}
