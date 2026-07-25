import React from 'react';
import { Link } from 'react-router-dom';

const NAV_LINKS = [
  { href: '#features', label: 'Features' },
  { href: '#solutions', label: 'Solutions' },
  { href: '#pricing', label: 'Pricing' },
  { href: '#howitworks', label: 'How it works' },
  { href: '#cta-section', label: 'Contact' },
];

function LandingHeader({
  dashboardLink,
  resolvedTheme,
  toggleTheme,
  onCommandToggle,
  isMobileMenuOpen,
  setIsMobileMenuOpen,
}) {
  return (
    <>
      <nav id="lp-nav">
        <Link to="/" className="nav-logo">Telite LMS</Link>
        <ul className="nav-links">
          {NAV_LINKS.map((item) => (
            <li key={item.href}>
              <a href={item.href}>{item.label}</a>
            </li>
          ))}
        </ul>
        <div className="nav-actions">
          <button className="cmd-btn magnetic" onClick={onCommandToggle} aria-label="Open Command Palette">
            <span>Commands</span><kbd>⌘K</kbd>
          </button>
          <button className="theme-btn magnetic" onClick={toggleTheme} aria-label="Toggle Theme">
            {resolvedTheme === 'dark' ? '☀️' : '🌙'}
          </button>
          {dashboardLink ? (
            <Link to={dashboardLink} className="btn-primary magnetic">Go to Dashboard</Link>
          ) : (
            <>
              <Link to="/login" className="btn-ghost">Sign in</Link>
              <Link to="/login" className="btn-primary magnetic">Get started free</Link>
            </>
          )}
        </div>

        <button
          className={`mobile-menu-btn ${isMobileMenuOpen ? 'active' : ''}`}
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-label="Toggle Navigation Menu"
          aria-expanded={isMobileMenuOpen}
        >
          <span />
          <span />
          <span />
        </button>
      </nav>

      <div className={`mobile-drawer-overlay ${isMobileMenuOpen ? 'active' : ''}`} onClick={() => setIsMobileMenuOpen(false)} />
      <div className={`mobile-drawer ${isMobileMenuOpen ? 'active' : ''}`}>
        <div className="mobile-drawer-header">
          <Link to="/" className="nav-logo logo-dark" onClick={() => setIsMobileMenuOpen(false)}>
            Telite LMS
          </Link>
        </div>
        <ul className="mobile-drawer-links">
          {NAV_LINKS.map((item) => (
            <li key={item.href}>
              <a href={item.href} onClick={() => setIsMobileMenuOpen(false)}>{item.label}</a>
            </li>
          ))}
        </ul>
        <div className="mobile-drawer-actions">
          {dashboardLink ? (
            <Link to={dashboardLink} className="btn-drawer-primary" onClick={() => setIsMobileMenuOpen(false)}>Go to Dashboard</Link>
          ) : (
            <>
              <Link to="/login" className="btn-drawer-ghost" onClick={() => setIsMobileMenuOpen(false)}>Sign in</Link>
              <Link to="/login" className="btn-drawer-primary" onClick={() => setIsMobileMenuOpen(false)}>Get started free</Link>
            </>
          )}
        </div>
      </div>
    </>
  );
}

export default React.memo(LandingHeader);
