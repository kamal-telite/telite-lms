import React from 'react';
import { Link } from 'react-router-dom';

const LEARNERS = [
  ["Ratan Singh", "68%", ""],
  ["Priya Seth", "82%", ""],
  ["Aman Gupta", "41%", "warn"],
  ["Sara Verma", "75%", ""],
];

function HeroSection({ dashboardLink, vantaHeroRef, heroTypedRef }) {
  return (
    <section id="hero">
      <div id="hero-bg" ref={vantaHeroRef} />
      <div className="hero-orb hero-orb--1" />
      <div className="hero-orb hero-orb--2" />
      <div className="hero-orb hero-orb--3" />
      <div className="hero-content">
        <div className="hc-left">
          <div className="hero-eyebrow"><span className="hero-eyebrow-dot" />Internal Learning Platform</div>
          <h1 className="hero-headline">
            One platform to manage<br />
            <span className="hero-typed-line"><span id="hero-typed" ref={heroTypedRef} /></span>
          </h1>
          <p className="hero-sub">Streamline education and training with role-based dashboards, real-time tracking, and seamless LMS integration.</p>
          <div className="hero-ctas">
            <Link to={dashboardLink || '/login'} className="btn-hero-primary magnetic">
              {dashboardLink ? 'Go to Dashboard' : 'Get started free'}
            </Link>
            <a href="#features" className="btn-hero-ghost magnetic">Explore features</a>
          </div>
          <div className="hero-ticker">
            <span className="ticker-label">AI Insights Live</span>
            <div className="ticker-feed"><span>Predictive learning models active...</span></div>
          </div>
        </div>

        <div className="hero-card-wrap">
          <div className="hero-card">
            <div className="hc-header"><span className="hc-dot" /><span className="hc-title">ATS Admin Dashboard</span><span className="hc-badge">Admin Panel</span></div>
            <div className="hc-metrics">
              <div className="hc-metric"><span className="num">6</span><small>Orgs</small></div>
              <div className="hc-metric"><span className="num">17</span><small>Courses</small></div>
              <div className="hc-metric hl"><span className="num">81%</span><small>Avg Score</small></div>
            </div>
            <div className="hc-learners">
              {LEARNERS.map(([name, pct, warn]) => (
                <div className="lr" key={name}>
                  <span className="lr-name">{name}</span>
                  <div className="lr-bar-wrap">
                    <div className={`lr-bar ${warn}`} style={{ width: pct }} />
                  </div>
                  <span className="lr-pct">{pct}</span>
                </div>
              ))}
            </div>
            <div className="hc-footer"><span>1 pending enrollment</span><a href="#features">2 at-risk learners →</a></div>
          </div>

          <div className="hero-float-card hero-float--1">
            <svg viewBox="0 0 18 18" fill="none" stroke="#10b981" strokeWidth="2" width="18" height="18"><path d="M4 9l3 3 7-7" /></svg>
            <span>Cloud synced</span>
          </div>
          <div className="hero-float-card hero-float--2">
            <svg viewBox="0 0 18 18" fill="none" stroke="#818cf8" strokeWidth="2" width="18" height="18"><circle cx="9" cy="9" r="7" /><path d="M9 5v4l3 2" /></svg>
            <span>42 active now</span>
          </div>
          <div className="hero-float-card hero-float--3">
            <svg viewBox="0 0 18 18" fill="none" stroke="#f59e0b" strokeWidth="2" width="18" height="18"><path d="M9 2l2 4 5 1-4 3 1 5-4-2-4 2 1-5-4-3 5-1z" /></svg>
            <span>AI analyzing</span>
          </div>
        </div>
      </div>
    </section>
  );
}

export default React.memo(HeroSection);
