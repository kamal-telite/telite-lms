import { Link, useLocation } from "react-router-dom";

export default function AdminSidebar({ collapsed, onToggle, onLogout }) {
  const { pathname } = useLocation();

  const navGroups = [
    { section: "Core Section", items: [
      { id: "/platform-admin", icon: "dashboard", label: "Dashboard", exact: true },
      { id: "/platform-admin/organizations", icon: "corporate_fare", label: "Organizations" },
      { id: "/platform-admin/admins", icon: "admin_panel_settings", label: "Admin Control" },
    ]},
    { section: "Insights Section", items: [
      { id: "/platform-admin/analytics", icon: "insights", label: "Analytics" },
    ]},
    { section: "System Section", items: [
      { id: "/platform-admin/audit", icon: "history_edu", label: "Audit Logs" },
      { id: "/platform-admin/features", icon: "flag", label: "Feature Flags" },
      { id: "/platform-admin/settings", icon: "settings", label: "Settings" },
    ]},
  ];

  return (
    <aside id="sidebar" className={collapsed ? "collapsed" : ""}>
      <div className="sb-head">
        <div className="sb-logo">
          <span className="sb-logo-name">Telite LMS</span>
          <span className="sb-logo-sub">Global Admin Console</span>
        </div>
        <button className="sb-toggle" onClick={onToggle} title="Toggle sidebar">
          <span className="material-symbols-outlined" style={{fontSize: '16px'}}>menu</span>
        </button>
      </div>

      <nav className="sb-nav">
        {navGroups.map((group, idx) => (
          <div className="sb-section" key={idx}>
            <div className="sb-section-label">{group.section}</div>
            {group.items.map(item => {
              const isActive = item.exact ? pathname === item.id : pathname.startsWith(item.id);
              if (item.action) {
                return (
                  <div key={item.id} className={`nav-item ${isActive ? 'active' : ''}`} onClick={item.action}>
                    <span className="material-symbols-outlined">{item.icon}</span>
                    <span className="nav-label">{item.label}</span>
                  </div>
                );
              }
              return (
                <Link key={item.id} to={item.id} className={`nav-item ${isActive ? 'active' : ''}`}>
                  <span className="material-symbols-outlined">{item.icon}</span>
                  <span className="nav-label">{item.label}</span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="sb-footer">
        <Link to="/platform-admin/help" className={`nav-item ${pathname.startsWith('/platform-admin/help') ? 'active' : ''}`}>
          <span className="material-symbols-outlined">help</span>
          <span className="nav-label">Help</span>
        </Link>
        <div className="nav-item" onClick={onLogout} style={{color: 'var(--tx3)', marginTop: '4px'}}>
          <span className="material-symbols-outlined">logout</span>
          <span className="nav-label">Logout</span>
        </div>
      </div>
    </aside>
  );
}
