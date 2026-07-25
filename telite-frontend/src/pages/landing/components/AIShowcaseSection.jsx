import React from 'react';

export default function AIShowcaseSection() {
  return (
    <section id="ai-showcase">
      <div className="inner ai-showcase-layout">
        <div className="ai-showcase-left">
          <span className="section-eyebrow ai-glow-text">AI Diagnostics</span>
          <h2 className="section-title text-light">Predictive learning<br />intelligence</h2>
          <p className="section-sub text-light-muted">Telite doesn&apos;t just record scores; our proactive machine learning layer analyzes cognitive habits, identifies fatigue patterns, and alerts instructors before a learner falls behind.</p>
          <div className="ai-features-list">
            <div className="ai-feat-item">
              <div className="ai-feat-dot" />
              <div>
                <h4>Cognitive Fatigue Detection</h4>
                <p>Monitors action-delays, navigation pacing, and session intervals to map individual learning curves.</p>
              </div>
            </div>
            <div className="ai-feat-item">
              <div className="ai-feat-dot" />
              <div>
                <h4>Automated Risk Vector Triggers</h4>
                <p>Instantly flags at-risk profiles and suggests tailored remedial pathways with zero administrative overhead.</p>
              </div>
            </div>
          </div>
        </div>
        <div className="ai-showcase-right">
          <div className="ai-interactive-card">
            <div className="ai-card-header">
              <span className="ai-status-pulse" />
              <span className="ai-card-title">Cognitive Diagnostic Panel</span>
              <span className="ai-card-tag">Active Analysis</span>
            </div>
            <div className="ai-risk-profile">
              <div className="ai-profile-main">
                <div className="ai-avatar-placeholder">SK</div>
                <div>
                  <div className="ai-profile-name">Shreyas Kulkarni</div>
                  <div className="ai-profile-meta">Category: Advanced Cryptography</div>
                </div>
              </div>
              <div className="ai-risk-badge high-risk">High Risk Vector</div>
            </div>
            <div className="ai-diagnostics-metrics">
              <div className="ai-diag-metric">
                <span className="ai-diag-lbl">Velocity Profile</span>
                <span className="ai-diag-val warning-val">-24% drop-off</span>
              </div>
              <div className="ai-diag-metric">
                <span className="ai-diag-lbl">Concept Retention</span>
                <span className="ai-diag-val">82% accuracy</span>
              </div>
              <div className="ai-diag-metric">
                <span className="ai-diag-lbl">Cognitive Load</span>
                <span className="ai-diag-val danger-val">Fatigue detected</span>
              </div>
            </div>
            <div className="ai-card-remedial">
              <div className="ai-remedial-title">AI Suggested Remedial Action</div>
              <p className="ai-remedial-desc">Insert micro-conceptual recap quiz covering &quot;Symmetric Cipher Blocks&quot; and delay Module 4 by 48 hours.</p>
              <button className="btn-ai-action">Approve Path</button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
