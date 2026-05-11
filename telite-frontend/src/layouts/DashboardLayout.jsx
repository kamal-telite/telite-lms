import { useState } from "react";
import { Badge, Avatar, Button } from "../components/common/ui";
import { Icon } from "../components/common/icons";

export function DashboardShell({
  theme = "brand",
  brandMark,
  brandTitle,
  brandSubtitle,
  navGroups,
  activeNav,
  onNavClick,
  profile,
  title,
  subtitle,
  topbarBadge,
  topbarActions,
  tabBar,
  scrollRef,
  children,
}) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={`dashboard-shell ${collapsed ? 'is-collapsed' : ''}`} data-theme={theme}>
      <aside className={`dashboard-sidebar ${collapsed ? 'dashboard-sidebar--collapsed' : ''}`}>
        <div className="sidebar-brand">
          <div className="sidebar-brand__mark" style={{ background: brandMark.background }}>
            {brandMark.label}
          </div>
          {!collapsed && (
            <div>
              <div className="sidebar-brand__title">{brandTitle}</div>
              <div className="sidebar-brand__subtitle">{brandSubtitle}</div>
            </div>
          )}
        </div>

        <div className="sidebar-nav">
          {navGroups.map((group) => (
            <div className="sidebar-nav__group" key={group.label}>
              {!collapsed && <div className="sidebar-nav__label">{group.label}</div>}
              <div className="sidebar-nav__items">
                {group.items.map((item) => (
                  <button
                    key={`${group.label}-${item.id}`}
                    type="button"
                    className={`nav-item ${activeNav === item.id ? "is-active" : ""}`}
                    onClick={() => onNavClick(item)}
                    title={collapsed ? item.label : undefined}
                  >
                    <span className="nav-item__left">
                      <Icon name={item.icon} size={15} />
                      {!collapsed && <span>{item.label}</span>}
                    </span>
                    {!collapsed && item.badge ? <Badge tone={item.badgeTone}>{item.badge}</Badge> : null}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="sidebar-bottom">
          <div className="sidebar-profile" style={{ justifyContent: collapsed ? 'center' : 'flex-start' }}>
            <Avatar initials={profile.initials} gradient={profile.gradient} size={30} />
            {!collapsed && (
              <div>
                <div className="sidebar-profile__name">{profile.name}</div>
                <div className="sidebar-profile__role">{profile.roleLabel}</div>
              </div>
            )}
          </div>
          <button 
            type="button" 
            className="sidebar-collapse-btn"
            onClick={() => setCollapsed(!collapsed)}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <Icon name={collapsed ? "chevron-right" : "chevron-left"} size={16} />
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </aside>

      <div className="dashboard-main">
        <header className="topbar">
          <div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
          <div className="topbar__actions">
            {topbarBadge ? <Badge tone={topbarBadge.tone}>{topbarBadge.label}</Badge> : null}
            {topbarActions}
          </div>
        </header>
        {tabBar ? <div className="tabbar">{tabBar}</div> : null}
        <main className="dashboard-content" ref={scrollRef}>
          {children}
        </main>
      </div>
    </div>
  );
}

export function TabBar({ tabs, activeTab, onChange }) {
  return (
    <div className="tabbar__row">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={`tabbar__tab ${activeTab === tab.id ? "is-active" : ""}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function SectionTitle({ label, actions }) {
  return (
    <div className="section-title">
      <div>{label}</div>
      {actions ? <div className="section-title__actions">{actions}</div> : null}
    </div>
  );
}

export function ProfileDropdown({ profile, onLogout, onNavigate }) {
  const [open, setOpen] = useState(false);

  // Added a small inline click-away listener logic or simple toggle
  return (
    <div className="profile-dropdown-wrapper" style={{ position: "relative" }}>
      <button 
        type="button"
        className="profile-btn" 
        onClick={() => setOpen(!open)}
        style={{
          background: "transparent",
          border: "1px solid var(--border)",
          borderRadius: "99px",
          padding: "2px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center"
        }}
      >
        <div 
          style={{
            width: 32, 
            height: 32, 
            borderRadius: "50%", 
            background: profile?.gradient ? `linear-gradient(135deg, ${profile.gradient.join(", ")})` : "var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            fontWeight: 600,
            fontSize: "12px"
          }}
        >
          {profile?.initials || "U"}
        </div>
      </button>
      {open ? (
        <div 
          className="menu-popover" 
          style={{ 
            position: "absolute", 
            top: "44px", 
            right: "0", 
            minWidth: "220px", 
            background: "var(--surface)", 
            border: "1px solid var(--border)", 
            borderRadius: "12px", 
            boxShadow: "0 10px 15px -3px rgba(0,0,0,0.1)",
            zIndex: 50,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden"
          }}
        >
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
            <div style={{ fontWeight: 600, fontSize: "14px", color: "var(--text-primary)" }}>{profile?.name || "Admin User"}</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>{profile?.roleLabel || "System Admin"}</div>
          </div>
          <div style={{ padding: "8px" }}>
            <button type="button" className="dropdown-item" onClick={() => { setOpen(false); onNavigate?.('profile'); }}>👤 Profile</button>
            <button type="button" className="dropdown-item" onClick={() => { setOpen(false); onNavigate?.('settings'); }}>⚙️ Settings</button>
            <button type="button" className="dropdown-item" onClick={() => { setOpen(false); onNavigate?.('notifications'); }}>🔔 Notifications</button>
            <button type="button" className="dropdown-item" onClick={() => { setOpen(false); onNavigate?.('help'); }}>❓ Help & Support</button>
          </div>
          <div style={{ padding: "8px", borderTop: "1px solid var(--border)" }}>
            <button type="button" className="dropdown-item" style={{ color: "var(--danger)" }} onClick={onLogout}>🚪 Log out</button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
