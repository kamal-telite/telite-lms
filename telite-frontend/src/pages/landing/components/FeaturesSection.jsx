import React from 'react';
import { FEATURES } from '../constants/features.jsx';
import FeatureCard from './FeatureCard';

export default function FeaturesSection() {
  return (
    <section id="features">
      <div className="inner">
        <div className="features-header">
          <span className="section-eyebrow">Everything you need</span>
          <h2 className="section-title">Built for modern learning<br />operations</h2>
          <p className="section-sub">A complete toolkit for admins, instructors, and learners.</p>
        </div>
        <div className="features-grid">{FEATURES.map((f) => <FeatureCard key={f.id} f={f} />)}</div>
      </div>
    </section>
  );
}
