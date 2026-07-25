export default function AdminFab({ open, onToggle, onCreateOrg, onInviteAdmin }) {
  return (
    <div id="fab">
      <div className={`fab-sub ${open ? 'show' : ''}`}>
        <div className="fab-action">
          <div className="fab-action-btn" onClick={() => { onCreateOrg(); onToggle(false); }}>
            <span className="material-symbols-outlined" style={{fontSize: '15px'}}>business</span> New Organization
          </div>
        </div>
        <div className="fab-action">
          <div className="fab-action-btn" onClick={() => { onInviteAdmin(); onToggle(false); }}>
            <span className="material-symbols-outlined" style={{fontSize: '15px'}}>person_add</span> Send Invitation
          </div>
        </div>
      </div>
      <button className="fab-main" onClick={() => onToggle(!open)}>
        <span className="material-symbols-outlined" style={{fontSize: '22px'}}>add</span>
      </button>
    </div>
  );
}
