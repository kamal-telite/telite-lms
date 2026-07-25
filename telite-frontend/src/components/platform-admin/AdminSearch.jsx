import { useRef } from "react";
import { useNavigate } from "react-router-dom";

export default function AdminSearch({ query, onQueryChange, results }) {
  const navigate = useNavigate();
  const searchRef = useRef(null);

  return (
    <div className="tb-search" id="searchWrap" style={{position: 'relative'}}>
      <span className="material-symbols-outlined s-ico" style={{fontSize: '15px'}}>search</span>
      <input 
        ref={searchRef}
        type="text" 
        placeholder="Global search… (⌘K)" 
        value={query}
        onChange={e => onQueryChange(e.target.value)}
      />
      {query && (
        <span 
          className="material-symbols-outlined s-clear" 
          style={{display:'block', cursor:'pointer'}} 
          onClick={() => onQueryChange('')}
        >
          close
        </span>
      )}
      {results && (results.orgs?.length > 0 || results.admins?.length > 0 || results.sync?.length > 0) && (
        <div className="popover show" style={{top: '100%', left: 0, width: '320px', marginTop: '8px'}}>
          <div className="popover-head">
            <span className="popover-title">Search Results</span>
          </div>
          <div style={{padding: '8px 0'}}>
            {results.orgs?.length > 0 && (
              <div style={{marginBottom: '12px'}}>
                <div style={{padding: '0 14px', fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', textTransform: 'uppercase', marginBottom: '4px'}}>Organizations</div>
                {results.orgs.map(org => (
                  <div 
                    key={org.id} 
                    className="notif-item" 
                    style={{padding: '6px 14px', gap: '8px', alignItems: 'center', cursor: 'pointer'}} 
                    onClick={() => { onQueryChange(''); navigate('/platform-admin/organizations'); }}
                  >
                    <div className="notif-icon-wrap" style={{width: '24px', height: '24px', background: 'var(--primary-lt)'}}>
                      <span className="material-symbols-outlined" style={{color: 'var(--primary)', fontSize: '14px'}}>business</span>
                    </div>
                    <div>
                      <div className="notif-title" style={{fontSize: '12px'}}>{org.name}</div>
                      <div className="notif-sub" style={{fontSize: '10px'}}>{org.domain}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {results.admins?.length > 0 && (
              <div style={{marginBottom: '12px'}}>
                <div style={{padding: '0 14px', fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', textTransform: 'uppercase', marginBottom: '4px'}}>Administrators</div>
                {results.admins.map(admin => (
                  <div 
                    key={admin.id} 
                    className="notif-item" 
                    style={{padding: '6px 14px', gap: '8px', alignItems: 'center', cursor: 'pointer'}} 
                    onClick={() => { onQueryChange(''); navigate('/platform-admin/admins'); }}
                  >
                    <div className="avatar" style={{width: '24px', height: '24px', fontSize: '10px', background: 'var(--green-bg)', color: 'var(--green)'}}>
                      {(admin.full_name || admin.email || 'U').substring(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <div className="notif-title" style={{fontSize: '12px'}}>{admin.full_name || admin.email}</div>
                      <div className="notif-sub" style={{fontSize: '10px'}}>{admin.role?.replace('_', ' ')}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
