import React, { useMemo } from 'react';
import { INTEGRATIONS } from '../constants/integrations.jsx';

export default function IntegrationsSection({ activeIntegrationTab, setActiveIntegrationTab }) {
  const categories = useMemo(() => ['All', 'LMS', 'Communication', 'Payments', 'Enterprise'], []);
  const filteredIntegrations = useMemo(
    () => activeIntegrationTab === 'All' ? INTEGRATIONS : INTEGRATIONS.filter((item) => item.category === activeIntegrationTab),
    [activeIntegrationTab]
  );

  return (
    <section id="integrations">
      <div className="inner">
        <div className="integrations-header">
          <span className="section-eyebrow">Ecosystem</span>
          <h2 className="section-title">Seamless Integrations</h2>
          <p className="section-sub">Connect your existing workflows, LMS platforms, and identity providers with one click.</p>
        </div>
        <div className="integrations-tabs-wrapper">
          <div className="integrations-tabs">
            {categories.map((cat) => (
              <button
                key={cat}
                className={`integration-tab magnetic ${activeIntegrationTab === cat ? 'active' : ''}`}
                onClick={() => setActiveIntegrationTab(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
        <div className="integrations-grid">
          {filteredIntegrations.map((item) => (
            <div className="integration-card" key={item.name}>
              <div className="int-card-header">
                <div className="int-logo-wrapper">{item.svg}</div>
                <span className={`status-badge ${item.status.toLowerCase().replace(' ', '-')}`}>{item.status}</span>
              </div>
              <h3 className="int-name">{item.name}</h3>
              <span className="int-category">{item.category}</span>
              <p className="int-desc">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
