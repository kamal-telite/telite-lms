import React from 'react';
import { Link } from 'react-router-dom';

function Pricing({ dashboardLink, isAnnual, selectedPlan, setSelectedPlan, handleToggle, plans, onContactSales }) {

  return (
    <section id="pricing">
      <div className="inner">
        <div className="pricing-header">
          <span className="section-eyebrow">Pricing</span>
          <h2 className="section-title">Simple, transparent pricing</h2>
          <div className="pricing-trust-line">Trusted by 120+ institutions globally</div>
          <p className="section-sub">Start free. Scale as you grow. No hidden fees.</p>
        </div>
        <div className="pricing-toggle">
          <span className={`toggle-label ${!isAnnual ? 'active' : ''}`} onClick={handleToggle}>Monthly</span>
          <div className={`toggle-switch ${isAnnual ? 'annual' : ''}`} onClick={handleToggle} role="switch" aria-checked={isAnnual} aria-label="Toggle annual pricing" />
          <span className={`toggle-label ${isAnnual ? 'active' : ''}`} onClick={handleToggle}>Annually</span>
          <span className="toggle-badge">Save 20%</span>
        </div>
        <div className="pricing-grid">
          {plans.map((p) => (
            <div
              key={p.name}
              className={`pricing-card ${p.highlight ? 'pro' : ''} ${selectedPlan === p.name ? 'selected' : ''}`}
              onClick={() => setSelectedPlan(p.name)}
              role="button"
              tabIndex={0}
              aria-label={`Select ${p.name} plan`}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setSelectedPlan(p.name); }}
            >
              {p.highlight && <span className="pro-badge">Most popular</span>}
              <div className="plan-name">{p.name}</div>
              <div className="plan-tag">{p.tag}</div>
              <div className="plan-price price-number">{isAnnual ? p.price.annual : p.price.monthly}</div>
              <div className="plan-period">{isAnnual && p.name === 'Pro' ? 'per month, billed annually' : p.period}</div>
              <ul className="plan-features">
                {p.features.map((feature) => (
                  <li key={feature}>
                    <span className="pf-check">
                      <svg viewBox="0 0 16 16" fill="none" stroke="#10b981" strokeWidth="2">
                        <path d="M4 8l3 3 5-6" />
                      </svg>
                    </span>
                    {feature}
                  </li>
                ))}
              </ul>
              <Link
                to={dashboardLink || (p.price.monthly === 'Custom' ? '#' : '/login')}
                className={`btn-plan magnetic ${p.highlight ? 'btn-plan-white' : p.price.monthly === 'Custom' ? 'btn-plan-ghost' : 'btn-plan-outline'}`}
                onClick={(e) => {
                  if (p.price.monthly === 'Custom') {
                    e.preventDefault();
                    e.stopPropagation();
                  }
                }}
              >
                {dashboardLink ? 'Go to Dashboard' : p.price.monthly === 'Custom' ? 'Contact Sales' : 'Get started'}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default React.memo(Pricing);
