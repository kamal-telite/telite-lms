import { useState } from "react";
import { Badge } from "../components/common/ui";
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
          <div className="sidebar-brand__identity">
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
          <button
            type="button"
            className="sidebar-collapse-btn"
            onClick={() => setCollapsed(!collapsed)}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <Icon name={collapsed ? "chevron-right" : "chevron-left"} size={16} />
          </button>
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

  return (
    <div className="profile-dropdown-wrapper">
      <button 
        type="button"
        className="profile-btn" 
        onClick={() => setOpen(!open)}
        aria-label="Open profile menu"
      >
        <div
          className="profile-btn__avatar"
          style={{ background: profile?.gradient ? `linear-gradient(135deg, ${profile.gradient.join(", ")})` : "var(--border)" }}
        >
          {profile?.initials || "U"}
        </div>
      </button>
      {open ? (
        <div className="profile-menu">
          <div className="profile-menu__header">
            <div className="row-title">{profile?.name || "Admin User"}</div>
            <div className="row-subtitle">{profile?.roleLabel || "System Admin"}</div>
          </div>
          <div className="profile-menu__items">
            <button type="button" className="dropdown-item" onClick={() => { setOpen(false); onNavigate?.('profile'); }}>
              <Icon name="profile" size={15} />
              <span>Profile</span>
            </button>
            <button type="button" className="dropdown-item" onClick={() => { setOpen(false); onNavigate?.('settings'); }}>
              <Icon name="settings" size={15} />
              <span>Settings</span>
            </button>
            <button type="button" className="dropdown-item" onClick={() => { setOpen(false); onNavigate?.('notifications'); }}>
              <Icon name="bell" size={15} />
              <span>Notifications</span>
            </button>
            <button type="button" className="dropdown-item" onClick={() => { setOpen(false); onNavigate?.('help'); }}>
              <Icon name="circle" size={15} />
              <span>Help & Support</span>
            </button>
          </div>
          <div className="profile-menu__items profile-menu__items--footer">
            <button type="button" className="dropdown-item dropdown-item--danger" onClick={onLogout}>
              <Icon name="logout" size={15} />
              <span>Log out</span>
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
