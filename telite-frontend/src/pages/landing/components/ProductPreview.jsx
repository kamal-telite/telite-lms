import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Line } from 'react-chartjs-2';
import CountUp from './CountUp';

const PREVIEW_CHART_DATA = {
  labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
  datasets: [
    {
      label: 'Live Engagement',
      data: [65, 78, 90, 85, 95, 110, 105],
      borderColor: '#6366f1',
      backgroundColor: 'rgba(99, 102, 241, 0.1)',
      borderWidth: 3,
      fill: true,
      tension: 0.4,
      pointRadius: 4,
      pointBackgroundColor: '#05050a',
      pointBorderColor: '#6366f1',
      pointBorderWidth: 2,
    },
    {
      label: 'Cognitive Fatigue Risk',
      data: [20, 15, 30, 25, 10, 5, 8],
      borderColor: '#f59e0b',
      backgroundColor: 'rgba(245, 158, 11, 0.1)',
      borderWidth: 2,
      borderDash: [5, 5],
      fill: false,
      tension: 0.4,
      pointRadius: 0,
    },
  ],
};

const PREVIEW_CHART_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
      labels: {
        color: 'rgba(255, 255, 255, 0.7)',
        font: { family: 'Cabinet Grotesk, sans-serif', size: 12 },
      },
    },
    tooltip: {
      backgroundColor: 'rgba(17, 16, 39, 0.95)',
      titleColor: '#fff',
      bodyColor: 'rgba(255, 255, 255, 0.8)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      borderWidth: 1,
    },
  },
  scales: {
    x: {
      grid: { color: 'rgba(255, 255, 255, 0.05)' },
      ticks: { color: 'rgba(255, 255, 255, 0.5)', font: { family: 'Cabinet Grotesk' } },
    },
    y: {
      grid: { color: 'rgba(255, 255, 255, 0.05)' },
      ticks: { color: 'rgba(255, 255, 255, 0.5)', font: { family: 'Cabinet Grotesk' } },
    },
  },
};

function formatDuration(modules) {
  return modules.reduce((sum, module) => sum + parseInt(module.duration, 10), 0);
}

function ProductPreview({ activePreviewTab, activeIntegrationTab, setActivePreviewTab, approvals, handleApprove, handleReject, modules, toggleModule }) {
  const filteredPreviewTabs = useMemo(
    () => ['analytics', 'operations', 'builder'],
    []
  );

  return (
    <section id="product-preview">
      <div className="inner">
        <div className="preview-header" style={{ textAlign: 'center' }}>
          <span className="section-eyebrow" style={{ textAlign: 'center' }}>Interactive Sandbox</span>
          <h2 className="section-title" style={{ textAlign: 'center' }}>See Telite LMS in Action</h2>
          <p className="section-sub" style={{ textAlign: 'center', margin: '0 auto' }}>Experience our lightning-fast analytical layers, operational queues, and curriculum building tools.</p>
        </div>

        <div className="preview-container">
          <div className="preview-tabs">
            {filteredPreviewTabs.map((tab) => (
              <button
                key={tab}
                className={`preview-tab magnetic ${activePreviewTab === tab ? 'active' : ''}`}
                onClick={() => setActivePreviewTab(tab)}
              >
                {tab === 'analytics' ? 'Workspace Analytics' : tab === 'operations' ? 'Admin Operations' : 'Course Builder'}
              </button>
            ))}
          </div>

          <div className="preview-window">
            <div className="window-header">
              <div className="window-dots">
                <span className="dot red" />
                <span className="dot yellow" />
                <span className="dot green" />
              </div>
              <div className="window-address">https://app.telite.edu/dashboard/{activePreviewTab}</div>
            </div>
            <div className="window-body">
              {activePreviewTab === 'analytics' && (
                <div className="preview-pane-analytics">
                  <div className="pane-sidebar">
                    <div className="sidebar-metric">
                      <span className="label">Completion Index</span>
                      <h4 className="value">84.5%</h4>
                      <span className="subtext green">+3.2% vs baseline</span>
                    </div>
                    <div className="sidebar-metric">
                      <span className="label">Active Study Pacing</span>
                      <h4 className="value">4.8 hrs</h4>
                      <span className="subtext">Daily average session</span>
                    </div>
                    <div className="sidebar-metric">
                      <span className="label">Satisfaction Score</span>
                      <h4 className="value">4.92/5</h4>
                      <span className="subtext green">99.8% positive feedback</span>
                    </div>
                  </div>
                  <div className="pane-chart-container">
                    <div className="pane-chart-header">
                      <h4>Cohort Progression Trends</h4>
                      <p>Real-time analytics syncing directly from institutional webhooks.</p>
                    </div>
                    <div className="chart-canvas-wrap">
                      <Line data={PREVIEW_CHART_DATA} options={PREVIEW_CHART_OPTIONS} />
                    </div>
                  </div>
                </div>
              )}

              {activePreviewTab === 'operations' && (
                <div className="preview-pane-operations">
                  <div className="pane-header">
                    <h4>SuperAdmin Enrollment Approvals Queue</h4>
                    <p>Filter, verify, and approve domain-restricted student enrollments in real time.</p>
                  </div>
                  <div className="approvals-list">
                    {approvals.map((app) => (
                      <div className={`approval-row ${app.status.toLowerCase()}`} key={app.id}>
                        <div className="app-info">
                          <span className="app-name">{app.name}</span>
                          <span className="app-org">{app.org}</span>
                          <span className="app-course">{app.course}</span>
                        </div>
                        <div className="app-actions">
                          {app.status === 'Pending' ? (
                            <>
                              <button className="btn-approve magnetic" onClick={() => handleApprove(app.id)}>Approve</button>
                              <button className="btn-reject magnetic" onClick={() => handleReject(app.id)}>Reject</button>
                            </>
                          ) : (
                            <span className={`status-pill ${app.status.toLowerCase()}`}>{app.status}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="pane-footer-text">
                    <span>{approvals.filter((a) => a.status === 'Pending').length} pending verification checkouts in current queue</span>
                  </div>
                </div>
              )}

              {activePreviewTab === 'builder' && (
                <div className="preview-pane-builder">
                  <div className="pane-header">
                    <h4>Course Curriculum Composer</h4>
                    <p>Toggle modular course chunks to dynamically adjust syllabus weight and pacing paths.</p>
                  </div>
                  <div className="modules-list">
                    {modules.map((m) => (
                      <div className={`module-row ${m.active ? 'active' : ''}`} key={m.id}>
                        <div className="module-info">
                          <span className="module-title">{m.title}</span>
                          <span className="module-duration">{m.duration}</span>
                        </div>
                        <div className="module-action">
                          <button className={`toggle-btn-switch ${m.active ? 'on' : 'off'}`} onClick={() => toggleModule(m.id)}>
                            <span className="switch-dot" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="builder-summary">
                    <div className="summary-item">
                      <span className="label">Active Modules</span>
                      <span className="val">{modules.filter((m) => m.active).length} / {modules.length}</span>
                    </div>
                    <div className="summary-item">
                      <span className="label">Total Syllabus Duration</span>
                      <span className="val">{formatDuration(modules)} Hours</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default React.memo(ProductPreview);
