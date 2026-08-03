import React from 'react';
import CountUp from './CountUp';

const SOLUTIONS = {
  college: {
    headline: 'Academic learning management',
    items: [
      'Manage students, courses, and departments',
      'Academic analytics and attendance tracking',
      'Role-based access per faculty and staff',
      'Bulk enrollment and verification tools',
      'API integration for existing systems',
    ],
  },
  company: {
    headline: 'Employee training and upskilling',
    items: [
      'Onboarding and compliance training paths',
      'Skill tracking and attendance management',
      'Team-level performance dashboards',
      'Domain-restricted signup and access control',
      'Export reports as CSV or PDF',
    ],
  },
};

const QUANT_METRICS = [
  { label: 'Organizations', value: 1284 },
  { label: 'Learners', value: 2.4, decimals: 1, suffix: 'M', useSeparator: false },
  { label: 'Sync Rate', value: 98.2, decimals: 1, suffix: '%', useSeparator: false },
  { label: 'Avg Session', value: 42, suffix: 'min' },
];

export default function SolutionsSection({ activeTab, setActiveTab }) {
  const current = SOLUTIONS[activeTab];

  return (
    <section id="solutions">
      <div className="inner">
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <span className="section-eyebrow" style={{ textAlign: 'center' }}>Solutions</span>
          <h2 className="section-title" style={{ textAlign: 'center' }}>Built for your context</h2>
          <p className="section-sub" style={{ textAlign: 'center', margin: '0 auto' }}>Whether managing students across departments or training employees at scale.</p>
        </div>
        <div className="solutions-grid">
          <div className="sol-left">
            <div className="sol-tabs">
              <button className={`sol-tab magnetic ${activeTab === 'college' ? 'active' : ''}`} onClick={() => setActiveTab('college')}>For Colleges</button>
              <button className={`sol-tab magnetic ${activeTab === 'company' ? 'active' : ''}`} onClick={() => setActiveTab('company')}>For Companies</button>
            </div>
            <div className={`sol-panel ${activeTab === 'college' ? 'active' : ''}`}>
              <h3 className="sol-headline">{SOLUTIONS.college.headline}</h3>
              <ul className="sol-checklist">
                {SOLUTIONS.college.items.map((item) => (
                  <li key={item}><span className="check-icon"><svg viewBox="0 0 16 16" fill="none" stroke="#10b981" strokeWidth="2"><path d="M4 8l3 3 5-6"/></svg></span>{item}</li>
                ))}
              </ul>
            </div>
            <div className={`sol-panel ${activeTab === 'company' ? 'active' : ''}`}>
              <h3 className="sol-headline">{SOLUTIONS.company.headline}</h3>
              <ul className="sol-checklist">
                {SOLUTIONS.company.items.map((item) => (
                  <li key={item}><span className="check-icon"><svg viewBox="0 0 16 16" fill="none" stroke="#10b981" strokeWidth="2"><path d="M4 8l3 3 5-6"/></svg></span>{item}</li>
                ))}
              </ul>
            </div>
          </div>
          <div className="sol-visual">
            <div className="sol-stats">
              {QUANT_METRICS.map((metric) => (
                <div className={`sol-stat ${metric.label === 'Organizations' || metric.label === 'Avg Session' ? 'accent' : ''}`} key={metric.label}>
                  <div className="big">
                    <CountUp
                      target={metric.value}
                      suffix={metric.suffix}
                      decimals={metric.decimals}
                      useSeparator={metric.useSeparator}
                    />
                  </div>
                  <div className="lbl">{metric.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
