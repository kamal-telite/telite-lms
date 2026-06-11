import { useState } from "react";
import { Badge, Avatar } from "../components/common/ui";
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
    <div className={`dashboard-shell ${collapsed ? "is-collapsed" : ""}`} data-theme={theme}>
      <aside className={`dashboard-sidebar ${collapsed ? "dashboard-sidebar--collapsed" : ""}`}>
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
          <div className="sidebar-profile">
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
  const menuItems = [
    { id: "profile", label: "Profile", icon: "profile" },
    { id: "settings", label: "Settings", icon: "settings" },
    { id: "notifications", label: "Notifications", icon: "bell" },
    { id: "help", label: "Help & Support", icon: "circle" },
  ];

  return (
    <div className="profile-dropdown-wrapper">
      <button
        type="button"
        className="profile-btn"
        onClick={() => setOpen(!open)}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <div
          className="profile-btn__avatar"
          style={{
            background: profile?.gradient
              ? `linear-gradient(135deg, ${profile.gradient.join(", ")})`
              : "var(--border)",
          }}
        >
          {profile?.initials || "U"}
        </div>
      </button>
      {open ? (
        <div className="menu-popover profile-menu" role="menu">
          <div className="profile-menu__header">
            <div className="profile-menu__name">{profile?.name || "Admin User"}</div>
            <div className="profile-menu__role">{profile?.roleLabel || "System Admin"}</div>
          </div>
          <div className="profile-menu__section">
            {menuItems.map((item) => (
              <button
                key={item.id}
                type="button"
                className="dropdown-item"
                role="menuitem"
                onClick={() => {
                  setOpen(false);
                  onNavigate?.(item.id);
                }}
              >
                <Icon name={item.icon} size={14} />
                <span>{item.label}</span>
              </button>
            ))}
          </div>
          <div className="profile-menu__section profile-menu__section--bordered">
            <button type="button" className="dropdown-item dropdown-item--danger" role="menuitem" onClick={onLogout}>
              <Icon name="logout" size={14} />
              <span>Log out</span>
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
