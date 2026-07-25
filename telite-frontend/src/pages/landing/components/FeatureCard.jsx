import React from 'react';

export default function FeatureCard({ f }) {
  return (
    <div className="feature-card">
      <div className="fc-icon">{f.svg}</div>
      <h3 className="fc-title">{f.title}</h3>
      <p className="fc-desc">{f.desc}</p>
    </div>
  );
}
