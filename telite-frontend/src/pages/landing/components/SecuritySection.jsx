import React from 'react';

const CARD_DATA = [
  {
    title: 'Military-Grade Encryption',
    description: 'End-to-end cryptographic shielding utilizing AES-256 for data-at-rest and TLS 1.3 for active operations in-transit.',
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
    ),
  },
  {
    title: 'Row-Level Tenancy Security',
    description: 'Strict, cryptographically isolated boundary policies running on the database-level to guarantee absolute data privacy.',
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/></svg>
    ),
  },
  {
    title: 'Continuous Audit Logs',
    description: 'Immutable audit trails recording credential configurations, role promotions, access vectors, and administrative workflows.',
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
    ),
  },
  {
    title: 'GDPR & ISO Readiness',
    description: 'Direct compliance frameworks engineered aligned with SOC 2 Type II, ISO 27001, and global GDPR residency mandates.',
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9 12l2 2 4-4"/></svg>
    ),
  },
];

export default function SecuritySection() {
  return (
    <section id="security-trust">
      <div className="inner">
        <div className="security-header" style={{ textAlign: 'center' }}>
          <span className="section-eyebrow" style={{ textAlign: 'center' }}>Enterprise Security</span>
          <h2 className="section-title" style={{ textAlign: 'center' }}>Guardians of your learning data</h2>
          <p className="section-sub" style={{ textAlign: 'center', margin: '0 auto' }}>Telite is engineered with state-of-the-art security compliance to protect institutional privacy and intellectual assets.</p>
        </div>
        <div className="security-grid">
          {CARD_DATA.map((item) => (
            <div className="security-card" key={item.title}>
              <div className="sec-icon-wrap">{item.svg}</div>
              <h3 className="sec-title">{item.title}</h3>
              <p className="sec-desc">{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
