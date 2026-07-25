import { Link, useLocation } from "react-router-dom";

export default function AdminTopbar({ searchComponent, notifOpen, setNotifOpen, appsOpen, setAppsOpen, notifications, unreadCount, markAllRead }) {
  const { pathname } = useLocation();

  return (
    <header id="topbar">
      <div className="tb-left">
        {searchComponent}
        <nav className="tb-nav">
          <Link to="/platform-admin" className={`tb-nav-item ${pathname === '/platform-admin' ? 'active' : ''}`}>Overview</Link>
          <Link to="/platform-admin/organizations" className={`tb-nav-item ${pathname.startsWith('/platform-admin/organizations') ? 'active' : ''}`}>Organizations</Link>
          <Link to="/platform-admin/admins" className={`tb-nav-item ${pathname.startsWith('/platform-admin/admins') ? 'active' : ''}`}>Admin Control</Link>
        </nav>
      </div>
      <div className="tb-right">
        <div style={{position: 'relative'}}>
          <button 
            className="tb-icon-btn" 
            onClick={() => { setNotifOpen(!notifOpen); setAppsOpen(false); }} 
            title="Notifications"
          >
            <span className="material-symbols-outlined">notifications</span>
            {unreadCount > 0 && <span className="badge-dot"></span>}
          </button>
          <div className={`popover ${notifOpen ? 'show' : ''}`} style={{right: 0, top: '38px', width: '300px'}}>
            <div className="popover-head">
              <span className="popover-title">Notifications</span>
              <span style={{fontSize: '11px', color: 'var(--primary)', cursor: 'pointer', fontWeight: 600}} onClick={markAllRead}>Mark all read</span>
            </div>
            <div style={{padding: '8px 0'}}>
              {notifications.length === 0 ? (
                <div style={{padding: '20px', textAlign: 'center', color: 'var(--tx3)', fontSize: '12px'}}>
                  No notifications
                </div>
              ) : (
                notifications.slice(0, 5).map(n => (
                  <div key={n.id} className="notif-item" style={{padding: '8px 14px', gap: '10px', alignItems: 'flex-start', cursor: 'pointer'}}>
                    <div className="notif-icon-wrap" style={{width: '28px', height: '28px', background: n.color || 'var(--primary-lt)'}}>
                      <span className="material-symbols-outlined" style={{color: n.color || 'var(--primary)', fontSize: '14px'}}>{n.icon || 'info'}</span>
                    </div>
                    <div style={{flex: 1}}>
                      <div className="notif-title" style={{fontSize: '12px', fontWeight: n.read ? 400 : 600}}>{n.title}</div>
                      <div className="notif-sub" style={{fontSize: '10px', color: 'var(--tx3)'}}>{n.time}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
