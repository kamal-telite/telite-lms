import React from 'react';
import { TRUST_LOGOS } from '../constants/trustLogos.jsx';

export default function TrustLogosSection() {
  return (
    <section className="trust-section">
      <span className="trust-eyebrow">Trusted by 200+ institutions & enterprises globally</span>
      <div className="trust-marquee-container">
        <div className="trust-marquee-track">
          {[...TRUST_LOGOS, ...TRUST_LOGOS].map((logo, idx) => (
            <div className="trust-logo-card" key={`${logo.name}-${idx}`}>
              {logo.svg}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
