import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Badge } from "../components/common/ui";
import { Icon } from "../components/common/icons";
import AccountSwitcher from "../components/common/AccountSwitcher";
import ThemeSelector from "../components/common/ThemeSelector";
import NotificationBell from "../components/common/NotificationBell";
import { PageScroll, PanelScroll } from "../components/common/scroll";

export function DashboardShell({
  theme = "brand",
  variant,
  brandMark,
  brandTitle,
  brandSubtitle,
  navGroups,
  activeNav,
  onNavClick,
  title,
  subtitle,
  topbarBadge,
  topbarActions,
  tabBar,
  scrollRef,
  children,
  session,
  onSessionChange,
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isCompact, setIsCompact] = useState(() => typeof window !== "undefined" ? window.innerWidth < 1024 : false);
  const dashboardVariant = variant || theme;

  useEffect(() => {
    if (typeof window === "undefined") return undefined;

    const handleResize = () => {
      const compact = window.innerWidth < 1024;
      setIsCompact(compact);
      if (compact) {
        setCollapsed(true);
      }
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const sidebarCollapsed = isCompact ? false : collapsed;

  return (
    <div className={`dashboard-shell ${sidebarCollapsed ? 'is-collapsed' : ''}`} data-dashboard-variant={dashboardVariant}>
      <div className={`dashboard-sidebar__overlay ${mobileOpen ? 'is-visible' : ''}`} onClick={() => setMobileOpen(false)} />
      <PanelScroll autoHide={false} as="aside" data-lenis-prevent className={`dashboard-sidebar ${sidebarCollapsed ? 'dashboard-sidebar--collapsed' : ''} ${isCompact ? 'dashboard-sidebar--mobile' : ''} ${mobileOpen ? 'is-open' : ''}`}>
        <div className="sidebar-brand">
          <div className="sidebar-brand__mark" style={{ background: brandMark.background }}>
            {brandMark.label}
          </div>
          {!sidebarCollapsed && (
            <div>
              <div className="sidebar-brand__title">{brandTitle}</div>
              <div className="sidebar-brand__subtitle">{brandSubtitle}</div>
            </div>
          )}
        </div>

        <div className="sidebar-nav">
          {navGroups.map((group) => (
            <div className="sidebar-nav__group" key={group.label}>
              {!sidebarCollapsed && <div className="sidebar-nav__label">{group.label}</div>}
              <div className="sidebar-nav__items">
                {group.items.map((item) => (
                  <button
                    key={`${group.label}-${item.id}`}
                    type="button"
                    className={`nav-item ${activeNav === item.id ? "is-active" : ""}`}
                    onClick={() => {
                      onNavClick(item);
                      if (isCompact) {
                        setMobileOpen(false);
                      }
                    }}
                    title={sidebarCollapsed ? item.label : undefined}
                  >
                    <span className="nav-item__left">
                      <Icon name={item.icon} size={18} />
                      {!sidebarCollapsed && <span>{item.label}</span>}
                    </span>
                    {!sidebarCollapsed && item.badge ? <Badge tone={item.badgeTone}>{item.badge}</Badge> : null}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="sidebar-bottom">
          <button 
            type="button" 
            className="sidebar-collapse-btn"
            onClick={() => {
              if (isCompact) {
                setMobileOpen(false);
                return;
              }
              setCollapsed(!collapsed);
            }}
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <Icon name={sidebarCollapsed ? "chevron-right" : "chevron-left"} size={16} />
            {!sidebarCollapsed && <span>Collapse</span>}
          </button>
        </div>
      </PanelScroll>

      <div className="dashboard-main">
        <header className="topbar">
          <div className="topbar__leading">
            {isCompact ? (
              <button type="button" className="topbar__menu-btn" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
                <Icon name="list" size={18} />
              </button>
            ) : null}
            <div>
              <h1>{title}</h1>
              {subtitle && <p>{subtitle}</p>}
            </div>
          </div>
          <div className="topbar__actions">
            {topbarBadge ? <Badge tone={topbarBadge.tone}>{topbarBadge.label}</Badge> : null}
            {topbarActions}
            {session ? (
              <>
                <NotificationBell />
                <div style={{ width: 1, height: 24, backgroundColor: 'var(--border-color)', margin: '0 4px' }} />
                <AccountSwitcher session={session} onSessionChange={onSessionChange} />
              </>
            ) : null}
          </div>
        </header>
        {tabBar ? <div className="tabbar">{tabBar}</div> : null}
        <PageScroll as="main" className="dashboard-content" ref={scrollRef}>
          {children}
        </PageScroll>
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
          {profile?.initials ? profile.initials : <Icon name="profile" size={16} />}
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
            {profile?.roleLabel !== "learner" && (
              <button type="button" className="dropdown-item" onClick={() => { setOpen(false); onNavigate?.('profile'); }}>👤 Profile</button>
            )}
            <button type="button" className="dropdown-item" onClick={() => { setOpen(false); onNavigate?.('settings'); }}>⚙️ Settings</button>
            <button type="button" className="dropdown-item" onClick={() => { setOpen(false); onNavigate?.('notifications'); }}>🔔 Notifications</button>
            <button type="button" className="dropdown-item" onClick={() => { setOpen(false); onNavigate?.('help'); }}>❓ Help & Support</button>
          </div>
          <div style={{ padding: "10px 12px", borderTop: "1px solid var(--border)" }}>
            <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", fontWeight: 700, marginBottom: "8px" }}>
              Appearance
            </div>
            <ThemeSelector compact />
          </div>
          <div style={{ padding: "8px", borderTop: "1px solid var(--border)" }}>
            <button type="button" className="dropdown-item" style={{ color: "var(--danger)" }} onClick={onLogout}>🚪 Log out</button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

DashboardShell.propTypes = {
  theme: PropTypes.string,
  variant: PropTypes.string,
  brandMark: PropTypes.shape({
    background: PropTypes.string,
    label: PropTypes.node,
  }).isRequired,
  brandTitle: PropTypes.node.isRequired,
  brandSubtitle: PropTypes.node,
  navGroups: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string,
      items: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.string.isRequired,
          icon: PropTypes.string.isRequired,
          label: PropTypes.node.isRequired,
          badge: PropTypes.node,
          badgeTone: PropTypes.string,
        })
      ).isRequired,
    })
  ).isRequired,
  activeNav: PropTypes.string,
  onNavClick: PropTypes.func.isRequired,
  title: PropTypes.node.isRequired,
  subtitle: PropTypes.node,
  topbarBadge: PropTypes.shape({
    tone: PropTypes.string,
    label: PropTypes.node.isRequired,
  }),
  topbarActions: PropTypes.node,
  tabBar: PropTypes.node,
  scrollRef: PropTypes.oneOfType([
    PropTypes.func, 
    PropTypes.shape({ current: PropTypes.instanceOf(Element) })
  ]),
  children: PropTypes.node.isRequired,
  session: PropTypes.object,
  onSessionChange: PropTypes.func,
};

TabBar.propTypes = {
  tabs: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      label: PropTypes.node.isRequired,
    })
  ).isRequired,
  activeTab: PropTypes.string,
  onChange: PropTypes.func.isRequired,
};

SectionTitle.propTypes = {
  label: PropTypes.node.isRequired,
  actions: PropTypes.node,
};

ProfileDropdown.propTypes = {
  profile: PropTypes.shape({
    initials: PropTypes.string,
    gradient: PropTypes.arrayOf(PropTypes.string),
    name: PropTypes.string,
    roleLabel: PropTypes.string,
  }),
  onLogout: PropTypes.func.isRequired,
  onNavigate: PropTypes.func,
};
